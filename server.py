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
        sockCliente.close() # fechando o socket
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
    conteudoInfo = f"{numPacotes};{hash_arquivo}"      # monta o texto "8588;d0ae6a9b..."
    
    sockCliente.sendto(protocol.montar_pacote(protocol.TipoPacote.INFO, 0, conteudoInfo.encode('utf-8')), endereco)

    with open(caminho,'rb') as arquivo:

        sockCliente.settimeout(protocol.TIMEOUT) 

        for i in range(numPacotes):

            pedaco = arquivo.read(protocol.TAM_PAYLOAD)
            dado = protocol.montar_pacote(protocol.TipoPacote.DATA, i, pedaco)
            tentativas = 0
            
            
            #--------------------------------timeout--------------------------------------
            while(tentativas < protocol.MAX_TENTATIVAS):
                
                sockCliente.sendto(dado, endereco)

                try:
                    resposta, _ = sockCliente.recvfrom(protocol.BUFFER)
                    seraUmAck,seq,_,_ = protocol.desmontar_pacote(resposta)
                    if (seraUmAck == protocol.TipoPacote.ACK and seq == i):
                        break
                except socket.timeout:
                    tentativas += 1
                    print(f"[{nome} -> {endereco}] Timeout no pacote {i}, re-enviando... (tentativa {tentativas})\n")
                    if tentativas >= protocol.MAX_TENTATIVAS:
                        break
            #-------------------------------------
            if(tentativas >= protocol.MAX_TENTATIVAS):
                break
            
        
        if(tentativas >= protocol.MAX_TENTATIVAS):
            print(f"Falha ao enviar o arquivo {nome} para {endereco} apos {protocol.MAX_TENTATIVAS} tentativas\n")
        else:
            sockCliente.sendto(protocol.montar_pacote(protocol.TipoPacote.EOF, 0, b""), endereco)
            print(f"Arquivo {nome} enviado com sucesso para {endereco}!\n")
            print(f"//--------------------------------------------//\n")

        sockCliente.close() # fechando o socket

        #sockCliente.settimeout(None) 


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

    #atender_cliente(dados.decode('utf-8'), endereco) # chamando a função para atender o cliente, passando o nome do arquivo e o endereço do cliente

    thread = threading.Thread(target=atender_cliente, args=(dados.decode('utf-8'), endereco)) # criando uma thread para atender o cliente, passando o nome do arquivo e o endereço do cliente
    thread.start() 

    #if(tipoPacote == protocol.TipoPacote.GET): #caso 1 GET
        
    #-----recorta aqui ? -----------
    
    #------ termina recorte aqui ? -----------
    
sock.close() # fechando o socket