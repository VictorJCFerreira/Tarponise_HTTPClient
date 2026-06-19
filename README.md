# Client HTTP

Um cliente HTTP simples, escrito em Python puro (só biblioteca padrão), que
monta uma requisição `GET` na mão, envia por um socket TCP e imprime a resposta
crua do servidor na tela.

O objetivo é **didático**: entender o que acontece "por trás" de um navegador,
do `curl` ou do Insomnia — HTTP é texto puro por cima do TCP.

## Requisitos

- Python 3.6 ou superior (usa f-strings).
- Nenhuma dependência externa — só a biblioteca padrão (`socket`,
  `sys`, `urllib.parse`).

## Como rodar

```bash
python client.py <url>
```

Exemplo:

```bash
python client.py http://httpbin.org/get
```

> ⚠️ Use sempre `http://` na URL. HTTPS (`https://`) ainda **não** é suportado
> (veja [Limitações](#limitações)).

## Exemplo de saída

```
=== STATUS ===
HTTP/1.1 200 OK

=== HEADERS ===
Date: Fri, 19 Jun 2026 12:08:49 GMT
Content-Type: application/json
Content-Length: 235
Connection: close
Server: gunicorn/19.9.0

=== BODY ===
{
  "args": {},
  "headers": {
    "Host": "httpbin.org",
    "User-Agent": "meu-client/0.1"
  },
  "origin": "177.100.66.93",
  "url": "http://httpbin.org/get"
}
```

Repare que o `httpbin.org` devolve no corpo os próprios headers que enviamos —
uma forma fácil de confirmar que a requisição foi montada corretamente.

## Como funciona

O fluxo segue 4 etapas (detalhadas em [ARQUITETURA.md](ARQUITETURA.md)):

1. **Parse da URL** (`parse_url`) — separa a URL em host, porta e path.
2. **Montagem da requisição** (`build_request`) — monta a string HTTP crua,
   com os `\r\n` (CRLF) exigidos pelo protocolo, e a codifica em `bytes`.
3. **Conexão TCP** (`send_request`) — abre o socket, envia a requisição e lê a
   resposta inteira em um loop até o servidor fechar a conexão.
4. **Parse da resposta** (`parse_response`) — separa status, headers e body
   pela linha em branco (`\r\n\r\n`) que divide o cabeçalho do corpo.

A requisição enviada "no fio" tem este formato:

```http
GET /get HTTP/1.1
Host: httpbin.org
User-Agent: meu-client/0.1
Connection: close

```

O header `Connection: close` faz o servidor encerrar a conexão ao terminar, o
que simplifica a leitura da resposta (lemos até o socket fechar).

## Limitações

Por ser um projeto de aprendizado, foram deixados de fora de propósito:

- Apenas **HTTP** (sem HTTPS/TLS).
- Apenas o método **GET** (sem POST/PUT/headers customizados).
- Não segue **redirects** (`3xx`) automaticamente.
- Sem tratamento de **timeouts** nem de erros de conexão.
- Apenas **IPv4**.

## Ferramentas de referência

Para comparar o comportamento deste client com implementações completas:

```bash
curl -v http://httpbin.org/get
```

Ou use o **Insomnia** / **Postman** (clients HTTP gráficos) apontando para a
mesma URL — a aba *Timeline* do Insomnia mostra a requisição/resposta cruas,
exatamente o que este programa gera.
