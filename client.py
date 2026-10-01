import socket
import protocol
import os
import hashlib

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ip = input("Digite o IP do servidor: ")
porta = int(input("Digite a porta do servidor: "))
nome = input("Digite o nome do arquivo que deseja receber: ")
SERVIDOR_HOST = (ip, porta)

texto = input("Digite os blocos que deseja descartar: ")

if (texto.strip() == ""):
    blocosDescartados = set()
else:
    blocosDescartados = {int(numero) for numero in texto.split(',')}

sock.sendto(protocol.montar_pacote(protocol.TipoPacote.GET, 0, nome.encode('utf-8')), SERVIDOR_HOST)

resposta, enderecoServidor = sock.recvfrom(protocol.BUFFER)
print(f"Resposta recebida do servidor {enderecoServidor}\n")

tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(resposta)

if(tipoPacote == protocol.TipoPacote.ERROR):
    print("Erro: ", dados.decode('utf-8'))
    sock.close()
    exit()

elif(tipoPacote == protocol.TipoPacote.INFO):
    total, hashServidor = dados.decode().split(";")
    numPacotes = int(total)
    print(f"Numero de pacotes a serem recebidos: {numPacotes}\n")

    os.makedirs("downloads_client", exist_ok=True)
    caminhoSaida = os.path.join("downloads_client", os.path.basename(nome))

    with open(caminhoSaida, 'wb') as arquivo:

        hashArquivo = hashlib.md5()

        proximoBloco = 0

        while(tipoPacote != protocol.TipoPacote.EOF):

            pacote, _ = sock.recvfrom(protocol.BUFFER)

            tipoPacote, numSeq, checksum, dados = protocol.desmontar_pacote(pacote)

            if(tipoPacote == protocol.TipoPacote.DATA):

                if numSeq in blocosDescartados:
                    print(f"Pacore {numSeq} ignorado!!!\n")
                    blocosDescartados.remove(numSeq)
                    continue

                if(checksum != protocol.calcular_checksum(dados)):
                    print("Erro de checksum no pacote", numSeq)

                else:
                    if(numSeq == proximoBloco):
                        proximoBloco += 1
                        arquivo.write(dados)
                        hashArquivo.update(dados)
                        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ACK, numSeq, b""), enderecoServidor)
                    elif(numSeq < proximoBloco):
                        print(f"Pacote {numSeq} ja recebido, ACK enviado novamente\n")
                        sock.sendto(protocol.montar_pacote(protocol.TipoPacote.ACK, numSeq, b""), enderecoServidor)

            if(tipoPacote == protocol.TipoPacote.EOF):

                if(hashServidor != hashArquivo.hexdigest()):
                    print("Erro de hash no arquivo recebido\n")
                else:
                    print(f"Arquivo recebido com sucesso! hash {hashArquivo.hexdigest()} verificado!\n")
                break
        sock.close()

else:
    print("Mensagem recebida inesperada")
    sock.close()
    exit()
