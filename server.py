import socket
import protocol
import os
import hashlib

def calcular_hash_arquivo(caminho):

    hash_md5 = hashlib.md5()

    with open(caminho, 'rb') as arquivo:

        while True:
            bloco = arquivo.read(protocol.TAM_PAYLOAD)

            if not bloco:
                break

            hash_md5.update(bloco)
    
    return hash_md5.hexdigest()


HOST = '127.0.0.1'
#PORT = 65432

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # criando um socket UDP - primeiro arg é o IPV4 , segundo arg é o tipo de socket (UDP)
print(f"Socket criado!\n")

sock.bind((HOST, protocol.PORTA)) # associando o socket a uma porta e endereço
print(f"Servidor UDP iniciado e escutando em {HOST}:{protocol.PORTA}\n")
print(f"//--------------------------------------------//\n")


while True:

    #dados, endereco = sock.recvfrom(1024) # recebendo dados do cliente , buffer de 1024 bytes no recvfrom
    
    #sock.sendto(resposta.encode('utf-8'), endereco) # enviando a resposta, encode codifica a string para bytes, sendto envia os bytes para o endereço do cliente

    pacote, endereco = sock.recvfrom(protocol.BUFFER) # recebendo dados do cliente , buffer é o tamandho do paylaoad bytes no recvfrom

    tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(pacote) # desmontando o pacote recebido 

    if(tipoPacote != protocol.TipoPacote.GET):
        print("Pacote recebido nao eh do tipo GET")
        continue



    if(tipoPacote == protocol.TipoPacote.GET): #caso 1 GET
        
        nome = os.path.basename(dados.decode('utf-8'))   
        caminho = os.path.join("files", nome)   
        print(f"Mensagem recebida de {endereco}: pedindo {nome}\n")

    if not os.path.isfile(caminho):
        print(f"Arquivo {nome} nao encontrado por aqui\n")
        print(f"//--------------------------------------------//\n")
        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ERROR, 0, b"Arquivo NAO encontrado"), endereco)
        continue

    print(f"Arquivo {caminho} encontrado por aqui\n")

    tamanho = os.path.getsize(caminho)
    print(f"Tamanho do arquivo: {tamanho} bytes\n")

    numPacotes = tamanho // protocol.TAM_PAYLOAD

    if tamanho % protocol.TAM_PAYLOAD > 0:
        numPacotes += 1

    print(f"Numero de pacotes a serem enviados: {numPacotes}\n")

    hash_arquivo = calcular_hash_arquivo(caminho)
    print(f"Hash do arquivo: {hash_arquivo}\n")
    conteudoInfo = f"{numPacotes};{hash_arquivo}"      # monta o texto "8588;d0ae6a9b..."
    
    sock.sendto(protocol.montar_pacote(protocol.TipoPacote.INFO, 0, conteudoInfo.encode('utf-8')), endereco)

    with open(caminho,'rb') as arquivo:

        for i in range(numPacotes):

            pedaco = arquivo.read(protocol.TAM_PAYLOAD)
            dado = protocol.montar_pacote(protocol.TipoPacote.DATA, i, pedaco)
            sock.sendto(dado, endereco)

            resposta, _ = sock.recvfrom(protocol.BUFFER)
            ack, _, _, _ = protocol.desmontar_pacote(resposta)
            if ack != protocol.TipoPacote.ACK:
                print("ACK nao recebido, re-enviando pacote!\n")
                continue

        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.EOF, 0, b""), endereco)
        print(f"Arquivo {nome} enviado com sucesso para {endereco}!\n")
        print(f"//--------------------------------------------//\n")
    
    
sock.close() # fechando o socket