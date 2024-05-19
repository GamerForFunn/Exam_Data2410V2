import argparse
from datetime import datetime
import ipaddress
import sys
from struct import *
from socket import *
import time

header_format = '!HHH'     # Format for the header
data_size = 994    # Size for data to be sent
header_size = 6    # Size of the header
packet_size = data_size + header_size       # Total packet size is data + header
# Set flags to be used
rest_flag = 1
fin_flag = 2
ack_flag = 4
syn_flag = 8
# Window size for acknowledgement
ack_window_size = 64
# Time interval to be used for timeout
time_interval = 0.5

 # Description: 
 # Converts val to an int
 # Arguments: 
 # val: given value to convert
 # Tries to convert to int and return the new value
 # returns an error if it doesn't work
 
def convertToInt(val):
    try:
        value = int(val)
    except ValueError:
        raise argparse.ArgumentTypeError('Expected an integer but you entered a string')
    return value

 # Description: 
 # Checks for valid IP
 # Arguments: 
 # val: given value to check
 # Checks if the IP address given in val is valid and returns it
 # Tells the user that the IP address is not valid if it fails.

def check_IP(val):
    try:
        value = ipaddress.ip_address(val)
    except ValueError:
        print(f'The IP address {val} is not valid')
        sys.exit()
    return value

 # Description: 
 # Checks if port number is valid
 # Arguments: 
 # val: given value check
 # converts port number to int and checks if it's valid
 # Tell user that it's not valid if it fails.

def check_port(val):
    #Tries to convert the specified value to an integer
    value = convertToInt(val)
    # Port value can't be lower than 1024 or higher than 65535
    if (value < 1024 or value > 65535):
        print(f'{value} is not a valid port')
        sys.exit()
    return value



 # Description: 
 # Checks if given testcase is valid
 # Arguments: 
 # val: given value to check
 # Checks if val is a valid test case and returns it.
 # Tells user that the given protocol is invalid if it fails.

def check_testCase(val):
    if (val not in ['skip_ack', 'skip_seq_num']):
        print(f'{val} is not a valid test case')
        sys.exit()
    return val

 # Description: 
 # Checks if given window size is valid.
 # Arguments: 
 # val: given value to check
 # converts val to int and checks if it's a valid window size and returns it
 # Tells user that it's an invalid window size if it fails.

def check_windowSize(val):
    value = convertToInt(val)
    if (value not in [3, 5, 10]):
        print(f'{value} is not a valid window size')
        sys.exit()
    return value

 # Description: 
 # Creates a packet
 # Arguments: 
 # seq: holds sequence number
 # ack: holds the acknowledgement
 # flags: holds the flag
 # win: Holds the window
 # data: holds the data
 # Packs seq, ack, flags, and window size using header_format into a header
 # then creates a packet with the header and data.
 # returns: the full packet to be sent

def create_packet(seq, ack, flags, data):
    header = pack (header_format, seq, ack, flags)
    packet = header + data
    return packet

 # Description: 
 # Function that parses header
 # Arguments: 
 # header: Holds the header
 # Takes in a header and uses the header_format to parse it.
 # returns: parsed header

def parse_header(header):
    header_from_msg = unpack(header_format, header)
    return header_from_msg

 # Description: 
 # parses flags
 # Arguments: 
 # flags: holds flags
 # Sets syn, ack, and fin based on flags
 # returns syn, ack, and fin

def parse_flags(flags):
    syn = flags & (1 << 3)
    ack = flags & (1 << 2)
    fin = flags & (1 << 1)
    rest = flags &(1 << 0)
    return syn, ack, fin

 # Description: 
 # calculates throughput
 # Arguments: 
 # start_time: holds start_time
 # end_time: holds end_time
 # bytes: holds the amount of bytes
 # Finds duration based on start_time and end_time
 # then calculates throughput by getting the bytes and duration to the right format and dividing bytes by duration.
 # returns: throughput

def calculateThroughput(start_time, end_time, bytes):
    duration = end_time - start_time    # Calculate the duration by subtracting start time from end time
    throughput = (bytes * 8) / (duration * 1000000)     # Calculate the throughput in megabits per second
    return throughput

 # Description: 
 # restructures file
 # Arguments: 
 # file: holds the file to restruct
 # constructs the file in the right order based on buffered packets
 # prints when it's done and returns nothing as the function is used to write to file.

