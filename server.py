from socket import *
from random import randint
import json
import threading
import autenticazione
import gioco
import gestione_giocatori
import time
import ssl_config
import protocollo_mm

partite_in_corso = {}
lock_partite = threading.Lock()

# REGISTRO SESSIONI ATTIVE 
utenti_online = set()
lock_online = threading.Lock()

#gestiamo la chiusura delle partite
def chiudi_partita(id_partita, tabellone):
    with lock_partite:
        if id_partita not in partite_in_corso:
            return

        msg_fine = {"op": protocollo_mm.OP_SPETTATORE, "messaggio": "Partita terminata."}
        for spettatore in tabellone.get("spettatori", []):
            try:
                spettatore.send(json.dumps(msg_fine).encode())
                
            except:
                pass

        del partite_in_corso[id_partita]
        print(f"[SERVER] Partita {id_partita[0]} vs {id_partita[1]} rimossa dal tabellone.")


class SessioneClient:
    def __init__(self, connectionSocket, addr):
        self.connectionSocket = connectionSocket
        self.addr = addr
        self.utente_autenticato = False
        self.username_corrente = None
        
        self.codice_segreto = None
        self.in_partita_singolo = False
        self.ruolo = None
        self.avversario = None
        self.tabellone = None

        #  DISPATCH TABLES 
        self.dispatch_autenticazione = {
            protocollo_mm.OP_REGISTRAZIONE: self.esegui_registrazione,
            protocollo_mm.OP_LOGIN: self.esegui_login
        }
        
        self.dispatch_menu = {
            protocollo_mm.OP_CLASSIFICA: self.modalita_classifica,
            protocollo_mm.OP_LISTA_SPEC: self.modalita_spettatore
        }
        
        self.dispatch_gioco_singolo = {
            protocollo_mm.OP_ESCI: self.azione_esci_singolo,
            protocollo_mm.OP_MOSSA: self.azione_mossa_singolo
        }
        
        self.dispatch_pvp = {
            protocollo_mm.OP_CHAT: self.azione_chat_pvp,
            protocollo_mm.OP_MOSSA: self.azione_mossa_pvp
        }

    def avvia(self):
        print(f"[SERVER] Connessione stabilita con il client:{self.addr}")
        #gestiamo l'autenticazione del client
        while not self.utente_autenticato:
            try:
                dati_in = self.connectionSocket.recv(1024).decode()
                if not dati_in:
                    break

                richiesta = json.loads(dati_in)
                tipo_azione = richiesta.get("op")

                if tipo_azione in self.dispatch_autenticazione:
                    self.dispatch_autenticazione[tipo_azione](richiesta)
                else:
                    risposta_errore = {"op": protocollo_mm.OP_ERRORE, "messaggio": "Operazione non consentita in questa fase."}
                    self.connectionSocket.send(json.dumps(risposta_errore).encode())

            except Exception as e:
                print(f"[ERRORE AUT] {self.addr}: {e}")   
                self.connectionSocket.close()
                return
            
        if not self.utente_autenticato:
            self.connectionSocket.close()
            return

        print(f"[SERVER] L'utente '{self.username_corrente}' ha fatto il login")


        while self.utente_autenticato:
            try:
                scelta_raw = self.connectionSocket.recv(1024).decode()
                if not scelta_raw:
                    break # il client si è disconnesso volontariamente o è crashato
                    
                pacchetto_scelta = json.loads(scelta_raw)
                codice_op = pacchetto_scelta.get("op")
                
                if codice_op == protocollo_mm.OP_GIOCA:
                    modalita = pacchetto_scelta.get("scelta")
                    if modalita == "1": 
                        self.modalita_singolo()
                    elif modalita == "2": 
                        self.modalita_pvp()
                elif codice_op in self.dispatch_menu:
                    self.dispatch_menu[codice_op]()
                elif codice_op == protocollo_mm.OP_ESCI:
                    break # L'utente ha cliccato per uscire dal client
                else:
                    risposta_errore = {"op": protocollo_mm.OP_ERRORE, "messaggio": "Modalità non valida."}
                    self.connectionSocket.send(json.dumps(risposta_errore).encode())

            except Exception as e:
                print(f"[ERRORE] Connessione interrotta con {self.username_corrente}:{e}")
                break # esce dal ciclo in caso di errore di rete
        
        # rimozione utente online quando la sessione termina
        if self.utente_autenticato and self.username_corrente:
            with lock_online:
                if self.username_corrente in utenti_online:
                    utenti_online.remove(self.username_corrente)
            print(f"[SERVER] L'utente '{self.username_corrente}' è uscito ed è stato rimosso dagli utenti online.")
        
        self.connectionSocket.close()
        print(f"[SERVER] Connessione chiusa con l'indirizzo {self.addr}")

