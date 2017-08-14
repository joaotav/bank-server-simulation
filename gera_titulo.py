import info_pb2 as data
from secretsharing import SecretSharer
from secretsharing import PlaintextToHexSecretSharer
import struct
import os

shares = PlaintextToHexSecretSharer.split_secret('2123;350;2;0', 3, 4)
for share in range(len(shares)):
	with open (os.path.join('data' + str(share + 1),'banrisul','titulos','titulo2123.dat'), 'w') as file:
		file.write(shares[share])

shares = PlaintextToHexSecretSharer.split_secret('2124;457;1;1', 3, 4)
for share in range(len(shares)):
	with open (os.path.join('data' + str(share + 1),'banrisul','titulos','titulo2124.dat'), 'w') as file:
		file.write(shares[share])

shares = PlaintextToHexSecretSharer.split_secret('1123;229;4;0', 3, 4)
for share in range(len(shares)):
	with open (os.path.join('data' + str(share + 1),'america','titulos','titulo1123.dat'), 'w') as file:
		file.write(shares[share])

shares = PlaintextToHexSecretSharer.split_secret('1124;87;2;0', 3, 4)
for share in range(len(shares)):
	with open (os.path.join('data' + str(share + 1),'america','titulos','titulo1124.dat'), 'w') as file:
		file.write(shares[share])
