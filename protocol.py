import struct
import zlib
from enum import IntEnum

class TipoPacote(IntEnum):
    GET =  0
    INFO = 1
    DATA = 2
    ACK =  3
    ERROR = 4
    EOF = 5

FORMATO_CABECALHO = '! B I H'

TAMANHO_CABECALHO = struct.calcsize(FORMATO_CABECALHO) 

PORTA = 65432

TAM_PAYLOAD = 1500 - 20 - 8 - TAMANHO_CABECALHO #1500 é MTU, 20 do IPv4 e 8 do UDP

BUFFER = TAMANHO_CABECALHO + TAM_PAYLOAD

MAX_TENTATIVAS = 5

TIMEOUT = 0.5


def montar_pacote(tipoPacote, numSeq, dados):
    
    checksum = calcular_checksum(dados)

    cabecalho = struct.pack(FORMATO_CABECALHO, tipoPacote, numSeq, checksum)    

    pacote = cabecalho + dados 
    
    return pacote


def get_pacote(): # sepa que isso seja inutil
    return struct.pack(FORMATO_CABECALHO, TipoPacote.GET.value, 0, 0)


def desmontar_pacote(pacote):

    cabecalho = pacote[:TAMANHO_CABECALHO]
    dados = pacote[TAMANHO_CABECALHO:]

    tipoPacote, numSeq, checksum = struct.unpack(FORMATO_CABECALHO, cabecalho)
    
    return tipoPacote, numSeq, checksum, dados


def calcular_checksum(dados): # AQUI TO USANDO UMA FUNÇAO PRONTA PRA CALCULAR O CHECKSUM, MAS TALVEZ TENHA QUE FAZER NA MAO
    return zlib.crc32(dados) & 0xFFFF



#--------------- testeeee -------------------------#

if __name__ == "__main__":
    pacote = montar_pacote(TipoPacote.DATA, 42, b"teste")
    print(len(pacote))          # deve dar 7 + 5 = 12
    print(desmontar_pacote(pacote))     # deve voltar (2, 42, <algum checksum>, b'teste')