import os
import ssl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(BASE_DIR, "cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "key.pem")

_context_server = None
_context_client = None

def crea_context_server():
    """Contesto TLS lato server: carica certificato e chiave privata."""
    global _context_server
    if _context_server is not None:
        return _context_server

    if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
        raise FileNotFoundError(
            "Certificato non trovato. Esegui prima: python genera_certificato.py"
        )

    _context_server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    _context_server.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    return _context_server

def crea_context_client():
    global _context_client
    if _context_client is not None:
        return _context_client

    # Creiamo un contesto sicuro standard
    _context_client = ssl.create_default_context()
    
    # 1. OBBLIGHIAMO il client a verificare il certificato
    _context_client.verify_mode = ssl.CERT_REQUIRED
    
    # 2. Gli diciamo: "Fidati SOLO di questo specifico file cert.pem"
    # (Affinché funzioni, il file cert.pem deve trovarsi anche nella cartella del client)
    _context_client.load_verify_locations(cafile=CERT_FILE)
    
    # 3. Verifichiamo che il nome del server corrisponda a quello nel certificato (localhost)
    _context_client.check_hostname = True 
    
    return _context_client

def avvolgi_server(sock):
    """Avvolge un socket TCP accettato con TLS (handshake server-side)."""
    return crea_context_server().wrap_socket(sock, server_side=True)

def avvolgi_client(sock, hostname="127.0.0.1"):
    """Avvolge un socket TCP connesso con TLS (handshake client-side)."""
    return crea_context_client().wrap_socket(sock, server_hostname=hostname)
