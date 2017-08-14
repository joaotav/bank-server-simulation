# -*- coding: utf-8 -*-
import os
import sys
import getopt
import socket
import threading
import ssl
import time
import info_pb2 as data

from Crypto import Random
from Crypto.Cipher import AES
from secretsharing import SecretSharer
from secretsharing import PlaintextToHexSecretSharer
# Importa as funções do arquivo communication
from communication import (
    send_message, recv_message, gen_key, SocketReadError
)

#Chave padrão para uso na geração de MACs
global KEY
KEY = gen_key(32)


# Gerador da chave padrão, sempre a mesma na intenção de facilitar a checagem
def gen_key(size):
    return size * 'x'

# Exibe mensagem de ajuda
def args_help():
    print os.path.basename(sys.argv[0]) + ' -h -i <IP> -p <Port> '

# Inicia a transação com o servidor de aplicação
def begin_transaction(IP, PORT, msg_type):
    msg = data.Operation()
    msg.type = msg_type
    # Busca os dados básicos da conta
    get_acc_info(msg)
    # Criação do descritor do socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Criação do wrapper SSL
    ssl_sock = ssl.wrap_socket(sock, ca_certs="server.crt",
    cert_reqs=ssl.CERT_REQUIRED)
    try:
        ssl_sock.connect((IP, int(PORT)))
    except:
        print "[-] Erro ao estabelecer conexão com o servidor"
        quit()
    # Envia a mensagem com os dados básicos para checar existência da conta
    # Aguarda a resposta do servidor para prosseguir a transação
    send_message(ssl_sock, msg)
    # Se a resposta for 1, prossegue a operação
    if ssl_sock.recv() == '1':
        # Continua a operação de saque
        if msg_type == 'withdraw':
            withdraw(ssl_sock, msg)
        # Continua a operação de depósito
        elif msg_type == 'deposit':
            deposit(ssl_sock, msg)
        # Continua a operação de transferência
        elif msg_type == 'transfer':
            transfer(ssl_sock, msg)
        # Continua a operação de pagamento de título
        elif msg_type == 'payment':
            payment(ssl_sock, msg)
        # Continua a operação de saldo
        elif msg_type == 'check_balance':
            balance(ssl_sock, msg)
        # Continua a operação de extrato
        elif msg_type == 'statement':
            statement(ssl_sock, msg)

    # Se a resposta do servidor for 0, as informações da conta não foram encontradas
    else:
        print 35 * '-' + '\n\n[-] Conta inexistente.\n'
        return
    return

def get_acc_info(msg):
    ## CRIAR UMA LISTA DE CONTAS EXISTENTES ###\n
    ## Testar por erros no acesso à conta #####
    try:
        if msg.type == 'withdraw' or msg.type == 'check_balance' or msg.type == 'statement':
            msg.bank = raw_input('[=] Digite o nome do banco: ')
            while 1:
                try:
                    msg.agency = int(raw_input('[=] Digite o número da agência: '))
                    msg.account = int(raw_input('[=] Digite o número da conta: '))
                    break
                except ValueError:
                    print ("\n[-] Por favor, utilize somente números para a agência e conta.")

        elif msg.type == 'deposit':
            msg.bank = raw_input('[=] Digite o nome do banco de destino: ')
            while 1:
                try:
                    msg.agency = int(raw_input('[=] Digite o número da agência de destino: '))
                    msg.account = int(raw_input('[=] Digite o número da conta de destino: '))
                    break
                except ValueError:
                    print ("\n[-] Por favor, utilize somente números para a agência e conta.")

        elif msg.type == 'transfer':
            msg.bank = raw_input('[=] Digite o nome do banco de origem: ')
            while 1:
                try:
                    msg.agency = int(raw_input('[=] Digite o número da agência de origem: '))
                    msg.account = int(raw_input('[=] Digite o número da conta de origem: '))
                    break
                except ValueError:
                    print ("\n[-] Por favor, utilize somente números para a agência e conta.")

        elif msg.type == 'payment':
            print "[=] Digite os dados de sua conta para que seja possível efetuar o pagamento: "
            msg.bank = raw_input('[=] Digite o nome do banco: ')
            while 1:
                try:
                    msg.agency = int(raw_input('[=] Digite o número da agência: '))
                    msg.account = int(raw_input('[=] Digite o número da conta: '))
                    break
                except ValueError:
                    print ("\n[-] Por favor, utilize somente números para a agência e conta.")

    except(KeyboardInterrupt, SystemExit):
        print("\n[-] Finalização solicitada, encerrando...")
        raise SystemExit
    return

def withdraw(ssl_sock, msg):
    # Cria a estrutura da mensagem para receber o valor da transação
    amount = data.Amount()
    while True:
        try:
            amount.amount = int(raw_input('\n[=] Digite o valor que deseja sacar: '))
            if amount.amount <= 0:
                print '[-] Por favor, digite somente valores positivos.'
            else:
                break
        except:
            print '[-] Por favor, digite somente valores inteiros positivos.'
    # Envia o valor para o servidor de aplicação
    send_message(ssl_sock, amount)
    if ssl_sock.recv() == '1':
        print 35 * '-' + '\n\n[+] Operação concluída, retire seu dinheiro.\n'
    else:
        print '\n[-] Saldo insuficiente.\n'
    return