def restructFile(file):
    recv_buffer.sort(key=lambda x: x[0])    # Sort the received buffer based on sequence numbers
    # Iterate over the sorted buffer and write packet data to the file
    for seq_num, packet in recv_buffer:
        file.write(packet[header_size:])
    print("Done constructing")

 # Description: 
 # Function that reads data from a file
 # Makes a data array and takes file_path from sys arguments.
 # opens filepath and reads data from it and appends into the data array
 # prints error if something is wrong with the file or path
 # returns data array

def readDataFromFile():
    # Setup Array for data and get filepath from sys arguments
    dataArr = []
    file_path = args.file

    try:
        file = open(file_path, "rb")    # Open file and read data while true
        while True:
            data = file.read(data_size)
            if not data:
                break       # Break when there's no more data
            # Put data into array and close
            dataArr.append(data)        
        file.close() 
    # if file isn't found, tell user that file doesn't exist and exit
    except FileNotFoundError:
        print(f"File {file_path} does not exist")
        sys.exit()
    # if an error happens with the file, inform user that the application is unable to read file and exit.
    except IOError:
        print(f"Unable to read file {file_path}")
        sys.exit()

    return dataArr

 # Description: 
 # closes the connection
 # Arguments: 
 # clientSocket: holds the clientSocket
 # creates a fin packet and sends it to server to close the connection gracefully
 # closes the socket after.

def closeConnection(clientSocket): 
    # get server details
    serverIP = str(args.serverIP)
    serverPort = args.port

    # Create FIN packet and send to server, then close socket.
    packet = create_packet(0, 0, fin_flag, b'')
    clientSocket.sendto(packet, (serverIP, serverPort))
    print("Sent FIN from client")
    # Close client
    clientSocket.close()

 # Description: 
 # handshake from serverside
 # Arguments: 
 # serverSocket: Holds serverSocket
 # header: holds the header
 # clientAddress: holds the address for client
 # sets seq and ack numbers to 0 to synchronize for communication with client
 # creates syn packet and sends to client then returns true
 # returns false and tells user that server didn't receive SYN from client.

def serverHandshake(serverSocket, header, clientAddress):
    recv_seq, recv_ck, recv_flags = parse_header(header)
            
    #SYN flag is set
    if (recv_flags & 8) == 8 :
        sequence_number = 0
        ack_number = 0
        #SYN and ACK flags are set
        flags = syn_flag + ack_flag
        data = b''      # No data is included in the packet
        packet = create_packet(sequence_number, ack_number, flags, data)
        serverSocket.sendto(packet, clientAddress)
        return True     # Handshake successful
    print("Failed to receive SYN from client at address", clientAddress)
    return False        # Handshake failed

 # Description: 
 # Handshake from client
 # Arguments: 
 # clientSocket: holds the clientSocket
 # sets seq and ack to 0, then creates a SYN packet and sends to server
 # Receives a packet from server and checks if the SYN packet from server is correct
 # Sends acknowledgement of synchronization if successful and returns true
 # returns false and say what went wrong if not

def clientHandshake(clientSocket):
    serverIP = str(args.serverIP)
    serverPort = args.port
    
    sequence_num = 0
    ack_num = 0
    data = b''   # No data is included in the packet

    packet = create_packet(sequence_num, ack_num, syn_flag, data)
    clientSocket.sendto(packet, (serverIP, serverPort))
    clientSocket.settimeout(time_interval) 

    try:
        header, serverAddress = clientSocket.recvfrom(header_size)
        recv_seq, recv_ack, recv_flags = parse_header(header)

        # Check that SYN and ACK flags are set
        if (recv_flags & 12) == 12: 
            # Send ACK packet to acknowledge the SYN-ACK
            data = b''
            ack_num = recv_seq  # Set the acknowledgment number to the received sequence number
            packet = create_packet(sequence_num, ack_num, ack_flag, data)
            clientSocket.sendto(packet, serverAddress) 
            return True     # Handshake successful
        else:
            print("Received packet is not a SYN-ACK")
            return False        # Handshake failed
    except:
        print("Timeout reached")    
        return False        # Handshake failed


 # Description: 
 # client for go-back-N
 # Arguments: 
 # clientSocket: holds the client socket
 # dataArr: holds the data array
 # if packets are unacked append them to unacked packets array and check for testcase
 # Send data to server and wait for acknowledgements
 # closes connection after transfer and returns amount of sent bytes.

