from socket import *
import time
import random
import sys


def get_time():
    return int(round(time.time() * 1000))


def main(remote_host, recieve_host):
    # What's your IP address and witch port should we use?
    #recieve_host = '192.168.121.212'
    recieve_port = 50000

    # What's the remote host's IP address and witch port should we use?
    #remote_host = '192.168.121.91'
    remote_port = 50000

    # Create a UDP socket
    # Notice the use of SOCK_DGRAM for UDP packets
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    # Assign IP address and port number to socket
    serverSocket.bind((recieve_host, recieve_port))

    sequence_number = 0
    start = get_time()
    start_send = start
    while True:
        sequence_number += 1
        current = get_time()
        if current - start_send > 60 * 1000:
            break
        duration = current - start
        message = 'PING ' + str(sequence_number) + ' ' + str(duration)
        serverSocket.sendto(message, (remote_host, remote_port))
        print 'Send ' + message + ' to ' + remote_host + ':' + str(remote_port)
        time.sleep(0.0001)


if __name__ == '__main__':
    print sys.argv
    main(sys.argv[1], sys.argv[2])




