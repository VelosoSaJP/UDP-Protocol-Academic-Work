import socket
import protocol
import os

SERVIDOR_HOST = ('127.0.0.1', protocol.PORTA) # definindo o endereço do servidor, tupla com IP e porta

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # criando um socket UDP - primeiro arg é o IPV4 , segundo arg é o tipo de socket (UDP)

nome = input("Digite o nome do arquivo que deseja receber: ") # pedindo para o usuario digitar o nome do arquivo

sock.sendto(protocol.montar_pacote(protocol.TipoPacote.GET, 0, nome.encode('utf-8')), SERVIDOR_HOST) 

resposta, _ = sock.recvfrom(protocol.BUFFER) # recebendo a resposta do servidor

tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(resposta) # desmontando o pacote recebido

if(tipoPacote == protocol.TipoPacote.ERROR): # caso 1 ERROR
    print("Erro: ", dados.decode('utf-8')) # decodificando os bytes para string e imprimindo a mensagem de erro
    sock.close() # fechando o socket
    exit() # saindo do programa

if(tipoPacote == protocol.TipoPacote.INFO): # caso 2 INFO
    numPacotes = int(dados.decode('utf-8')) # decodificando os bytes para string e convertendo para inteiro
    print(f"Numero de pacotes a serem recebidos: {numPacotes}") # imprimindo o numero de pacotes a serem recebidos

    
    os.makedirs("downloads_client", exist_ok=True)   # cria a pasta se não existir (e não reclama se já existir)
    caminhoSaida = os.path.join("downloads_client", os.path.basename(nome))  # "downloads_client/teste.txt"
    
    with open(caminhoSaida, 'wb') as arquivo: # abrindo o arquivo para escrita em binario

        while(tipoPacote != protocol.TipoPacote.EOF): # loop para receber todos os pacotes

            pacote, _ = sock.recvfrom(protocol.BUFFER) # recebendo o pacote do servidor

            tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(pacote) # desmontando o pacote recebido

            if(tipoPacote == protocol.TipoPacote.DATA): # caso 1 DATA
                arquivo.write(dados)
                sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ACK, numSeq, b""), SERVIDOR_HOST) 

            if(tipoPacote == protocol.TipoPacote.EOF): # caso 2 EOF
                print("Arquivo recebido com sucesso")
                break # saindo do loop
        sock.close() # fechando o socket

else:
    #(tipoPacote != protocol.TipoPacote.ERROR and tipoPacote != protocol.TipoPacote.INFO ): # caso 3 : qualquer outra mensagem
    print("Mensagem recebida inesperada")
    sock.close() # fechando o socket
    exit() # saindo do programa