def goBackNClient(clientSocket, dataArr):
    serverIP = str(args.serverIP)
    serverPort = args.port
    window = args.windowSize
    testCase = args.testCase    
    skipped_seq_num = False     # Flag to indicate if a sequence number was skipped in the test case
    base = 0
    next_seq_num = 0
    ack_num = 0
    flags = 0
    unackedPackets = []     # List to store unacknowledged packets
    sent_bytes = 0      # Counter for the total number of sent bytes
    clientSocket.settimeout(time_interval)
    
    # Continue sending packets until all packets are sent and acknowledged
    while (base < len(dataArr) or unackedPackets):
        # Send packets within the window
        while (next_seq_num < base + window and next_seq_num < len(dataArr)):
            data = dataArr[next_seq_num]    # Get the data for the next sequence number
            packet = create_packet(next_seq_num, ack_num, flags, data)
            unackedPackets.append((next_seq_num, packet))   # Add the packet to the list of unacknowledged packets

            # Check if the current sequence number needs to be skipped based on the test case
            if(next_seq_num == 4 and testCase == 'skip_seq_num' and not skipped_seq_num):
                print("Skipped sending", next_seq_num)
                for seq_num, packet in unackedPackets:
                    print("Unacked list:", seq_num)
                next_seq_num += 1
                skipped_seq_num = True
                continue

            clientSocket.sendto(packet, (serverIP, serverPort))
            print("Sending packet ", next_seq_num)
            for seq_num, packet in unackedPackets:
                print("Unacked list:", seq_num)
            sent_bytes += len(packet[header_size:])     #Increment sent bytes variable
            next_seq_num += 1
        try:
            received_packet, serverAddress = clientSocket.recvfrom(packet_size)
            header = received_packet[:header_size]
            recv_seq, recv_ack, recv_flags = parse_header(header)

            # Check if the received packet is an acknowledgment and the base sequence number
            if(recv_flags == ack_flag and recv_ack == base):
                print("Received ack ", recv_ack)
                unackedPackets.pop(0)       # Remove the acknowledged packet from the list
                base = recv_ack + 1     # Update the base sequence number
        # retransmit
        except Exception:
            for seq_num, packet in unackedPackets:
                print("----------------Retransmitting packet-----------------", seq_num)
                clientSocket.sendto(packet, (serverIP, serverPort))
                sent_bytes += len(packet[header_size:])

    closeConnection(clientSocket) # Close socket connection
    return sent_bytes   # return total number of bytes sent

 # Description: 
 # Server for Go-Back-N and Stop and wait
 # Arguments: 
 # serverSocket: Holds the server socket
 # clientAddress: holds the client address info
 # file: holds the file
 # recv_seq: holds the received sequence
 # data: holds the data
 # checks for test case
 # receives packets from client and sends acknowledgements back.

def gbnSwServer(serverSocket, clientAddress, file, recv_seq, data):
    global expected_seq_num
    global testCase     # The current test case being executed
    global skipped_ack
    sent_data = b''     # Placeholder for sent data (empty in this case)

    # Check if the expected sequence number matches the condition to skip ACK
    if(expected_seq_num == 4 and testCase == 'skip_ack' and not skipped_ack):
        print(f"Received packet {recv_seq}. Skipping ACK ", expected_seq_num)
        skipped_ack = True
        testCase = ""
    # Check if the received sequence number matches the expected sequence number
    elif(recv_seq == expected_seq_num):
        file.write(data)    # Write the received data to the file
        packet = create_packet(0, expected_seq_num, ack_flag, sent_data)
        print(f"Received packet {recv_seq}. Sending ACK {expected_seq_num}")
        serverSocket.sendto(packet, clientAddress)
        expected_seq_num += 1
        skipped_ack = False     # Reset the skipped_ack flag
    else:
        # Discard the packet if its sequence number doesn't match the expected sequence number
        print(f"Discarded packet {recv_seq}")

 # Description: 
 # Runs the client
 # Creates a socket and creates a data array using readDataFromFile()
 # Initiates handshake to ensure a good connection
 # Starts appropriate client based on system argument
 # After client is done running, prints throughput and total amount of bytes sent.

def client():
    clientSocket = socket(AF_INET, SOCK_DGRAM)  # Create a UDP socket for the client
    sent_bytes = 0

    dataArr = readDataFromFile()    # Read data from a file and store it in an array

    # Check if the data array is empty, if yes, exit.
    if(not len(dataArr) > 0):
        print("The specified file is empty")
        sys.exit()

    handshake = clientHandshake(clientSocket)   # Perform the client-side handshake

    # Check if the handshake was unsuccessful, if yes, exit
    if not handshake:
        clientSocket.close()
        sys.exit()
    
    start_time = time.time()    # Record the start time for calculating throughput
    
    
    sent_bytes = goBackNClient(clientSocket, dataArr)
    

    end_time = time.time()  # Record the end time for calculating throughput
    
    if(not args.testCase):
        # Check if a test case was not specified
        throughput = calculateThroughput(start_time, end_time, sent_bytes)
        print("Sent bytes:", sent_bytes)
        print(f'{throughput:.2f} Mbps')
 
 # Description: 
 # Runs the server
 # Creates a socket and binds to IP and port
 # Initiates handshake to ensure a good connection
 # Starts appropriate client based on system argument
 # sets filename and path to write to
 # Starts appropriate server method based on system arguments
 # After server is done running, prints throughput and total amount of bytes sent.

