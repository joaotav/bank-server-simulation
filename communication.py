import socket
import struct

def gen_key(size):
    key = "a" * size
    return key

class SocketReadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def socket_read_n(sock, n):
    buf = ''
    while n > 0:
        data = sock.recv(n)
        if data == '':
            raise SocketReadError('unexpected connection close')
        buf += data
        n -= len(data)
    return buf

def send_message(sock, message):
    msg = message.SerializeToString()
    packed_len = struct.pack('>L', len(msg))
    sock.sendall(packed_len + msg)

def get_message_by_type(sock, msgtype):
    len_buf = sock.recv(4)
    msg_len = struct.unpack('>L', len_buf)[0]
    msg_buf = sock.recv(msg_len)
    msg = msgtype()
    msg.ParseFromString(msg_buf)
    return msg

def recv_message(sock):
    len_buf = socket_read_n(sock, 4)
    msg_len = struct.unpack('>L', len_buf)[0]
    msg_buf = socket_read_n(sock, msg_len)
    return msg_buf
