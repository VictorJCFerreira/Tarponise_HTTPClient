import socket
import sys
from urllib.parse import urlparse

def parse_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "http":
        raise ValueError("Apenas suporte http:// (sem https).")
    
    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    
    # Separa o Host, pois muitos domínios copartilham o mesmo endereço IP físico, ele indica qual aplicação específica 
    # deve processar a requisição.
    # A porta é o número da porta TCP onde o servidor está escutando.
    # Se a URL não especificar uma porta, usamos a porta padrão 80 (HTTP).
    # E o path é a parte da URL que indica o recurso específico que queremos acessar no servidor. 
    # Se a URL não tiver um path, usamos "/" como padrão, que geralmente representa a página inicial ou raiz do site.
    return host, port, path

def build_request(host, path, method="GET"):
    request_line = f"{method} {path} HTTP/1.1\r\n"
    headers = (
        f"Host: {host}\r\n"
        f"User-Agent: meu-client/0.1\r\n"
        f"Connection: close\r\n"
    )

    # O "\r\n" extra é a linha em branco que marca o fim dos headers.
    # Se nao for tratado da forma correta, pode gerar vulnerabilidades como CRLF injection.
    requisicao = request_line + headers + "\r\n"
    return requisicao.encode("utf-8")

def send_request(host, port, data):
    #Socket IPv4 (AF_INET) e TCP (SOCK_STREAM) - {UDP seria SOCK_DGRAM}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: 
        sock.connect((host, port))  #Abre o Scoket e conecta ao servidor 
        sock.sendall(data)          #Envia a requisição HTTP crua para o servidor

        resposta = b""              #Lê toda a resposta do servidor
        while True:
            chunk = sock.recv(4096) #Recebe os dados em blocos de 4096 bytes
            if not chunk:
                break
            resposta += chunk

    return resposta

def parse_response(response):
    # A resposta HTTP é composta por uma linha de status, seguida por headers e um corpo.
    # O .partition(b"\r\n\r\n") é para separar o cabeçalho do corpo da resposta.
    cabecalho_bruto, _, corpo = response.partition(b"\r\n\r\n")
    linhas = cabecalho_bruto.split(b"\r\n")

    # O .decode converte os bytes em string
    # Oerrors="replace" substitui caracteres inválidos
    status_line = linhas[0].decode("utf-8", errors="replace")
    headers = [linha.decode("utf-8", errors="replace") for linha in linhas[1:]]
    body = corpo.decode("utf-8", errors="replace")

    return status_line, headers, body

