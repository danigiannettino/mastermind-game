
#generiamo un certificato TLS 
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(BASE_DIR, "cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "key.pem")

def genera():
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print("I file cert.pem e key.pem esistono già.")
        return

    comando = [
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY_FILE,
        "-out", CERT_FILE,
        "-days", "365",
        "-nodes",
        "-subj", "/CN=localhost",
    ]

    print("Generazione certificato autofirmato in corso...")
    subprocess.run(comando, check=True)
    print(f"Creati:\n  - {CERT_FILE}\n  - {KEY_FILE}")

if __name__ == "__main__":
    try:
        genera()
    except FileNotFoundError:
        print("Errore: OpenSSL non trovato. Installalo oppure esegui manualmente:")
        print('openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"')
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Errore durante la generazione del certificato: {e}")
        sys.exit(1)