def server():
    serverSocket = socket(AF_INET, SOCK_DGRAM)      # Create a UDP socket for the server
    serverIP = str(args.serverIP)
    serverPort = args.port

    global expected_seq_num
    global testCase
    global skipped_ack
    global recv_buffer

    received_bytes = 0  # Counter for the total number of received bytes
    start_time = None       # Variable to store the start time of the transmission

    try:
        serverSocket.bind((serverIP, serverPort))       # Bind the server socket to the specified IP and port, exit if it fails
    except:
        print('Bind failed')
        sys.exit()

    header, clientAddress = serverSocket.recvfrom(header_size)  # Receive the initial handshake packet from the client
    #Receives SYN from client, and sends SYN ACK back
    handshake = serverHandshake(serverSocket, header, clientAddress)         # Perform the server-side handshake

    if not handshake:   # Exit if handshake fails
        serverSocket.close()
        sys.exit()

    file_path = args.file   # Get the file path from the command line arguments
    file = open(f'{file_path}', "wb")       # Open the file in write binary mode for writing the received data

    expected_seq_num = 0
    testCase = args.testCase
    skipped_ack = False
    recv_buffer = []    # Buffer to store received packets for selective repeat method

    while True:
        #Common for all 3 methods
        received_packet, clientAddress = serverSocket.recvfrom(packet_size)
        header = received_packet[:header_size]
        data = received_packet[header_size:]    # Extract the data from the received packet
        recv_seq, recv_ack, recv_flags = parse_header(header)  # Parse the header fields

        if len(received_packet) == header_size:
            #FIN flag is set
            if(recv_flags & 2) == 2:
                print("Recived FIN")        # Indicates that the server received a FIN packet from the client
                end_time = time.time()      # Record the end time of the transmission
                break
            # If the received packet is the ack for the handshake packet, skip
            else:
                start_time = time.time()        # Record the start time of the transmission
                continue

        gbnSwServer(serverSocket, clientAddress, file, recv_seq, data)
             # Else run selective-repeat server

        received_bytes += len(received_packet[header_size:])
    
        
    restructFile(file)
   
    if(not args.testCase and start_time is not None):       
        # Calculate the throughput
        throughput = calculateThroughput(start_time, end_time, received_bytes)
        print("Received bytes:", received_bytes)
        print(f'{throughput:.2f} Mbps')
    # Close socket connection
    serverSocket.close()

 # Description: 
 # Main
 # parses all the system arguments and prints accordingly if they are written wrong, or if help is asked for.
 # Runs server or client based on system arguments
 # Informs user that the application must run in either server or client if both or neither are used.

def main ():
    global args

    parser = argparse.ArgumentParser(description='Optional arguments', epilog='End of help')
    
    parser.add_argument('-s', '--server', action='store_true', help='Runs in server mode')
    parser.add_argument('-c', '--client', action='store_true', help='Runs in client mode')
    parser.add_argument('-i', '--serverIP', type=check_IP, default='127.0.0.1', help='Server IP to bind to. Must use dotted decimal notation')
    parser.add_argument('-p', '--port', type=check_port, default=8080, help='Port number to listen on/connect to. Must be in the range [1024, 65535]')
    parser.add_argument('-t', '--testCase', type=check_testCase, choices=('skip_ack', 'skip_seq_num'), help='Testcases to show the efficiency of the code')
    parser.add_argument('-w', '--windowSize', type=check_windowSize, choices=(3, 5, 10), default=5, help='Window size used for reliable transmission with GBN or SR')
    parser.add_argument('-f', '--file', required=True, help='File to transfer (client) and file to be saved (server)')

    args = parser.parse_args()

    if (args.server and not args.client): # Run in server if -s or --server is specified
        server()
    elif (args.client and not args.server): # run in client if -c or --client is specified
        client()
    else:
        print('Error: you must run either in server or client mode')    # print error and exit if both/neither client and server are specified
        sys.exit()

if __name__ == '__main__':
    main()