def deposit(ssl_sock, msg):
    # Cria a estrutura da mensagem para receber o valor da transação
    amount = data.Amount()
    while True:
        try:
            print '\n[=] Depósito em: \n[=] Banco: {}\n[=] Agência: {}\n[=] Conta: {}'.format(msg.bank, msg.agency, msg.account)
            amount.amount = int(raw_input('\n[=] Digite o valor que deseja depositar na conta: '))
            if amount.amount <= 0:
                print "[-] Por favor, digite somente valores positivos."
            else:
                break
        except:
            print "[-] Por favor, digite somente valores inteiros positivos."
    # Envia o valor para o servidor de aplicação
    send_message(ssl_sock, amount)
    if ssl_sock.recv() == '1':
        print 35 * '-' + '\n\n[+] Operação concluída.\n'
    return


def transfer(ssl_sock, msg):
    msg.destBank = raw_input('[=] Digite o nome do banco de destino: ')
    msg.destAgency = int(raw_input('[=] Digite o número da agência de destino: '))
    msg.destAccount = int(raw_input('[=] Digite o número da conta de destino: '))
    send_message(ssl_sock, msg)
    # Se o cliente receber 1, a conta de destino também existe
    if ssl_sock.recv() == '1':
        # Cria a estrutura da mensagem para receber o valor da transação
        amount = data.Amount()
        while True:
            try:
                print '\n[=] Transferência para: \n[=] Banco: {}\n[=] Agência: {}\n[=] Conta: {}'.format(msg.destBank, \
                msg.destAgency, msg.destAccount)
                amount.amount = int(raw_input('\n[=] Digite o valor que deseja transferir para a conta: '))
                if amount.amount <= 0:
                    print "[-] Por favor, digite somente valores positivos."
                else:
                    break
            except:
                print "[-] Por favor, digite somente valores inteiros positivos."
        # Envia o valor para o servidor de aplicação
        send_message(ssl_sock, amount)
        if ssl_sock.recv():
            print "\n[+] Operação concluída."
            return
        else:
            print "[+] Saldo da conta de origem é insuficiente."
            return
    else:
        print "[-] Conta de destino inexistente."
        return

def payment(ssl_sock, msg):
    msg.id = int(raw_input("\n[=] Digite o número do título a ser pago: "))
    send_message(ssl_sock, msg)
    if ssl_sock.recv() == '1':
        # Título encontrado no servidor de dados
        if ssl_sock.recv() == '1':
            # O título ainda não foi pago, realizar pagamento com os dados
            # da conta
            value = ssl_sock.recv()
            ans = ''
            while ans.lower() != 'y' and ans.lower() != 'n':
                ans = raw_input("\n[=] Título {} - Valor: R$ {},00 \n[=] Deseja efetuar o pagamento? [y/n]\n".format(msg.id, value))
            if ans.lower() == 'y':
                ssl_sock.send('1')
            elif ans.lower() == 'n':
                ssl_sock.send('0')
                print "\n[-] Operação cancelada.\n"
                return
            if ssl_sock.recv() == '1':
                print '\n[+] Pagamento efetuado.'
            else:
                print '\n[-] Saldo insuficiente para realizar o pagamento.'
        else:
            print '\n[-] O Título já foi pago.'

    else:
        # Título não encontrado no servidor de dados
        print "\n[-] Título inexistente."

def balance(ssl_sock, msg):
    # Requisita ao servidor o saldo da conta
    acc_balance = ssl_sock.recv()
    print
    print 35 * '-' + '\n\n[+] Saldo disponível: R$ {},00\n'.format(acc_balance)

def statement(ssl_sock,msg):
    # Requisita ao servidor e exibe o extrato de operações da conta
    st = ssl_sock.recv()
    st = st.split('\n')

    print 35 * '-' + "\n[+] Histórico de operações:\n"
    for line in st[:-1]:
        print "[+] {} \n".format(line)

def main(argv):
    global IP
    global PORT
    IP = ''
    PORT = 0
    try:
        opts, args = getopt.getopt(argv,"hi:p:",["IP=", "Port="])
    except getopt.GetoptError:
        args_help()
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            args_help()
            sys.exit(1)
        elif opt in ('-i', '--IP'):
            IP = arg
        elif opt in ('-p', '--Port'):
            PORT = arg

    if IP == '' or PORT == 0:
        args_help()
        sys.exit(1)



    option_list = ['withdraw', 'deposit', 'transfer', 'payment', 'check_balance', 'statement']
    while True:
        print 35 * '-'
        print "[+] Selecione a operação desejada:\n"
        print "[1] Saque"
        print "[2] Depósito"
        print "[3] Transferência"
        print "[4] Pagamento de título"
        print "[5] Consulta de saldo"
        print "[6] Gerar extrato"
        print "[7] Sair do sistema"

        try:
            op_choice = int(raw_input("\n[+] Selecione uma opção: "))
        except:
            print '\n[-] Por favor, selecione uma opção válida.'
            continue
        if op_choice >= 1 and op_choice <= 6:
            begin_transaction(IP, PORT, option_list[op_choice - 1])
        elif op_choice == 7:
            exit()
        else:
            print '\n[-] Por favor, selecione uma opção válida.'



if __name__ == "__main__":
    main(sys.argv[1:])