#ogni funzione sottostante gestisce un'operazione diversa richiesta dal client
    def esegui_registrazione(self, richiesta):
        username = richiesta.get("username", "")
        password = richiesta.get("password", "")
        successo, msg = autenticazione.registra_utente(username, password)
        status = "SUCCESS" if successo else "ERRORE"
        risposta = {"op": protocollo_mm.OP_RISPOSTA_AUT, "status": status, "messaggio": msg}
        self.connectionSocket.send(json.dumps(risposta).encode())

    def esegui_login(self, richiesta):
        username = richiesta.get("username", "")
        password = richiesta.get("password", "")

        # controlliamo se l'utente è già online in un altro terminale
        with lock_online:
            if username in utenti_online:
                risposta = {"op": protocollo_mm.OP_RISPOSTA_AUT, "status": "ERRORE", "messaggio": "Account già in uso in un'altra finestra."}
                self.connectionSocket.send(json.dumps(risposta).encode())
                return

        # se non è online, verifichiamo la password nel database
        successo, msg = autenticazione.effettua_login(username, password)
        if successo:
            self.utente_autenticato = True
            self.username_corrente = username.strip()
            
            # utente aggiunto alla lista delle persoene online
            with lock_online:
                utenti_online.add(self.username_corrente)
                
            risposta = {"op": protocollo_mm.OP_RISPOSTA_AUT, "status": "SUCCESS", "messaggio": msg}
        else:
            risposta = {"op": protocollo_mm.OP_RISPOSTA_AUT, "status": "ERRORE", "messaggio": msg}
            
        self.connectionSocket.send(json.dumps(risposta).encode())

    def modalita_singolo(self):
        print(f"[SERVER] L'utente '{self.username_corrente}' inizia a giocare da solo")
        self.codice_segreto = [str(randint(1, 4)) for _ in range(4)]
        print(f" codice segreto {self.username_corrente}:{self.codice_segreto}")
        
        benvenuto = {"op": protocollo_mm.OP_MESSAGGIO, "messaggio": f"{self.username_corrente}, il codice segreto è pronto, fai il tuo tentativo"}
        self.connectionSocket.send(json.dumps(benvenuto).encode())
        
        self.in_partita_singolo = True
        while self.in_partita_singolo:
            messaggio = self.connectionSocket.recv(1024).decode()
            if not messaggio:
                break

            dati_ricevuti = json.loads(messaggio)
            tipo_ricevuto = dati_ricevuti.get("op")

            if tipo_ricevuto in self.dispatch_gioco_singolo:
                self.dispatch_gioco_singolo[tipo_ricevuto](dati_ricevuti)
            else:
                continue

    def azione_esci_singolo(self, dati_ricevuti):
        print(f"[SERVER] {self.username_corrente} ha abbandonato.")
        self.in_partita_singolo = False

    def azione_mossa_singolo(self, dati_ricevuti):
        combinazione_utente = dati_ricevuti.get("combinazione")
        if len(combinazione_utente) != 4:
            risposta_errore = {"op": protocollo_mm.OP_ERRORE, "messaggio": "inserisci 4 cifre"}
            self.connectionSocket.send(json.dumps(risposta_errore).encode())
            return

        neri, bianchi, ha_vinto = gioco.calcola_punteggio(self.codice_segreto, combinazione_utente)
        risposta_protocollo = {
            "op": protocollo_mm.OP_RISULTATO, "neri": neri, "bianchi": bianchi, "vittoria": ha_vinto
        }
        self.connectionSocket.send(json.dumps(risposta_protocollo).encode())

        if ha_vinto:
            print(f"[SERVER] {self.username_corrente} HA VINTO!!")
            self.in_partita_singolo = False

    def modalita_pvp(self):
        print(f"[SERVER] {self.username_corrente} cerca un avversario 1vs1")

        dati_partita = gestione_giocatori.cerca_avversario(self.connectionSocket, self.username_corrente)
        self.ruolo = dati_partita["ruolo"]
        self.avversario = dati_partita["avversario_username"]

        pacchetto_benvenuto = {
            "op": protocollo_mm.OP_MESSAGGIO, 
            "messaggio": f"Avversario trovato! Sei contro {self.avversario}. Tu sei il {self.ruolo}!"
        }
        self.connectionSocket.send(json.dumps(pacchetto_benvenuto).encode())

        id_partita = tuple(sorted([self.username_corrente, self.avversario]))

        if self.ruolo == "Giocatore 1":
            #definiamo l'insieme di dati che caratterizzano la singola partita
            partite_in_corso[id_partita] = {
                "codice_segreto": [str(randint(1, 4)) for _ in range(4)],
                "turno": "Giocatore 1", "vincitore": None, "messaggio_spia": "",
                "chat_in_sospeso": None, "spettatori": [],
                "abbandono": False #per tracciare la disconnessione
            }
            print(f" CODICE SEGRETO PARTITA {id_partita[0]} vs {id_partita[1]}: {partite_in_corso[id_partita]['codice_segreto']}")

        while id_partita not in partite_in_corso:
            time.sleep(0.1)

        self.tabellone = partite_in_corso[id_partita]

        try:
            while True:
                # controllo se l'avversario ha abbandonato
                if self.tabellone.get("abbandono"):
                    avviso = {"op": protocollo_mm.OP_RISULTATO, "vittoria": True, "messaggio": f"L'avversario {self.avversario} si è disconnesso. Hai vinto a tavolino!"}
                    self.connectionSocket.send(json.dumps(avviso).encode())
                    autenticazione.aggiorna_punteggio(self.username_corrente, 10) # assegna i punti al giocatore rimasto
                    break

                if self.tabellone["vincitore"] is not None:
                    if self.tabellone["vincitore"] == self.username_corrente:
                        break
                    else:
                        sconfitta = {"op": protocollo_mm.OP_RISULTATO, "vittoria": False, "messaggio": f"Partita terminata! {self.avversario} ha indovinato il codice!"}
                        self.connectionSocket.send(json.dumps(sconfitta).encode())
                        autenticazione.aggiorna_punteggio(self.username_corrente, -5)
                        break

                if self.tabellone["turno"] == self.ruolo:
                    if self.tabellone["messaggio_spia"]:
                        avviso = {"op": protocollo_mm.OP_MESSAGGIO, "messaggio": self.tabellone["messaggio_spia"]}
                        self.connectionSocket.send(json.dumps(avviso).encode())
                        time.sleep(0.1)

                    richiesta_mossa = {"op": protocollo_mm.OP_TURNO, "messaggio": "E' il tuo turno, inserisci 4 cifre:"}
                    self.connectionSocket.send(json.dumps(richiesta_mossa).encode())

                    messaggio_raw = self.connectionSocket.recv(1024).decode()
                    if not messaggio_raw:
                        # segnaliamo la disconnessione
                        print(f"[SERVER] L'utente '{self.username_corrente}' ha abbandonato la partita 1vs1.")
                        self.tabellone["abbandono"] = True
                        break

                    dati_ricevuti = json.loads(messaggio_raw)
                    tipo_ricevuto = dati_ricevuti.get("op")

                    if tipo_ricevuto in self.dispatch_pvp:
                        self.dispatch_pvp[tipo_ricevuto](dati_ricevuti)
                        if self.tabellone["vincitore"] == self.username_corrente:
                            break
                    else:
                        continue
                else:
                    if self.tabellone.get("chat_in_sospeso") and self.tabellone["chat_in_sospeso"]["destinatario"] == self.ruolo:
                        msg_chat = {"op": protocollo_mm.OP_CHAT, "messaggio": f"[{self.avversario}]: {self.tabellone['chat_in_sospeso']['testo']}"}
                        self.connectionSocket.send(json.dumps(msg_chat).encode())
                        self.tabellone["chat_in_sospeso"] = None

                    time.sleep(0.5)
        except Exception as e:
           
            print(f"[SERVER] Connessione persa con '{self.username_corrente}' .")
            self.tabellone["abbandono"] = True
        finally:
            chiudi_partita(id_partita, self.tabellone)

    def azione_chat_pvp(self, dati_ricevuti):
        self.tabellone["chat_in_sospeso"] = {
            "destinatario": "Giocatore 2" if self.ruolo == "Giocatore 1" else "Giocatore 1",
            "testo": dati_ricevuti.get("messaggio")
        }
        msg_tribuna = {"op": protocollo_mm.OP_SPETTATORE, "messaggio": f"💬 [{self.username_corrente}]: {dati_ricevuti.get('messaggio')}"}
        for spettatore in self.tabellone.get("spettatori", []):
            try:
                spettatore.send(json.dumps(msg_tribuna).encode())
            except:
                pass

    def azione_mossa_pvp(self, dati_ricevuti):
        combinazione = dati_ricevuti.get("combinazione")
        neri, bianchi, ha_vinto = gioco.calcola_punteggio(self.tabellone["codice_segreto"], combinazione)

        risultato = {"op": protocollo_mm.OP_RISULTATO, "neri": neri, "bianchi": bianchi, "vittoria": ha_vinto}
        self.connectionSocket.send(json.dumps(risultato).encode())

        self.tabellone["messaggio_spia"] = f"[SPIA] L'avversario ha provato {combinazione}: {neri} Neri, {bianchi} Bianchi"

        msg_tribuna = {"op": protocollo_mm.OP_SPETTATORE, "messaggio": f" [{self.username_corrente}] ha giocato {combinazione} -> Neri: {neri}, Bianchi: {bianchi}"}
        for spettatore in self.tabellone.get("spettatori", []):
            try:
                spettatore.send(json.dumps(msg_tribuna).encode())
            except:
                pass

        if ha_vinto:
            self.tabellone["vincitore"] = self.username_corrente
            print(f"[SERVER] {self.username_corrente} ha vinto il 1vs1 contro {self.avversario}!")
            autenticazione.aggiorna_punteggio(self.username_corrente, 10)
        else:
            self.tabellone["turno"] = "Giocatore 2" if self.ruolo == "Giocatore 1" else "Giocatore 1"
    
    def modalita_classifica(self):
        print(f"[SERVER] {self.username_corrente} ha richiesto la classifica.")
        with open("utenti.json", "r") as file_utenti:
            database = json.load(file_utenti)
        
        classifica_ordinata = sorted(
            [(nome, info.get("punti", 0)) for nome, info in database.items()],
            key=lambda x: x[1], reverse=True
        )
        
        top_5 = classifica_ordinata[:5]
        risposta_classifica = {"op": protocollo_mm.OP_DATI_CLASSIFICA, "dati": top_5}
        self.connectionSocket.send(json.dumps(risposta_classifica).encode())

    def modalita_spettatore(self):
        print(f"[SERVER] {self.username_corrente} vuole fare lo spettatore.")
        lista_partite = [f"{id_p[0]} vs {id_p[1]}" for id_p in partite_in_corso.keys()]
            
        if not lista_partite:
            self.connectionSocket.send(json.dumps({"op": protocollo_mm.OP_ERRORE, "messaggio": "Nessuna partita in corso."}).encode())
        else:
            self.connectionSocket.send(json.dumps({"op": protocollo_mm.OP_DATI_TRIBUNA, "partite": lista_partite}).encode())
            
            scelta_raw = self.connectionSocket.recv(1024).decode()
            if scelta_raw:
                scelta_json = json.loads(scelta_raw)
                
                if scelta_json.get("op") == protocollo_mm.OP_JOIN_SPEC:
                    indice = int(scelta_json.get("indice")) - 1
                    
                    if 0 <= indice < len(lista_partite):
                        id_scelto = list(partite_in_corso.keys())[indice]
                        partite_in_corso[id_scelto]["spettatori"].append(self.connectionSocket)
                        
                        msg_ok = {"op": protocollo_mm.OP_SPETTATORE, "messaggio": f"\nTi sei unito alla tribuna di {lista_partite[indice]}! In attesa di mosse..."}
                        self.connectionSocket.send(json.dumps(msg_ok).encode())
                        
                        while True:
                            time.sleep(1)


def gestisci_client(connectionSocket, addr):
    sessione = SessioneClient(connectionSocket, addr) #istanzio oggetto SessioneClient
    sessione.avvia()


serverPort = 12000
serverSocket = socket(AF_INET, SOCK_STREAM) #creiamo la socket TCP
serverSocket.bind(('', serverPort))
serverSocket.listen(5) #abbiamo scelto 5 come dimensione della coda di connessioni in attesa
print('Il server è pronto (TLS attivo sulla porta 12000)') 
while True:
    connectionSocket, addr = serverSocket.accept()
    try:
        secure_socket = ssl_config.avvolgi_server(connectionSocket)
        print(f"[TLS] Handshake completato con {addr}")
    except Exception as e:
        print(f"[ERRORE TLS] Handshake fallito con {addr}: {e}")
        connectionSocket.close()
        continue
    #se il tls va a buon fine viene creato un nuovo thread
    client_thread = threading.Thread(target=gestisci_client, args=(secure_socket, addr))
    client_thread.start() #avvio il thread