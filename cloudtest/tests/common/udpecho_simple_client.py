from socket import *
import time
import sys


def get_time():
    return int(round(time.time() * 1000))

def main(remote_host, recieve_host):
    # What's your IP address and witch port should we use?
    #recieve_host = '192.168.121.213'
    recieve_port = 50000

    # What's the remote host's IP address and witch port should we use?
    #remote_host = '192.168.121.90'
    remote_port = 50000

    # Setup a UDP socket
    # Notice the use of SOCK_DGRAM for UDP packets
    serverSocket = socket(AF_INET, SOCK_DGRAM)
    # Assign IP address and port number to socket
    serverSocket.settimeout(0.001)
    serverSocket.bind((recieve_host, recieve_port))

    last_num = 1
    timeoutnum = 0
    while True:
        try:
            message, address = serverSocket.recvfrom(remote_port)
            msg = message.split(' ')
            num = msg[1]
            # print 'num is' + num
            if int(num) - last_num != 1:
                print 'Recieve: ' + message
            last_num = int(num)
        except Exception, e:
            timeoutnum += 1
            print "TIME OUT " + str(timeoutnum)


if __name__ == '__main__':
    print sys.argv

    main(sys.argv[1], sys.argv[2])

