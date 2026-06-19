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
    
    return host, port, path