import socket
import protocol
import os
import hashlib

SERVIDOR_HOST = ('127.0.0.1', protocol.PORTA) # definindo o endereço do servidor, tupla com IP e porta

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # criando um socket UDP - primeiro arg é o IPV4 , segundo arg é o tipo de socket (UDP)

nome = input("Digite o nome do arquivo que deseja receber: ") # pedindo para o usuario digitar o nome do arquivo

texto = input("Digite os blocos que deseja descartar: ") # pedindo para o usuario digitar a quantidade de blocos que deseja receber

if (texto.strip() == ""):
    blocosDescartados = set()
else:
    blocosDescartados = {int(numero) for numero in texto.split(',')}


sock.sendto(protocol.montar_pacote(protocol.TipoPacote.GET, 0, nome.encode('utf-8')), SERVIDOR_HOST) 

resposta, enderecoServidor = sock.recvfrom(protocol.BUFFER) # recebendo a resposta do servidor
print(f"Resposta recebida do servidor {enderecoServidor}\n")

tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(resposta) # desmontando o pacote recebido

if(tipoPacote == protocol.TipoPacote.ERROR): # caso 1 ERROR
    print("Erro: ", dados.decode('utf-8')) # decodificando os bytes para string e imprimindo a mensagem de erro
    sock.close() # fechando o socket
    exit() # saindo do programa

elif(tipoPacote == protocol.TipoPacote.INFO): # caso 2 INFO
    total, hashServidor = dados.decode().split(";")
    numPacotes = int(total)
    print(f"Numero de pacotes a serem recebidos: {numPacotes}\n") # imprimindo o numero de pacotes a serem recebidos

    
    os.makedirs("downloads_client", exist_ok=True)   # cria a pasta se não existir (e não reclama se já existir)
    caminhoSaida = os.path.join("downloads_client", os.path.basename(nome))  # "downloads_client/teste.txt"
    
    with open(caminhoSaida, 'wb') as arquivo: # abrindo o arquivo para escrita em binario

        hashArquivo = hashlib.md5() # criando um objeto para calcular o hash do arquivo recebido

        proximoBloco = 0

        while(tipoPacote != protocol.TipoPacote.EOF): # loop para receber todos os pacotes

            pacote, _ = sock.recvfrom(protocol.BUFFER) # recebendo o pacote do servidor

            tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(pacote) # desmontando o pacote recebido

            if(tipoPacote == protocol.TipoPacote.DATA): # caso 1 DATA

                if numSeq in blocosDescartados:
                    print(f"Pacore {numSeq} ignorado!!!\n")
                    blocosDescartados.remove(numSeq) 
                    continue
                
                if(checksum != protocol.calcular_checksum(dados)): #verifica se o checksum bate
                    print("Erro de checksum no pacote", numSeq)
                
                else: # checksum == protocol.calcular_checksum(dados)
                    if(numSeq == proximoBloco): # verifica se o numero do pacote é o esperado
                        #print(f"Pacote {numSeq} recebido com sucesso!\n")
                        proximoBloco += 1
                        arquivo.write(dados)
                        hashArquivo.update(dados)
                        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ACK, numSeq, b""), enderecoServidor) 
                    elif(numSeq < proximoBloco):
                        print(f"Pacote {numSeq} ja recebido, ACK enviado novamente\n")
                        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ACK, numSeq, b""), enderecoServidor)


            if(tipoPacote == protocol.TipoPacote.EOF): # caso 2 EOF

                if(hashServidor != hashArquivo.hexdigest()): #verifica se o hash bate
                    print("Erro de hash no arquivo recebido\n")
                else:
                    print(f"Arquivo recebido com sucesso! hash {hashArquivo.hexdigest()} verificado!\n")
                break # saindo do loop
        sock.close() # fechando o socket

else:
    #(tipoPacote != protocol.TipoPacote.ERROR and tipoPacote != protocol.TipoPacote.INFO ): # caso 3 : qualquer outra mensagem
    print("Mensagem recebida inesperada")
    sock.close() # fechando o socket
    exit() # saindo do programa