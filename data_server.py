# -*- coding: utf-8 -*-
import sys
import argparse
import socket
import threading
import ssl
import traceback
import logging
import select
import info_pb2 as data
import os

from communication import (
    send_message, recv_message, gen_key, SocketReadError
)
from Crypto import Random
from Crypto.Cipher import AES
from secretsharing import SecretSharer
from secretsharing import PlaintextToHexSecretSharer

def client_handler(client_sock, address, server_id):
    ''' client_sock é o servidor de aplicação '''
    op = client_sock.recv()
    msg = data.Operation()
    msg_buf = recv_message(client_sock)
    msg.ParseFromString(msg_buf)

    # Verifica a operação solicitada para prosseguir as operações
    if op == 'acc_exists':
        if acc_exists(msg, server_id):
            client_sock.send('1')
        else:
            client_sock.send('0')

    elif op == 'balance':
        # Busca a share do cliente no servidor atual e envia para o servidor de aplicação
        share = fetch_data(msg, server_id, 'balance')
        client_sock.send(share)

    elif op == 'history':
        history = fetch_data(msg, server_id, 'history')
        client_sock.send(history)

    elif op == 'update_balance':
        data_share = client_sock.recv()
        store_data(msg, data_share, server_id, 'balance')

    elif op == 'store_history':
        data_share = client_sock.recv()
        store_data(msg, data_share, server_id, 'history')

    elif op == 'slip_exists':
        if slip_exists(msg, server_id):
            client_sock.send('1')
        else:
            client_sock.send('0')

    elif op == 'slip_info':
        data_share = fetch_data(msg, server_id, 'slip')
        client_sock.send(data_share)

    elif op == 'slip_status':
        data_share = client_sock.recv()
        store_data(msg, data_share, server_id, 'slip_paid')

    return


def acc_exists(msg, server_id):
    if os.path.exists(os.path.join('data1', msg.bank.lower(), 'agencia' + str(msg.agency), str(msg.account))):
        # Se o diretório existe, envia uma mensagem para o servidor de aplicação prosseguir
        # com as comunicações
        return 1
    else:
        # A conta não existe, então envia indicador de fim das comunicações
        # e sai da função
        return 0

def fetch_data(msg, server_id, dtype):
    # Função que busca as shares armazenadas nos servidores para enviar ao servidor
    # de aplicação
    if dtype == 'balance':
        with open(os.path.join('data' + str(server_id), msg.bank.lower(), 'agencia' + str(msg.agency),
        str(msg.account), 'saldo' + '.dat' )) as file:
            data = file.read()
        return data

    elif dtype == 'history':
        with open(os.path.join('data' + str(server_id), msg.bank.lower(), 'agencia' + str(msg.agency),
        str(msg.account), 'history' + '.dat' )) as file:
            data = file.read()
        return data

    elif dtype == 'slip':
        banks = ['america', 'banrisul']
        with open(os.path.join('data' + str(server_id), banks[int(str(msg.id)[0]) - 1], 'titulos', \
        'titulo' + str(msg.id) + '.dat')) as file:
            data = file.read()
        return data

def store_data(msg, data_share, server_id, dtype):
    # Função que armazena as shares recebidas do servidor de aplicação
    # O armazenamento varia em função do tipo de dado que está sendo recebido
    if dtype == 'balance':
        with open (os.path.join('data' + str(server_id), msg.bank.lower(), 'agencia' + str(msg.agency),
        str(msg.account), 'saldo' + '.dat' ), 'w') as file:
            file.write(data_share)
    elif dtype == 'history':
        with open (os.path.join('data' + str(server_id), msg.bank.lower(), 'agencia' + str(msg.agency),
        str(msg.account), 'history' + '.dat' ), 'a+') as file:
            file.write(data_share + '\n')
    elif dtype == 'slip_paid':
        banks = ['america', 'banrisul']
        with open(os.path.join('data' + str(server_id), banks[int(str(msg.id)[0]) - 1], 'titulos', \
        'titulo' + str(msg.id) + '.dat'),'w') as file:
            file.write(data_share)

    return


def slip_exists(msg, server_id):
    '''
    Verifica se o título a ser pago existe
    O primeiro digito do titulo indica o banco no qual foi gerado
    1: America
    2: Banrisul
    Pode retornar 2 valores diferentes:
    0: Título não existe
    1: Titulo existe
    '''
    banks = ['america', 'banrisul']
    # Verifica a existência do título no diretório do banco emissor
    if os.path.exists(os.path.join('data' + str(server_id), banks[int(str(msg.id)[0]) - 1], \
     'titulos', 'titulo' + str(msg.id) + '.dat')):
        return 1
    else:
        # Título não existe
        return 0

if __name__ == "__main__":

    CONNECTION_LIST = []
    PORT1 = 5001
    PORT2 = 5002
    PORT3 = 5003
    PORT4 = 5004

    try:
        s_socket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_socket1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_socket1.bind(("0.0.0.0", PORT1))
        s_socket1.listen(10)

        s_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_socket2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_socket2.bind(("0.0.0.0", PORT2))
        s_socket2.listen(10)

        s_socket3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_socket3.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_socket3.bind(("0.0.0.0", PORT3))
        s_socket3.listen(10)

        s_socket4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s_socket4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s_socket4.bind(("0.0.0.0", PORT4))
        s_socket4.listen(10)

        CONNECTION_LIST.append(s_socket1)
        CONNECTION_LIST.append(s_socket2)
        CONNECTION_LIST.append(s_socket3)
        CONNECTION_LIST.append(s_socket4)

        logging.info ("Servidor de dados 1 funcionando na porta %s", str(PORT1))
        logging.info ("Servidor de dados 2 funcionando na porta %s", str(PORT2))
        logging.info ("Servidor de dados 3 funcionando na porta %s", str(PORT3))
        logging.info ("Servidor de dados 4 funcionando na porta %s", str(PORT4))

        while 1:
            read_sockets,write_sockets,error_sockets = select.select(CONNECTION_LIST,[],[])

            for sock in read_sockets:

                if sock == s_socket1:
                    client, address = s_socket1.accept()
                    client_sock = ssl.wrap_socket(client,
    				server_side=True, certfile="server.crt", keyfile="server.key")
                    logging.info ("Cliente 1 (%s, %s) conectado" % address)
                    threading.Thread(target = client_handler, args = (client_sock, address, 1)).start()
                elif sock == s_socket2:
                    client, address = s_socket2.accept()
                    client_sock = ssl.wrap_socket(client,
    				server_side=True, certfile="server.crt", keyfile="server.key")
                    logging.info ("Cliente 2 (%s, %s) conectado" % address)
                    threading.Thread(target = client_handler, args = (client_sock, address, 2)).start()
                elif sock == s_socket3:
                    client, address = s_socket3.accept()
                    client_sock = ssl.wrap_socket(client,
    				server_side=True, certfile="server.crt", keyfile="server.key")
                    logging.info ("Cliente 3 (%s, %s) conectado" % address)
                    threading.Thread(target = client_handler, args = (client_sock, address, 3)).start()
                elif sock == s_socket4:
                    client, address = s_socket4.accept()
                    client_sock = ssl.wrap_socket(client,
    				server_side=True, certfile="server.crt", keyfile="server.key")
                    logging.info ("Cliente 4 (%s, %s) conectado" % address)
                    threading.Thread(target = client_handler, args = (client_sock, address, 4)).start()

        s_socket1.close()
        s_socket2.close()
        s_socket3.close()
        s_socket4.close()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Encerrando execução ...")
        pass
    except:
        traceback.print_exc()
