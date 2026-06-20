# Client HTTP

Um cliente HTTP/HTTPS escrito em Python puro (só biblioteca padrão), que monta
uma requisição `GET` na mão, envia por um socket TCP (com TLS quando for HTTPS)
e imprime a resposta do servidor na tela.

O objetivo é **didático**: entender o que acontece "por trás" de um navegador,
do `curl` ou do Insomnia — HTTP é texto puro por cima do TCP, e HTTPS é o mesmo
texto dentro de um túnel TLS.

## Requisitos

- Python 3.6 ou superior (usa f-strings).
- Nenhuma dependência externa — só a biblioteca padrão
  (`socket`, `ssl`, `sys`, `urllib.parse`, `ipaddress`).

## Como rodar

```bash
python client.py <url>
```

Exemplos:

```bash
python client.py http://example.com
python client.py https://example.com
python client.py http://wikipedia.org      # segue o redirect http -> https
```

## Funcionalidades

- ✅ **HTTP e HTTPS** (TLS com verificação de certificado).
- ✅ **Segue redirects 3xx** automaticamente (com limite contra loop infinito).
- ✅ **Defesa anti-SSRF**: recusa destinos em IPs internos/privados.
- ✅ **Tratamento de erros** amigável (DNS, conexão recusada, timeout, certificado).

## Exemplo de saída

```
=== STATUS ===
HTTP/1.1 200 OK

=== HEADERS ===
Content-Type: text/html; charset=UTF-8
Content-Length: 1256
Connection: close
...

=== BODY ===
<!doctype html>
...
```

Quando há redirect, cada salto é mostrado antes do resultado final:

```
-> 301 redirecionando para: https://wikipedia.org/
-> 301 redirecionando para: https://www.wikipedia.org/
=== STATUS ===
HTTP/1.1 200 OK
```

## Como funciona

O fluxo segue 4 etapas (detalhadas em [ARQUITETURA.md](ARQUITETURA.md)):

1. **Parse da URL** (`parse_url`) — separa em esquema, host, porta e path.
   Também aplica a defesa anti-SSRF (`assert_destino_publico`).
2. **Montagem da requisição** (`build_request`) — monta a string HTTP crua,
   com os `\r\n` (CRLF) exigidos pelo protocolo, e a codifica em `bytes`.
3. **Conexão** (`send_request`) — abre o socket; se for HTTPS, embrulha numa
   camada TLS. Envia a requisição e lê a resposta inteira até o servidor fechar.
4. **Parse da resposta** (`parse_response`) — separa status, headers e body
   pela linha em branco (`\r\n\r\n`) que divide o cabeçalho do corpo.

O header `Connection: close` faz o servidor encerrar a conexão ao terminar, o
que simplifica a leitura da resposta (lemos até o socket fechar).

## Segurança: defesa anti-SSRF

Como o client segue redirects, um servidor malicioso poderia redirecioná-lo para
um endereço **interno** (ex.: `http://169.254.169.254/` — metadata da nuvem — ou
`127.0.0.1`). Isso é um vetor de **SSRF** (Server-Side Request Forgery).

A defesa (`assert_destino_publico`) resolve o host para um IP e **recusa**
endereços privados/loopback/link-local/reservados. Como ela roda dentro do
`parse_url` (chamado a cada salto), **todo redirect** também é validado — não só
a URL inicial. Veja a seção 11 do [ARQUITETURA.md](ARQUITETURA.md).

A defesa pode ser desligada virando a constante no topo do `client.py` (por
exemplo, para acessar um serviço em rede local):

```python
BLOQUEAR_IPS_INTERNOS = False   # desliga a defesa anti-SSRF
```

## Limitações

Por ser um projeto de aprendizado, foram deixados de fora de propósito:

- Apenas o método **GET** (sem POST/PUT/headers customizados).
- Sem suporte a **chunked transfer encoding** nem **keep-alive** (depende de
  `Connection: close` para saber onde a resposta termina).
- Apenas **IPv4** (a resolução usa `socket.gethostbyname`).
- A defesa anti-SSRF é vulnerável a **DNS rebinding** (resolve na validação e o
  `connect` resolve de novo) — a versão robusta conectaria no IP já validado.

## Ferramentas de referência

Para comparar o comportamento deste client com implementações completas:

```bash
curl -v https://example.com
```

Ou use o **Insomnia** / **Postman** apontando para a mesma URL — a aba *Timeline*
do Insomnia mostra a requisição/resposta cruas, exatamente o que este programa gera.
