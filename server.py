import socket
import protocol
import os
import hashlib
import threading

def calcular_hash_arquivo(caminho):

    hash_md5 = hashlib.md5()

    with open(caminho, 'rb') as arquivo:

        while True:
            bloco = arquivo.read(protocol.TAM_PAYLOAD)

            if not bloco:
                break

            hash_md5.update(bloco)

    return hash_md5.hexdigest()

def atender_cliente(nome_arquivo, endereco):

    sockCliente = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sockCliente.settimeout(protocol.TIMEOUT)

    nome = os.path.basename(nome_arquivo)
    caminho = os.path.join("files", nome)
    print(f"Mensagem recebida de {endereco}: pedindo {nome}\n")

    if not os.path.isfile(caminho):
        print(f"Arquivo {nome} nao encontrado por aqui\n")
        print(f"//--------------------------------------------//\n")
        sockCliente.sendto(protocol.montar_pacote(protocol.TipoPacote.ERROR, 0, b"Arquivo NAO encontrado"), endereco)
        sockCliente.close()
        return

    print(f"Arquivo {caminho} encontrado por aqui\n")

    tamanho = os.path.getsize(caminho)
    print(f"[{nome} -> {endereco}] Tamanho do arquivo: {tamanho} bytes\n")

    numPacotes = tamanho // protocol.TAM_PAYLOAD

    if tamanho % protocol.TAM_PAYLOAD > 0:
        numPacotes += 1

    print(f"[{nome} -> {endereco}] Numero de pacotes a serem enviados: {numPacotes}\n")

    hash_arquivo = calcular_hash_arquivo(caminho)
    print(f"[{nome} -> {endereco}] Hash do arquivo: {hash_arquivo}\n")
    conteudoInfo = f"{numPacotes};{hash_arquivo}"

    sockCliente.sendto(protocol.montar_pacote(protocol.TipoPacote.INFO, 0, conteudoInfo.encode('utf-8')), endereco)

    with open(caminho,'rb') as arquivo:

        sockCliente.settimeout(protocol.TIMEOUT)

        for i in range(numPacotes):

            pedaco = arquivo.read(protocol.TAM_PAYLOAD)
            dado = protocol.montar_pacote(protocol.TipoPacote.DATA, i, pedaco)
            tentativas = 0

            while(tentativas < protocol.MAX_TENTATIVAS):

                sockCliente.sendto(dado, endereco)

                try:
                    resposta, _ = sockCliente.recvfrom(protocol.BUFFER)
                    seraUmAck,seq,_,_ = protocol.desmontar_pacote(resposta)
                    if (seraUmAck == protocol.TipoPacote.ACK and seq == i):
                        break
                except socket.timeout:
                    tentativas += 1
                    print(f"[{nome} -> {endereco}] Timeout no pacote {i}, re-enviando...\n")
                    if tentativas >= protocol.MAX_TENTATIVAS:
                        break
            
            if(tentativas >= protocol.MAX_TENTATIVAS):
                break

        if(tentativas >= protocol.MAX_TENTATIVAS):
            print(f"Falha ao enviar o arquivo {nome} para {endereco} apos {protocol.MAX_TENTATIVAS} tentativas\n")
        else:
            sockCliente.sendto(protocol.montar_pacote(protocol.TipoPacote.EOF, 0, b""), endereco)
            print(f"Arquivo {nome} enviado com sucesso para {endereco}!\n")
            print(f"//--------------------------------------------//\n")

        sockCliente.close()

HOST = '127.0.0.1'

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"Socket criado!\n")

sock.bind((HOST, protocol.PORTA))
print(f"Servidor UDP iniciado e escutando em {HOST}:{protocol.PORTA}")
print(f"//--------------------------------------------//\n")

while True:

    pacote, endereco = sock.recvfrom(protocol.BUFFER)

    tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(pacote)

    if(tipoPacote != protocol.TipoPacote.GET):
        print("Pacote recebido nao eh do tipo GET")
        continue

    thread = threading.Thread(target=atender_cliente, args=(dados.decode('utf-8'), endereco))
    thread.start()

sock.close()
