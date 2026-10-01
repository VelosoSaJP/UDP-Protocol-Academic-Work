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

TAM_PAYLOAD = 1500 - 20 - 8 - TAMANHO_CABECALHO

BUFFER = TAMANHO_CABECALHO + TAM_PAYLOAD

MAX_TENTATIVAS = 5

TIMEOUT = 0.5

def montar_pacote(tipoPacote, numSeq, dados):

    checksum = calcular_checksum(dados)

    cabecalho = struct.pack(FORMATO_CABECALHO, tipoPacote, numSeq, checksum)

    pacote = cabecalho + dados

    return pacote

def get_pacote():
    return struct.pack(FORMATO_CABECALHO, TipoPacote.GET.value, 0, 0)

def desmontar_pacote(pacote):

    cabecalho = pacote[:TAMANHO_CABECALHO]
    dados = pacote[TAMANHO_CABECALHO:]

    tipoPacote, numSeq, checksum = struct.unpack(FORMATO_CABECALHO, cabecalho)

    return tipoPacote, numSeq, checksum, dados

def calcular_checksum(dados):
    return zlib.crc32(dados) & 0xFFFF

if __name__ == "__main__":
    pacote = montar_pacote(TipoPacote.DATA, 42, b"teste")
    print(len(pacote))
    print(desmontar_pacote(pacote))
