# Mastermind - Multiplayer Network Game 

Un'implementazione client-server avanzata del classico gioco da tavolo Mastermind, scritta interamente in Python.
Questo progetto va oltre la semplice logica di gioco, implementando un'architettura di rete sicura con crittografia TLS, gestione della concorrenza multithread e un'interfaccia grafica responsiva basata sul pattern Produttore-Consumatore.

##  Caratteristiche principali

* **Autenticazione Sicura:** Sistema di Login e Registrazione. Le password sono salvate localmente in modo sicuro utilizzando tecniche di *Salting* (128-bit) e *Hashing* unidirezionale.

* **Modalità Singolo Giocatore:** Sfida contro il server per indovinare il codice generato casualmente.

* **Modalità PvP (1vs1 a turni):** Matchmaking in tempo reale tra due client remoti. Include un sistema di punteggio globale (+10 per la vittoria, -5 per la sconfitta) e gestione automatica delle disconnessioni (vittoria a tavolino).

* **Chat di Gioco:** Sistema di messaggistica integrato (broadcast) per comunicare con l'avversario durante il proprio turno.

* **Modalità Spettatore:** Permette di assistere in tempo reale a una partita PvP in corso, visualizzando le mosse e la chat.

* **Classifica Globale (Leaderboard):** Visualizzazione in tempo reale dei 5 migliori giocatori.

## Architettura 

Questo progetto è stato sviluppato con un forte accento sui principi dell'Ingegneria del Software e delle Reti:

* **Sicurezza e Crittografia (TLS):** Le comunicazioni sui socket TCP (porta 12000) sono incapsulate in un canale sicuro. L'handshake iniziale utilizza crittografia asimmetrica (con scambio di certificati) per poi passare a una più efficiente crittografia simmetrica tramite Chiave di Sessione. Questo previene attacchi di *packet sniffing* e manomissione dei dati.

* **Concorrenza e Multithreading:** Il server assegna un thread dedicato a ogni client connesso. L'accesso concorrente alle risorse condivise (es. salvataggio nel file `utenti.json`) è gestito in totale sicurezza tramite l'uso di **Lock**. Il matchmaking implementa meccanismi di sincronizzazione **Wait/Signal** per evitare sprechi di cicli CPU.

* **Design del Protocollo (OpCodes & Dispatch Tables):** La comunicazione avviene tramite payload JSON strutturati. Il server utilizza *Dispatch Tables* per mappare direttamente gli OpCode (es. `OP_MOSSA`) alle rispettive funzioni di gestione in tempo costante $\mathcal{O}(1)$, eliminando l'uso inefficiente di catene `if-else` e garantendo un'altissima modularità.

* **GUI Non-Bloccante (Produttore-Consumatore):** L'interfaccia (Tkinter) implementa una coda FIFO per disaccoppiare la ricezione dei dati dalla rete (Produttore) dall'aggiornamento grafico (Consumatore). Questo evita il blocco dell'interfaccia durante le chiamate bloccanti `socket.recv()`.

## Istruzioni per l'avvio

Il progetto utilizza esclusivamente librerie standard di Python (es. `socket`, `threading`, `tkinter`, `ssl`, `secrets`, `json`). Non è necessario installare pacchetti esterni tramite `pip`.

### 1. Avvio del server

Prima di avviare qualsiasi client, è necessario lanciare il server in ascolto:

```
python server.py

```

*(Nota: Assicurati che i file del certificato `cert.pem` e della chiave privata `key.pem` siano presenti nella stessa directory del server per consentire l'handshake TLS).*

### 2. Avvio del client

Apri uno o più terminali separati per lanciare le istanze dei giocatori:

```
python client.py

```

*(Nota per lo sviluppatore: Sostituisci `server.py` e `client.py` con il nome esatto dei tuoi script se sono diversi, ad esempio `main_client.py`)*

## Regole del gioco

1. Il server genera un codice segreto di **4 pioli colorati** (a scelta tra Rosso, Blu, Verde, Giallo).

2. Hai a disposizione **10 tentativi** per indovinare l'esatta combinazione e posizione.

3. Ad ogni mossa, il server fornisce un feedback:

   * **Piolo Nero:** Colore giusto nella posizione giusta.

   * **Piolo Bianco:** Colore giusto ma nella posizione sbagliata.
