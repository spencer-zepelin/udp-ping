Networks
MPCS 54001

UDP Ping Client
Project 3

Spencer Zepelin

June 2, 2019

------------------


Design
---
I implemented the project in Python 3. My work is present 
in udp_ping_client.py.

The client operates through the UdpPinger class which is 
instantiated when the program is called from the command
line. It spins up threads for the number of pings called
for by the "--count=" argument and sends a ping on each.

The datagram each ping sends consists of following:

- The type and code, one byte each, hardcoded as they 
remain static.
- The checksum, two bytes, calculated with a helper 
function from the other elements by taking the one's 
complement of the one's complement sum of 16-bit "words"
in the binary datagram.
- The identifier sequence, two bytes, determined by the 
os process id as suggested in the prompt. 
- The sequence number, two bytes, incremented with each
subsequent ping.
- The timestamp, six bytes, expressed as ms since the 
epoch.

Upon successful receipt of an echo from the pinged
server and validation of a correctly received checksum,
the thread will print a success message with the round 
trip time (RTT) and log the stats.

If a threads timeout elapses or the checksum fails, 
an error message will print.

After all threads have run, control is returned to the 
primary process and aggregate statistics are printed.
Failed pings--either due to bit errors or timeouts--
are excluded from min/avg/max calculations for RTT.

Testing
---
The client passed testing against standard calls and
edge cases.

Running the Program
---
In an environment with Python 3 installed as the default 
instance of python, the ping client can be spun up 
by running

python udp_ping_client.py <FLAGGED-ARGS>

For ease of testing, I set default values for all flagged 
arguments. If a flagged argument is not defined on the call
from the command line, the program will run with the default. 

The following are the available flagged arguments and their
default values:

--server_ip=<server ip address to be pinged> 127.0.0.1
--server_port= <server port number> 8080
--count=<number of pings to send> 5
--period=<wait interval in seconds> 1.0
--timeout=<timeout length in seconds> 1.0

The program should be given the IP address and port on which 
the ping server is running. The other arguments are less
critical and can be experimented with at will.


