# Transferência Confiável de Arquivos sobre UDP

Trabalho 1 da disciplina de Redes de Computadores (ICSR30), do Prof. Mauro Fonseca (UTFPR, DAINF).

Este projeto é uma aplicação cliente-servidor para transferência de arquivos sobre **UDP**, usando diretamente a API de sockets do Python. O UDP não garante entrega, ordem nem integridade. Por isso o projeto define um protocolo de aplicação próprio, com o necessário para a transferência ser confiável:

- segmentação do arquivo;
- cabeçalho com número de sequência e checksum;
- confirmação (ACK);
- retransmissão por timeout (*Stop-and-Wait*);
- verificação final de integridade com MD5.

O projeto usa só a biblioteca padrão do Python: `socket`, `struct`, `zlib`, `hashlib`, `threading`, `os` e `enum`.

## Estrutura

| Arquivo | Função |
|---|---|
| `protocol.py` | Definição do protocolo: tipos de mensagem, formato do cabeçalho, tamanhos, montagem e desmontagem de pacotes, e checksum. |
| `server.py` | Servidor UDP. Recebe requisições e atende cada cliente numa thread própria. |
| `client.py` | Cliente UDP. Requisita, recebe, valida e salva o arquivo. |
| `files/` | Pasta com os arquivos que o servidor disponibiliza. É a única pasta que ele pode acessar. |
| `downloads_client/` | Pasta onde o cliente salva os arquivos recebidos. É criada automaticamente. |

## Como executar

Requisito: Python 3.

1. Coloque os arquivos a serem servidos em `files/`. Para gerar arquivos de teste grandes:

   ```bash
   mkdir -p files
   head -c 12M /dev/urandom > files/teste_12M.bin
   head -c 15M /dev/urandom > files/teste_15M.bin
   ```

2. Inicie o servidor. Ele precisa estar rodando antes do cliente:

   ```bash
   python3 server.py
   ```

   O servidor escuta em `127.0.0.1:65432`. A porta fica na constante `PORTA` em `protocol.py` e é maior que 1024, então não exige privilégios de administrador.

3. Em outro terminal, inicie o cliente e responda às perguntas:

   ```
   $ python3 client.py
   Digite o IP do servidor: 127.0.0.1
   Digite a porta do servidor: 65432
   Digite o nome do arquivo que deseja receber: teste_12M.bin
   Digite os blocos que deseja descartar: 3,7
   ```

   Deixe a última pergunta em branco para não descartar nenhum bloco.

4. O arquivo recebido é salvo em `downloads_client/`. O cliente confere o MD5 e informa se a transferência deu certo.

## O protocolo

### Formato do pacote

Todo datagrama tem um cabeçalho fixo de **7 bytes**, seguido dos dados. O cabeçalho usa ordem de bytes de rede (big-endian), com o formato `struct` `'! B I H'`:

```
+--------+-------------------+-------------+---------------------------+
|  Tipo  |  Num. Sequência   |  Checksum   |  Dados (0 a 1465 bytes)   |
| 1 byte |     4 bytes       |   2 bytes   |                           |
+--------+-------------------+-------------+---------------------------+
```

- **Tipo:** identifica a mensagem (tabela abaixo).
- **Número de sequência:** índice do segmento dentro do arquivo, começando em 0. Com 4 bytes, permite arquivos com até cerca de 4 bilhões de segmentos.
- **Checksum:** CRC32 dos dados, truncado para 16 bits (`zlib.crc32(dados) & 0xFFFF`).

### Mensagens

| Tipo | Código | Sentido | Seq | Dados |
|---|---|---|---|---|
| `GET` | 0 | cliente → servidor | 0 | nome do arquivo requisitado |
| `INFO` | 1 | servidor → cliente | 0 | `"<total de segmentos>;<MD5 do arquivo>"` |
| `DATA` | 2 | servidor → cliente | índice do segmento | pedaço do arquivo |
| `ACK` | 3 | cliente → servidor | índice confirmado | vazio |
| `ERROR` | 4 | servidor → cliente | 0 | mensagem de erro (ex.: `Arquivo NAO encontrado`) |
| `EOF` | 5 | servidor → cliente | 0 | vazio, indica fim da transmissão |

### Fluxo de uma transferência

```
Cliente                     Servidor (porta 65432)        Thread do cliente (porta efêmera)
   |  GET "arquivo.bin"  -------->|                                    |
   |                              |-- cria thread ------------------->|
   |<------------------------------------------------ INFO "N;md5" ---|
   |<------------------------------------------------ DATA 0 ---------|
   |--- ACK 0 ------------------------------------------------------->|
   |<------------------------------------------------ DATA 1 ---------|
   |--- ACK 1 ------------------------------------------------------->|
   |                             ...                                   |
   |<------------------------------------------------ EOF ------------|
```

