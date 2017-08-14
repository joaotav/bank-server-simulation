# -*- coding: utf-8 -*-
import os
import sys
import getopt
import socket
import threading
import traceback
import ssl
import time
import info_pb2 as data
import datetime

from random import choice
from Crypto import Random
from Crypto.Cipher import AES
from secretsharing import SecretSharer
from secretsharing import PlaintextToHexSecretSharer
from communication import (
    send_message, recv_message, gen_key, SocketReadError
)

class Services(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        # Cria o descritor do socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.data_server_ports = [5001,5002,5003,5004]

    def listen(self):
        # 'Escuta' as conexões dirigidas ao socket
        self.sock.listen(10)
        while True:
            try:
                print("[=] Aguardando conexões...")
                # Aceita conexões solicitadas
                client, address = self.sock.accept()
                client.settimeout(60)
                # Envolve o descritor do socket em uma conexão SSL
                client_sock = ssl.wrap_socket(client,
                server_side=True, certfile="server.crt", keyfile="server.key")
                # Define a estrutura da mensagem protobuf
                print "[+] Cliente {} conectado".format(address)
                msg = data.Operation()
                # Recebe a primeira mensagem do cliente
                msg_buf = recv_message(client_sock)
                msg.ParseFromString(msg_buf)
                # Se o servidor checar a existência da conta, e a mesma existir
                if self.begin_transaction(msg) == '1':
                    client_sock.send('1')
                    # De acordo com o tipo da mensagem, iniciar a sequência de operações
                    if msg.type == 'withdraw':
                        threading.Thread(target = self.withdraw, args = (client_sock,address,msg,)).start()
                    elif msg.type == 'deposit':
                        threading.Thread(target = self.deposit, args = (client_sock,address,msg,)).start()
                    elif msg.type == 'transfer':
                        threading.Thread(target = self.transfer, args = (client_sock,address,msg,)).start()
                    elif msg.type == 'payment':
                        threading.Thread(target = self.payment, args = (client_sock,address,msg,)).start()
                    elif msg.type == 'check_balance':
                        threading.Thread(target = self.balance, args = (client_sock,address,msg,)).start()
                    elif msg.type == 'statement':
                        threading.Thread(target = self.statement, args = (client_sock,address,msg,)).start()
                else:
                    # Se a conta não existir
                    client_sock.send('0')
                    client_sock.close()

            except (KeyboardInterrupt, SystemExit):
                print("[-] Finalização solicitada, encerrando...")
                raise SystemExit

    def begin_transaction(self, msg):
        # Função que checa a existência da conta nos servidores de dados
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
        cert_reqs=ssl.CERT_REQUIRED)
        # Variável para testar a conexão
        not_connected = True
        while not_connected:
            try:
                server_sock.connect(('127.0.0.1', choice(self.data_server_ports)))
                not_connected = False
            except:
                print ('[-] Erro de conexão, tentando outro servidor...')
        print ('[+] Conexão com o servidor de dados estabelecida')
        # Envia a mensagem com os dados para que o servidor cheque a existência da conta
        if self.acc_exists(server_sock, msg):
            # Prosseguir com a operação
            return '1'
        else:
            return '0'

    def withdraw(self, client_sock, address, msg):
        # Função que realiza o saque de dinheiro
        amount = data.Amount()
        # Recebe o valor da transação
        msg_buf = recv_message(client_sock)
        amount.ParseFromString(msg_buf)
        balance = self.request_balance(msg)
        # Se o cliente possui mais saldo do que o saque solicitado
        if balance >= amount.amount:
            # Saldo suficiente, realiza a operação
            # Subtrai o saque do saldo atual
            balance = balance - amount.amount
            self.update_balance(msg, str(balance))
            # Avisa o cliente que a operação teve sucesso
            client_sock.send('1')
        else:
            # Saldo insuficiente, avisa o cliente
            # Envia '0' para o cliente
            client_sock.send('0')

        return


    def deposit(self, client_sock,address,msg):
        # Função que realiza o depósito de dinheiro
        amount = data.Amount()
        # Recebe o valor do depósito
        msg_buf = recv_message(client_sock)
        amount.ParseFromString(msg_buf)
        balance = self.request_balance(msg)
        # Adiciona o valor do depósito ao saldo atual
        balance = balance + amount.amount
        self.update_balance(msg, str(balance))
        # Avisa o cliente que a operação teve sucesso
        client_sock.send('1')
        self.store_history(msg, amount.amount)
        return

    def transfer(self, client_sock,address,msg):
        # Função que realiza transferência entre contas
        msg = data.Operation()
        msg_buf = recv_message(client_sock)
        msg.ParseFromString(msg_buf)
        dest_msg = data.Operation()
        dest_msg.type = 'transfer'
        dest_msg.bank = msg.destBank
        dest_msg.agency = msg.destAgency
        dest_msg.account = msg.destAccount
        # Retorna 1 se a conta de destino existe
        if self.begin_transaction(dest_msg):
            # Envia mensagem para o cliente prosseguir
            client_sock.send('1')
            amount = data.Amount()
            msg_buf = recv_message(client_sock)
            amount.ParseFromString(msg_buf)
            origin_balance = self.request_balance(msg)
            dest_balance = self.request_balance(dest_msg)
            if origin_balance >= amount.amount:
                # Saldo suficiente, realiza a operação
                # Subtrai o saque do saldo atual
                origin_balance = origin_balance - amount.amount
                dest_balance = dest_balance + amount.amount
                self.update_balance(msg, str(origin_balance))
                self.update_balance(dest_msg, str(dest_balance))
                # Avisa o cliente que a operação teve sucesso
                client_sock.send('1')
                self.store_history(dest_msg, amount.amount)
            else:
                # Saldo insuficiente, avisa o cliente
                # Envia '0' para o cliente
                client_sock.send('0')
        else:
            # A conta de destino não existe
            client_sock.send('0')



    def payment(self, client_sock, address, msg):
        # Função que realiza o pagamento de títulos
        msg = data.Operation()
        msg_buf = recv_message(client_sock)
        msg.ParseFromString(msg_buf)
        # Verifica se o título existe
        if self.slip_exists(msg):
            client_sock.send('1')
            # Título existe, verificar se já foi pago
            value, interest, status = self.slip_info(msg)
            if status:
                # Já foi pago, enviar 0
                client_sock.send('0')
            else:
                # Não foi pago, enviar 1
                client_sock.send('1')
                client_sock.send(str(value))
                acc_balance = self.request_balance(msg)
                # Se o cliente seguiu em frente com a operação
                if client_sock.recv() == '1':
                    if acc_balance >= value:
                        # A conta tem saldo suficiente para pagar o título
                        acc_balance = acc_balance - value
                        self.update_balance(msg, str(acc_balance))
                        self.update_slip_status(msg, value, interest)
                        self.store_history(msg, value)
                        client_sock.send('1')
                    else:
                        # A conta não tem saldo suficiente para pagar o título
                        client_sock.send('0')
                else:
                    # Cliente cancelou a operação
                    return
        else:
            client_sock.send('0')

    def balance(self, client_sock, address, msg):
        # Função que verifica o saldo da conta
        acc_balance = self.request_balance(msg)
        client_sock.send(str(acc_balance))
        self.store_history(msg)

    def statement(self, client_sock, address, msg):
        # Função que requisita aos servidores de dados o histórico da conta
        st = self.request_history(msg)
        client_sock.send(st)

    def acc_exists(self, server_sock, msg):
        # Função que verifica a existência de contas, similar ao begin_transaction
        # Porém usado em situações diferentes
        # Envia mensagem com os dados da conta para o servidor
        server_sock.send('acc_exists')
        send_message(server_sock, msg)
        # Se a conta existe retorna 1, senão retorna 0
        reply = server_sock.recv()
        return int(reply)

    def request_balance(self, msg):
        # Função que requisita o saldo para os servidores de dados
        ''' Conecta com todos os servidores de dados e solicita
        as shares referentes aos dados do cliente '''
        shares = []
        for port in self.data_server_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', int(port)))
                ssl_sock.sendall('balance')
                send_message(ssl_sock, msg)
                share = ssl_sock.recv()
                shares.append(share)
            except:
                print ("Erro de conexão")
                #ssl_sock.close()
        balance = PlaintextToHexSecretSharer.recover_secret(shares[0:3])
        #ssl_sock.close()
        return int(balance)

    def slip_exists(self, msg):
        # Função que verifica nos servidores de dados se o título existe
        # Envia mensagem com os dados da conta para o servidor
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
        cert_reqs=ssl.CERT_REQUIRED)
        # Variável para testar a conexão
        not_connected = True
        while not_connected:
            try:
                server_sock.connect(('127.0.0.1', choice(self.data_server_ports)))
                not_connected = False
            except:
                print ('[-] Erro de conexão, tentando outro servidor...')
        print ('[+] Conexão com o servidor de dados estabelecida')
        server_sock.send('slip_exists')
        send_message(server_sock, msg)
        # Se a conta existe retorna 1, senão retorna 0
        reply = server_sock.recv()
        return int(reply)

    def update_balance(self, msg, balance):
        # Função que envia para os servidores de dados as informações atualizadas
        # do saldo da conta
        try:
            shares = PlaintextToHexSecretSharer.split_secret(balance, 3, 4)
            share_id = 0
            for port in self.data_server_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', port))
                ssl_sock.sendall('update_balance')
                send_message(ssl_sock, msg)
                ssl_sock.send(shares[share_id])
                share_id += 1
        except:
            traceback.print_exc()


    def store_history(self, msg, amount = 0):
        # Função que envia para o servidor de dados as operações realizadas na conta
        if msg.type == 'check_balance':
            history = '{} - Verificação de saldo da conta'.format(datetime.datetime.now().strftime("%A, %d %B %Y %I:%M:%S %p"))
        elif msg.type == 'deposit':
            history = '{} - Recebeu depósito de: R$ {},00'.format(datetime.datetime.now().strftime("%A, %d %B %Y %I:%M:%S %p"), \
            amount)
        elif msg.type == 'transfer':
            history = '{} - Transferência - Origem: Banco {} - Agência {} - Conta {}; Valor: R$ {},00' \
            .format(datetime.datetime.now().strftime("%A, %d %B %Y %I:%M:%S %p"), msg.bank, msg.agency, msg.account, \
            amount)
        elif msg.type == 'payment':
            history = '{} - Pagamento de título - ID: {}; Valor: R$ {},00'.format(datetime.datetime.now().strftime("%A, %d %B %Y %I:%M:%S %p"), \
            msg.id, amount)
        try:
            for port in self.data_server_ports:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', port))
                ssl_sock.sendall('store_history')
                send_message(ssl_sock, msg)
                ssl_sock.send(history)
        except:
            traceback.print_exc()


    def request_history(self, msg):
        for port in self.data_server_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', int(port)))
                ssl_sock.sendall('history')
                send_message(ssl_sock, msg)
                history = ssl_sock.recv()
            except Exception as err:
                print err
        return history

    def slip_info(self, msg):
        ''' Conecta com todos os servidores de dados e solicita
        as shares referentes aos dados título '''
        shares = []
        for port in self.data_server_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', int(port)))
                ssl_sock.sendall('slip_info')
                send_message(ssl_sock, msg)
                share = ssl_sock.recv()
                shares.append(share)
            except:
                print ("Erro de conexão")
                #ssl_sock.close()
        # Reconstrói a informação, que consiste nos dados da mensagem protobuff
        # do título em formato serializado.
        info = PlaintextToHexSecretSharer.recover_secret(shares[0:3])
        value = info.split(';')[1]
        interest = info.split(';')[2]
        status = info.split(';')[3]
        return int(value), int(interest), int(status)

    def update_slip_status(self, msg, value, interest):
        # Muda o status do título para pago
        data = '{};{};{};{}'.format(msg.id, value, interest, 1)
        shares = PlaintextToHexSecretSharer.split_secret(data, 3, 4)
        share_id = 0
        for port in self.data_server_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
                cert_reqs=ssl.CERT_REQUIRED)
                ssl_sock.connect(('127.0.0.1', int(port)))
                ssl_sock.sendall('slip_status')
                send_message(ssl_sock, msg)
                ssl_sock.send(shares[share_id])
                share_id += 1
            except:
                print ("Erro de conexão")

def args_help():
    print os.path.basename(sys.argv[0]) + ' -h -p <Port> '

def main(argv):
    try:
        opts, args = getopt.getopt(argv,"h:p:",["Port=",])
    except:
        args_help()
        sys.exit(2)

    PORT = 0
    try:
        for opt, arg in opts:
            if opt == '-h':
                args_help()
                sys.exit(1)
            elif opt in ('-p', '--Port'):
                PORT = int(arg)
    except:
        args_help()
        sys.exit(2)

    if PORT == 0:
        args_help()
        sys.exit(2)

    Services('', int(PORT)).listen()


if __name__ == "__main__":
    main(sys.argv[1:])
