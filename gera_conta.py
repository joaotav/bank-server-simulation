import info_pb2 as data
from secretsharing import SecretSharer
from secretsharing import PlaintextToHexSecretSharer
import struct
import os

for bank in ['banrisul', 'america']:
	for agency in ['agencia1', 'agencia2']:
		for account in ['100', '101']:
			shares = PlaintextToHexSecretSharer.split_secret('1000', 3, 4)
			for share in range(len(shares)):
				with open (os.path.join('data' + str(share + 1),bank,agency,account,'saldo.dat'), 'w') as file:
					file.write(shares[share])
