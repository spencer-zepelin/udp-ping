import sys
import socket
import threading
import os
import time



######## UDP PINGER CLASS ###########

class UdpPinger:

    # Instantiation defines the core attributes for the given ping run
    def __init__(self, ip, port, cnt, prd, tmt):
        self.ip = ip
        self.port = port
        self.cnt = cnt
        self.prd = prd
        self.tmt = tmt
        self.idnum = os.getpid() % 65536 # mod by 2^16 to ensure process ID not greater than 16 bits

        # Object counter for replies received
        self.received = 0

        # Array of RTTs for replies received
        self.RTTs = []

        # Array of active threads to assist with return of control
        self.active_threads = []
        
        # Timestamp for start of ping run
        self.macrostart = round(time.time() * 1000)

        # Start Message
        print("PING {}".format(self.ip))

    # Ping function which handles the threading for messages and calls to print_stats upon thread completion
    def send_pings(self):
        # Spin up a thread for each ping
        for ping_num in range(self.cnt):
            # Add wait time equivalent to the period times that threads seqeunce number (NB: ping_num will start at 0 in this loop)  
            wait_interval = self.prd * ping_num
            # Threaded call to "pinger" function; only requires sequence number as argument,
            ping = threading.Timer(wait_interval, self.pinger, args=[ping_num+1]) # ping_num + 1 will represent the sequence number
            # Add thread to array so it can be joined afterwards to return control
            self.active_threads.append(ping)
            # Initialize thread
            ping.start()

        # Loop through used threads and "join" them to return control
        for thread in self.active_threads:
            ping.join()

        # Call to stats function upon ping completion
        self.print_stats()

    # Writes, sends, and recieves the ping; prints result and records stats in class attributes
    def pinger(self, seq):
        # Hardcoded type x\08 and code x\00
        typecode = "0000100000000000" 
        # ID number taken from process ID upon class initialization
        this_id = "{0:>016b}".format(self.idnum) # convert to binary and zero pad to 16 bytes
        # Passed argument for sequence number
        seqno = "{0:>016b}".format(seq) # convert to binary and zero pad to 16 bytes
        # Datagram socket
        ss = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Establish timeout length
        ss.settimeout(self.tmt)
        # Take timestamp for message send in ms
        startstamp = round(time.time() * 1000)
        # Convert timestamp to 6 bytes of binary
        fullstamp = "{0:>048b}".format(startstamp)
        # Call to helper function (below) to calculate checksum); returns a string with 2-byte binary checksum
        checksum = make_checksum([typecode, this_id, seqno, fullstamp[0:16], fullstamp[16:32], fullstamp[32:]])
        # Concatenate binary strings
        data_string = typecode + checksum + this_id + seqno + fullstamp
        # Convert binary string to big-endian bytes
        datagram = int(data_string, 2).to_bytes(14, byteorder="big")
        # Fire off the ping
        ss.sendto(datagram, (self.ip, self.port))
        
        # This try catch is specific to the socket timeout
        try: 
            # Handle recieved data and source server address
            data, server = ss.recvfrom(1024) 
            # Timestamp for receipt in ms since epoch
            endstamp = round(time.time() * 1000)
            # Converting data to binary string for checksum
            data_string = "{0:>0112b}".format(int.from_bytes(data, byteorder="big"))
        
            # validate the data returned is corrected
            # calls to helper function (below) to validate correctness
            if validate_checksum(data_string):
                # Calculate round trip time from start and end stamps
                RTT = str(endstamp - startstamp)
                # Prints stats for individual ping
                print("PONG {}: seq={} time={} ms".format(server[0], seq, RTT))
                # Increments number of received pings
                self.received += 1
                # Appends RTT to array
                self.RTTs.append(int(RTT))
            else: # checksum incorrect --> treat as lost packet
                print("Error (invalid checksum) receiving PONG {}: seq={}".format(self.ip, seq)) 
        except socket.timeout: # only executes on timeout
            print("Error (timeout) receiving PONG {}: seq={}".format(self.ip, seq))

    # Called upon completion of sending pings to calculate and report aggregate stats
    def print_stats(self):
        # Timestamp for end of entire process
        macroend = round(time.time() * 1000)
        # Three zeros for the edge case where loss is 100%
        rtt_min = 0
        rtt_avg = 0
        rtt_max = 0
        # Redefine stats if loss <100%
        if len(self.RTTs) > 0:
            # min RTT
            rtt_min = min(self.RTTs)
            # avg RTT
            rtt_avg = round(sum(self.RTTs)/len(self.RTTs))
            # max RTT
            rtt_max = max(self.RTTs)
        # Calculation of loss percentage
        percent_lost = round(100 - (100 * self.received/self.cnt))
        # Timedelta for entire process
        total_elapsed = str(macroend - self.macrostart)
        # Report of ping run
        print_string = "\n--- {server} ping statistics ---\n".format(server=self.ip)
        print_string += "{sent} transmitted, {received} received, ".format(sent=self.cnt, received=self.received)
        print_string += "{losspercent}% loss, time {totaltime}ms\n".format(losspercent=percent_lost, totaltime=total_elapsed)
        print_string += "rtt min/avg/max = {min}/{avg}/{max} ms\n".format(min=rtt_min, avg=rtt_avg, max=rtt_max)
        print(print_string)



