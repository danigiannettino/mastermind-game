from socket import *
import json
import ssl_config
import protocollo_mm
import sys
import tkinter as tk
from interfaccia import MastermindAppGUI

class MastermindClient:
    def __init__(self, server_name='localhost', server_port=12000):
        self.server_name = server_name
        self.server_port = server_port
        self.clientSocket = None
        self.autenticato = False

    def connetti(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect((self.server_name, self.server_port))
        self.clientSocket = ssl_config.avvolgi_client(sock, self.server_name)
        print("[TLS] Canale sicuro stabilito con il server")

    def avvia(self):
        self.connetti()
        
        
        while not self.autenticato:
            self.mostra_menu_autenticazione()
            
        print("\n Accesso effettuato. Passaggio all'interfaccia grafica in corso...")
        
        # avvio dell'Interfaccia Grafica Completa
        root = tk.Tk()
        
        app = MastermindAppGUI(root, self.clientSocket)
        
        root.mainloop()
        
        self.clientSocket.close()
        print("[*] Applicazione chiusa correttamente.")

    def mostra_menu_autenticazione(self):
        #gestisce il menu iniziale direttamente sul terminale per l'accesso/registrazione
        print("\n" + "="*20)
        print("     MASTERMIND")
        print("="*20)
        print("1. Accedi")
        print("2. Registrati")
        print("3. Esci")
        scelta = input("Seleziona un'opzione: ").strip()

        if scelta == "3":
            print("Chiusura in corso...")
            self.clientSocket.close()
            sys.exit()
        
        if scelta in ["1", "2"]:
            username = input("Username: ")
            password = input("Password: ")

            codice_operazione = protocollo_mm.OP_LOGIN if scelta == "1" else protocollo_mm.OP_REGISTRAZIONE

            dati_autenticazione = {
                "op": codice_operazione, "username": username, "password": password
            }
            self.clientSocket.send(json.dumps(dati_autenticazione).encode())

            risposta_in = self.clientSocket.recv(1024).decode()
            if not risposta_in:
                print("Errore: il server ha chiuso la connessione")
                self.clientSocket.close()
                sys.exit()

            risposta = json.loads(risposta_in)
            print(f"\nServer: {risposta.get('messaggio')}")

            #se il login ha successo, sblocca il ciclo per lanciare l'interfaccia
            if risposta.get("op") == protocollo_mm.OP_RISPOSTA_AUT and risposta.get("status") == "SUCCESS" and codice_operazione == protocollo_mm.OP_LOGIN:
                self.autenticato = True
        else:
            print("Opzione non valida. Riprova.")

if __name__ == "__main__":
    client = MastermindClient()
    client.avvia()