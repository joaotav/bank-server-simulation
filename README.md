# bank-transactions-simulation
This code simulates a bank, some accounts and bank servers. It allows deposits, transactions, transfers, and payments to be made. You can also view previous operations, when they ocurred, how much money was withdrawed, deposited, whom it was transfered to, etc..
The Servers use TLS and AES-256 for secure communication, they also store their data in pieces, using secret-sharing, which allows information to be broken in shares, which then can be used to reconstruct the original data, only when a determined amount of the shares is held.
The messages sent by the servers follow Protocol Buffers format.