####### HELPER FUNCTIONS FOR CHECKSUM ############

# Used to validate recieved checksum
def validate_checksum(input_string):
    # Current sum; starts at 0
    current = "0000000000000000"
    # Loop over the 7 16-bit segments
    for i in range(7):
        binstring = input_string[i*16:(i+1)*16]
        # Add integers and convert back to binary
        binsum = bin(int(current, 2) + int(binstring, 2))[2:]
        # No carry
        if len(binsum) < 17:
            # Update current to 16-bit binary string
            current = "{0:>016s}".format(binsum)
        # Carry
        else:
            # slice off leading 1
            binsum = binsum[1:] 
            # add 1 to what remains
            binsum = bin(int(binsum, 2) + int("1",2))[2:]
            # Update current to 16-bit binary string
            current = "{0:>016s}".format(binsum)
    # If correct, binary string should read as all 1s
    if current == "1111111111111111":
        return True
    else:
        return False

# Used to create checksum for outgoing message
def make_checksum(list_of_bin_strings):
    # Current sum; starts at 0
    current = "0000000000000000"
    # Loop through list of 16-bit binary strings
    for binstring in list_of_bin_strings:
        # Add integers and convert back to binary
        binsum = bin(int(current, 2) + int(binstring, 2))[2:]
        # No carry
        if len(binsum) < 17:
            # Update current to 16-bit binary string
            current = "{0:>016s}".format(binsum)
        else: # need to carry
            binsum = binsum[1:]
            # add 1 to what remains
            binsum = bin(int(binsum, 2) + int("1", 2))[2:]
            # Update current to 16-bit binary string
            current = "{0:>016s}".format(binsum)
    # Variable for the return string
    final_check = ""
    # take the one's complement of the sum
    for digit in current:
        # Flip the bits
        if digit == "1":
            final_check += "0"
        else:
            final_check += "1"
    return final_check



############ PRIMARY CONTROL FUNCTION ###################

if __name__ == "__main__":

    # Default values if undefined by program call
    ip = "127.0.0.1" # default to localhost
    port = 8080 # default port 
    cnt = 5
    prd = 1.0
    tmt = 1.0

    # Processing of command line arguments
    for argument in sys.argv[1:]:
        if "--server_ip" in argument: 
            ip = argument.split("=")[1] 
        elif "--server_port" in argument:
            port = int(argument.split("=")[1])
        elif "--count" in argument: 
            cnt = int(argument.split("=")[1])
        elif "--period" in argument: 
            prd = int(argument.split("=")[1])
        elif "--timeout" in argument: 
            tmt = float(argument.split("=")[1])
        
        # if there is an argument that does not conform with the above, print an error explaining proper use, and exit the program
        else:
            print("\nIMPROPER ARGUMENT: {} \nThis program can only handle the following arguments:\n\n".format(argument) + 
                "\t--server_ip=<server ip addr>\n \t--server_port=<server port>\n\t--count=<number of pings to send>\n" +
                "\t--period=<wait interval in seconds>\n\t--timeout=<timeout in seconds>\n")
            sys.exit()

    # Primary Class Instantiation
    up = UdpPinger(ip, port, cnt, prd, tmt)
    # Core Pinging Function
    up.send_pings()
