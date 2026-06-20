import socket
import sys
import ipaddress
from urllib.parse import urlparse, urljoin

# Defesa contra SSRF: bloqueia conexões para IPs internos/privados
BLOQUEAR_IPS_INTERNOS = True

def assert_destino_publico(host):
    ip_str = socket.gethostbyname(host)   # nome -> IP (resolve o DNS)
    ip = ipaddress.ip_address(ip_str)     # objeto que sabe se autoclassificar

    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
        raise ValueError(f"destino interno bloqueado (SSRF): {host} -> {ip}")

def parse_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "http":
        raise ValueError("Apenas suporte http:// (sem https).")
    
    host = parsed.hostname
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    # Defesa SSRF: roda a CADA chamada — logo, a cada redirect também, já que
    # fetch() -> parse_url() é o ponto único por onde toda requisição passa.
    if BLOQUEAR_IPS_INTERNOS:
        assert_destino_publico(host)
    
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

def send_request(host, port, data, timeout=10):
    # Socket IPv4 (AF_INET) e TCP (SOCK_STREAM) - {UDP seria SOCK_DGRAM}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: 
        sock.connect((host, port))  # Abre o Scoket e conecta ao servidor 
        sock.sendall(data)          # Envia a requisição HTTP crua para o servidor
        sock.settimeout(timeout)    # Define um timeout para evitar ficar esperando indefinidamente

        resposta = b""              # Lê toda a resposta do servidor
        while True:
            chunk = sock.recv(4096) # Recebe os dados em blocos de 4096 bytes
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

def get_status_code(status_line):
    pedaco = status_line.split()    # O split separa a linha em pedaços 
    return int(pedaco[1])           # O status é sempre o segundo pedaço 'HTTP/1.0 200 OK'

def get_header(headers, nome):
    nome = nome.lower()             # Exemplo de header: "Location: http://www.google.com/""
    for linha in headers:
        chave, _, valor = linha.partition(":")   
        if chave.strip().lower() == nome:
            return valor.strip()
    return None                     # Caso nao ache nada, retorna None

def fetch(url):                                      # Organizando uma requisição completa em uma função
    host, port, path = parse_url(url)                # Parse a URL
    requisicao = build_request(host, path)           # Monta a requisição HTTP crua
    resposta = send_request(host, port, requisicao)  # Envia a requisição e lê a resposta
    return parse_response(resposta)                  # Analisa a resposta e separa


def main():
    # Caso esqueça de passar a URL
    if len(sys.argv) != 2:
        print("Uso: python client.py <URL>")
        sys.exit(1)

    # Ordem de fluxo do programa:
    url = sys.argv[1]
    max_redirects = 5
    redirects = 0

    try:
        while True:
            status_line, headers, body = fetch(url)
            codigo = get_status_code(status_line)

            if not (300 <= codigo < 400):               #Verifica se o código é de redirecionamento (3xx)
                break
            location = get_header(headers, "Location")  # Se for um redirect, tem Location
            if location is None:
                break                                   # Redirect sem Location: não há pra onde seguir

            if redirects >= max_redirects:              # Protege contra loop infinito (A -> B -> A -> ...).
                print(f"Erro: muitos redirects (limite de {max_redirects}).")
                sys.exit(1)

            # Caso fosse um servidor, teriamos que ter cuidado com Open Directs.
            # Onde um atacante poderia redirecionar para um site malicioso.
            # Ou até mesmo achar um SSRF
            # https://confiavel.com/go?next=http://169.254.169.254/latest/meta-data/
            redirects += 1
            nova_url = urljoin(url, location)   # Resolve relativo OU absoluto
            print(f"-> {codigo} redirecionando para: {nova_url}")
            url = nova_url                      # Volta ao topo do while e requisita a nova URL

    except ValueError as e:
        print(f"URL inválida: {e}")
        sys.exit(1)
    except socket.timeout:
        print("Tempo limite da requisição excedido.(Timeout)")
        sys.exit(1)
    except ConnectionRefusedError:
        print("ERRO: Conexão recusada")
        sys.exit(1)
    except socket.gaierror:
        print("ERRO: Host não encontrado(DNS Falhou)")
        sys.exit(1)
    except OSError as e:
        print(f"Erro de rede: {e}")
        sys.exit(1)

    # Imprime o status, headers e corpo da resposta
    print("Status Line:", status_line)
    print("Headers:")
    for header in headers:
        print(header)
    print("\nBody:\n", body)

if __name__ == "__main__":
    main()