Se o arquivo não existe, a thread responde com `ERROR` em vez de `INFO`, e o cliente mostra a mensagem ao usuário.

## Decisões de projeto

### Segmentação e tamanho do buffer

O tamanho máximo de dados por datagrama é **1465 bytes**, fixo para todos os segmentos menos o último:

```
1500 (MTU Ethernet) - 20 (cabeçalho IPv4) - 8 (cabeçalho UDP) - 7 (cabeçalho do protocolo) = 1465
```

Com isso, cada datagrama cabe inteiro num quadro Ethernet e **não sofre fragmentação IP**. Sem fragmentação, cada segmento perdido é um único datagrama. Se um datagrama fosse fragmentado, a perda de qualquer fragmento descartaria o datagrama inteiro.

Servidor e cliente usam o mesmo buffer de recepção, `BUFFER = 7 + 1465 = 1472` bytes, definido em `protocol.py`. Os dois precisam ter tamanhos relacionados: se o buffer do `recvfrom` fosse menor que o datagrama, os bytes excedentes seriam descartados em silêncio.

### Detecção de erros

Os erros são verificados em dois níveis:

1. **Por segmento:** o servidor calcula o checksum dos dados ao montar o pacote e o coloca no cabeçalho. O cliente recalcula ao receber. Se os valores não batem, o segmento é descartado e o cliente não envia ACK, o que faz o servidor retransmitir quando o timeout estourar.
2. **Por arquivo:** o servidor envia o MD5 do arquivo inteiro na mensagem `INFO`. O cliente calcula o MD5 do que recebeu e compara os dois ao receber o `EOF`.

### Ordenação e detecção de perda

- **Ordenação:** cada segmento leva seu número de sequência. O cliente guarda o próximo segmento esperado (`proximoBloco`) e só grava no arquivo o segmento com esse número, o que garante a ordem. Um segmento com número menor é uma duplicata. Ele é descartado, mas o cliente reenvia o ACK correspondente, para o caso de o ACK anterior ter se perdido.
- **Perda:** o protocolo é **Stop-and-Wait**. O servidor envia um segmento e espera o ACK com aquele número de sequência por até `TIMEOUT = 0.5 s`. Se o timeout estourar, o servidor considera o segmento ou o ACK perdido e retransmite. Depois de `MAX_TENTATIVAS = 5` timeouts seguidos no mesmo segmento, o servidor desiste da transferência. Um pacote que chega atrasado depois da retransmissão é reconhecido como duplicata pelo número de sequência, então não é gravado duas vezes.
- **Solicitação de retransmissão:** no Stop-and-Wait, a falta do ACK é o pedido de retransmissão. Isso cobre tanto um segmento perdido quanto um segmento com checksum inválido.

### Controle de fluxo

O Stop-and-Wait já limita o fluxo: o servidor nunca tem mais de um segmento "em trânsito" e só envia o próximo depois que o cliente confirma o anterior. Assim, o servidor não consegue enviar mais rápido do que o cliente processa.

## Funcionalidades

- **Simulação de perda:** o cliente pergunta quais blocos descartar, como `3,7`. Cada bloco da lista é ignorado na primeira vez que chega, e o cliente mostra quais foram descartados. Sem o ACK, o servidor acusa o timeout no terminal e retransmite o bloco.
- **Vários clientes ao mesmo tempo:** o socket principal só recebe `GET`s. Para cada requisição, o servidor cria uma `threading.Thread` com um socket UDP próprio, numa porta efêmera, que cuida de toda a transferência daquele cliente. O cliente guarda o endereço de onde veio a resposta (`INFO` ou `ERROR`) e manda os ACKs para lá. Assim, os pacotes de clientes diferentes nunca se misturam. As mensagens do servidor levam o nome do arquivo e o endereço do cliente, para identificar cada transferência.
- **Arquivo inexistente:** o servidor responde com uma mensagem `ERROR`, e o cliente a mostra ao usuário.
- **Proteção contra path traversal:** o servidor aplica `os.path.basename()` ao nome recebido antes de montar o caminho dentro de `files/`. Isso descarta qualquer componente de diretório: tanto `../../etc/passwd` quanto `/etc/passwd` viram `passwd`, que é procurado apenas em `files/`. O cliente também aplica `basename` ao salvar, para não escrever fora de `downloads_client/`.

## Limitações conhecidas

- O cliente não tem timeout. Se o `INFO` ou o `EOF` se perderem, ou se o servidor desistir depois de `MAX_TENTATIVAS`, o cliente fica esperando indefinidamente.
- Se o MD5 final não bater, o cliente informa o erro, mas não requisita o arquivo de novo automaticamente.
- O servidor escuta apenas em `127.0.0.1`. Para aceitar clientes de outras máquinas, troque `HOST` por `'0.0.0.0'` em `server.py`.
