import tkinter as tk
from tkinter import messagebox, scrolledtext
import json
import threading
import queue
import protocollo_mm

class MastermindAppGUI:
    def __init__(self, root, socket_client):
        self.root = root
        self.socket_client = socket_client
        self.root.title("Mastermind Premium Suite")
        self.root.geometry("450x750")
        self.root.configure(bg="#2C3E50")

        #coda per ricevere in modo sicuro i pacchetti
        self.network_queue = queue.Queue()
        self.running = True

        self.color_map = {"1": "red", "2": "blue", "3": "green", "4": "yellow"}
        self.current_guess = []
        self.tentativo_corrente = 0
        self.max_tentativi = 10
        self.modalita_corrente = None  # "singolo", "pvp", "spettatore"
        self.mio_turno = False

        #avvio il thread di ascolto 
        self.listener_thread = threading.Thread(target=self.ascolta_rete, daemon=True)
        self.listener_thread.start()

        #mostro il menu principale all'avvio
        self.container = tk.Frame(self.root, bg="#2C3E50")
        self.container.pack(fill=tk.BOTH, expand=True)
        self.mostra_menu_principale()

        # controlla la coda dei messaggi ogni 100ms
        self.root.after(100, self.processa_coda_rete)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def clear_screen(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    #menu principale
    def mostra_menu_principale(self):
        self.clear_screen()
        self.modalita_corrente = None

        lbl = tk.Label(self.container, text="🏆 MASTERMIND MENU 🏆", font=("Arial", 20, "bold"), bg="#2C3E50", fg="white")
        lbl.pack(pady=40)

        pulsanti = [
            ("🤖 Contro il Server (Singolo)", "1"),
            ("⚔️ Contro un altro Giocatore (PvP)", "2"),
            ("📊 Visualizza Classifica", "3"),
            ("👁️ Fai da Spettatore", "4")
        ]

        for testo, scelta in pulsanti:
            btn = tk.Button(self.container, text=testo, font=("Arial", 13), bg="#34495E", fg="white",
                            width=30, height=2, bd=0, activebackground="#415B76", activeforeground="white",
                            command=lambda s=scelta: self.seleziona_opzione_menu(s))
            btn.pack(pady=12)

    def seleziona_opzione_menu(self, scelta):
        if scelta in ["1", "2"]:
            self.modalita_corrente = "singolo" if scelta == "1" else "pvp"
            pacchetto = {"op": protocollo_mm.OP_GIOCA, "scelta": scelta}
            self.socket_client.send(json.dumps(pacchetto).encode())
            self.mostra_schermata_gioco()
            if scelta == "2":
                self.disegna_log_messaggi("[*] In attesa di un avversario...")
                
        elif scelta == "3":
            pacchetto = {"op": protocollo_mm.OP_CLASSIFICA}
            self.socket_client.send(json.dumps(pacchetto).encode())
            
        elif scelta == "4":
            self.modalita_corrente = "spettatore"
            pacchetto = {"op": protocollo_mm.OP_LISTA_SPEC}
            self.socket_client.send(json.dumps(pacchetto).encode())

    #tabellone gioco e pvp
    def mostra_schermata_gioco(self):
        self.clear_screen()
        self.current_guess.clear()
        self.tentativo_corrente = 0
        self.mio_turno = (self.modalita_corrente == "singolo")

        
        self.lbl_status = tk.Label(self.container, text="Inizializzazione...", font=("Arial", 12, "bold"), bg="#16A085", fg="white", pady=5)
        self.lbl_status.pack(fill=tk.X)

        
        frame_centrale = tk.Frame(self.container, bg="#2C3E50")
        frame_centrale.pack(pady=5, fill=tk.BOTH, expand=True)

        
        self.canvas = tk.Canvas(frame_centrale, width=240, height=460, bg="#ECF0F1", highlightthickness=1)
        self.canvas.pack(side=tk.LEFT, padx=10)
        self.disegna_griglia_vuota()

        
        self.txt_log = scrolledtext.ScrolledText(frame_centrale, width=20, height=28, font=("Arial", 9), bg="#1C2833", fg="#85929E", state=tk.DISABLED)
        self.txt_log.pack(side=tk.RIGHT, padx=10, fill=tk.Y)

        # input chat (solo se in pvp)
        if self.modalita_corrente == "pvp":
            frame_chat_input = tk.Frame(self.container, bg="#2C3E50")
            frame_chat_input.pack(fill=tk.X, padx=10, pady=2)
            self.ent_chat = tk.Entry(frame_chat_input, font=("Arial", 11))
            self.ent_chat.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(frame_chat_input, text="Invia Chat", bg="#2980B9", fg="white", command=self.invia_chat).pack(side=tk.RIGHT, padx=5)

        #pannello pulsanti colori 
        if self.modalita_corrente != "spettatore":
            frame_colori = tk.Frame(self.container, bg="#2C3E50")
            frame_colori.pack(pady=5)
            for num, color in self.color_map.items():
                btn = tk.Button(frame_colori, bg=color, width=4, height=1, command=lambda n=num: self.aggiungi_colore(n))
                btn.pack(side=tk.LEFT, padx=4)

            frame_azioni = tk.Frame(self.container, bg="#2C3E50")
            frame_azioni.pack(pady=5)
            self.btn_invia = tk.Button(frame_azioni, text="Invia Mossa", font=("Arial", 11, "bold"), bg="#27AE60", fg="white", command=self.invia_mossa)
            self.btn_invia.pack(side=tk.LEFT, padx=5)
            tk.Button(frame_azioni, text="Cancella", font=("Arial", 11), bg="#E74C3C", fg="white", command=self.cancella_mossa).pack(side=tk.LEFT, padx=5)

        # bottone abbandona 
        tk.Button(self.container, text="🚪 Torna al Menu principale", font=("Arial", 10), bg="#7F8C8D", fg="white", command=self.mostra_menu_principale).pack(pady=5)
        self.aggiorna_stato_pulsanti_turno()

    def disegna_griglia_vuota(self):
        for riga in range(self.max_tentativi):
            y_offset = 420 - (riga * 42)
            for col in range(4):
                x_offset = 15 + (col * 38)
                self.canvas.create_oval(x_offset, y_offset, x_offset+25, y_offset+25, fill="#BDC3C7", outline="#7F8C8D")
            self.canvas.create_rectangle(170, y_offset, 225, y_offset+25, outline="#7F8C8D")

    def disegna_log_messaggi(self, testo):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, testo + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def aggiorna_stato_pulsanti_turno(self):
        if self.modalita_corrente == "pvp":
            if self.mio_turno:
                self.lbl_status.config(text="🟢 TOCCA A TE! Inserisci 4 colori", bg="#27AE60")
                self.btn_invia.config(state=tk.NORMAL)
            else:
                self.lbl_status.config(text="🔴 Attesa mossa dell'avversario...", bg="#D35400")
                self.btn_invia.config(state=tk.DISABLED)
        elif self.modalita_corrente == "singolo":
            self.lbl_status.config(text="🤖 Partita in Singolo contro il Server", bg="#2980B9")

    def aggiungi_colore(self, numero_colore):
        if self.modalita_corrente == "pvp" and not self.mio_turno:
            return
        if len(self.current_guess) < 4:
            self.current_guess.append(numero_colore)
            self.aggiorna_mossa_in_corso()

    def cancella_mossa(self):
        self.current_guess.clear()
        self.aggiorna_mossa_in_corso()

    def aggiorna_mossa_in_corso(self):
        y_offset = 420 - (self.tentativo_corrente * 42)
        for col in range(4):
            x_offset = 15 + (col * 38)
            colore = self.color_map[self.current_guess[col]] if col < len(self.current_guess) else "#BDC3C7"
            self.canvas.create_oval(x_offset, y_offset, x_offset+25, y_offset+25, fill=colore, outline="black")

    def invia_mossa(self):
        if len(self.current_guess) != 4:
            messagebox.showwarning("Attenzione", "Scegli 4 colori!")
            return
        pacchetto = {"op": protocollo_mm.OP_MOSSA, "combinazione": self.current_guess}
        self.socket_client.send(json.dumps(pacchetto).encode())
        if self.modalita_corrente == "pvp":
            self.mio_turno = False
            self.aggiorna_stato_pulsanti_turno()

    def invia_chat(self):
        testo = self.ent_chat.get().strip()
        if testo:
            pacchetto = {"op": protocollo_mm.OP_CHAT, "messaggio": testo}
            self.socket_client.send(json.dumps(pacchetto).encode())
            self.disegna_log_messaggi(f"[Tu]: {testo}")
            self.ent_chat.delete(0, tk.END)

    def disegna_risultato_pioli(self, neri, bianchi, riga_target=None):
        riga = riga_target if riga_target is not None else self.tentativo_corrente
        y_offset = 420 - (riga * 42)
        posizioni = [(175, y_offset+4), (190, y_offset+4), (175, y_offset+14), (190, y_offset+14)]
        pioli = ["black"] * neri + ["white"] * bianchi
        for i, color in enumerate(pioli):
            if i < 4:
                px, py = posizioni[i]
                self.canvas.create_oval(px, py, px+8, py+8, fill=color, outline="gray")

    #classifica
    def mostra_schermata_classifica(self, dati_classifica):
        self.clear_screen()
        lbl = tk.Label(self.container, text="📊 CLASSIFICA GLOBAL TOP 5 📊", font=("Arial", 16, "bold"), bg="#2C3E50", fg="yellow")
        lbl.pack(pady=25)

        frame_tabella = tk.Frame(self.container, bg="#34495E", padx=10, pady=10)
        frame_tabella.pack(pady=10, padx=20, fill=tk.X)

        for posizione, (nome, punti) in enumerate(dati_classifica, 1):
            riga = tk.Frame(frame_tabella, bg="#34495E")
            riga.pack(fill=tk.X, pady=6)
            
            lbl_pos = tk.Label(riga, text=f"{posizione}.", font=("Arial", 12, "bold"), bg="#34495E", fg="white", width=4, anchor="w")
            lbl_pos.pack(side=tk.LEFT)
            
            lbl_nome = tk.Label(riga, text=nome.upper(), font=("Arial", 12), bg="#34495E", fg="#ECF0F1", width=18, anchor="w")
            lbl_nome.pack(side=tk.LEFT)
            
            lbl_punti = tk.Label(riga, text=f"{punti} Punti", font=("Arial", 12, "bold"), bg="#34495E", fg="#2ECC71", width=10, anchor="e")
            lbl_punti.pack(side=tk.RIGHT)

        tk.Button(self.container, text="⬅️ Torna al Menu", font=("Arial", 12), bg="#E67E22", fg="white", command=self.mostra_menu_principale).pack(pady=30)

    #-tribuna spettatore
    def mostra_schermata_lista_partite(self, lista_partite):
        self.clear_screen()
        lbl = tk.Label(self.container, text="👁️ PARTITE IN CORSO IN TRIBUNA 👁️", font=("Arial", 14, "bold"), bg="#2C3E50", fg="white")
        lbl.pack(pady=25)

        if not lista_partite:
            tk.Label(self.container, text="Nessuna partita attiva al momento.", font=("Arial", 12, "italic"), bg="#2C3E50", fg="gray").pack(pady=20)
        else:
            for idx, descrizione in enumerate(lista_partite, 1):
                frame_match = tk.Frame(self.container, bg="#34495E")
                frame_match.pack(fill=tk.X, padx=30, pady=8)
                
                tk.Label(frame_match, text=descrizione, font=("Arial", 11), bg="#34495E", fg="white", anchor="w").pack(side=tk.LEFT, padx=10, pady=10)
                btn_join = tk.Button(frame_match, text="Guarda", bg="#2ECC71", fg="white", font=("Arial", 10, "bold"),
                                     command=lambda i=idx: self.unisciti_come_spettatore(i))
                btn_join.pack(side=tk.RIGHT, padx=10)

        tk.Button(self.container, text="⬅️ Torna al Menu", font=("Arial", 12), bg="#7F8C8D", fg="white", command=self.mostra_menu_principale).pack(pady=20)

    def unisciti_come_spettatore(self, indice):
        pacchetto = {"op": protocollo_mm.OP_JOIN_SPEC, "indice": str(indice)}
        self.socket_client.send(json.dumps(pacchetto).encode())
        self.mostra_schermata_gioco()
        self.lbl_status.config(text="Mode Spettatore: Osservazione Partita", bg="#8E44AD")

    #threading
    def ascolta_rete(self):
        """Eseguito in un thread separato. Riceve dati dal server e li mette in coda."""
        while self.running:
            try:
                risposta_raw = self.socket_client.recv(2024).decode()
                if not risposta_raw:
                    break
                # Gestione di pacchetti multipli accumulati nel buffer TCP
                for blocco in risposta_raw.split("}{"):
                    frammento = blocco
                    if not frammento.startswith("{"): frammento = "{" + frammento
                    if not frammento.endswith("}"): frammento = frammento + "}"
                    
                    try:
                        pacchetto = json.loads(frammento)
                        self.network_queue.put(pacchetto)
                    except json.JSONDecodeError:
                        pass
            except:
                break

    def processa_coda_rete(self):
        
        try:
            while True:
                pacchetto = self.network_queue.get_nowait()
                op = pacchetto.get("op")

                if op == protocollo_mm.OP_DATI_CLASSIFICA:
                    self.mostra_schermata_classifica(pacchetto["dati"])

                elif op == protocollo_mm.OP_DATI_TRIBUNA:
                    self.mostra_schermata_lista_partite(pacchetto["partite"])

                elif op == protocollo_mm.OP_MESSAGGIO:
                    msg = pacchetto.get("messaggio", "")
                    if self.modalita_corrente in ["pvp", "singolo"]:
                        self.disegna_log_messaggi(f"[SISTEMA]: {msg}")

                elif op == protocollo_mm.OP_TURNO:
                    self.mio_turno = True
                    self.aggiorna_stato_pulsanti_turno()
                    self.disegna_log_messaggi(f"🔔 Tocca a te!")

                # messaggi di chat dell'avversario
                elif op == protocollo_mm.OP_CHAT:
                    self.disegna_log_messaggi(pacchetto.get("messaggio", ""))

                # flusso spettatore in tempo reale
                elif op == protocollo_mm.OP_SPETTATORE:
                    msg = pacchetto.get("messaggio", "")
                    self.disegna_log_messaggi(f"📺 {msg}")
                    if "ha giocato" in msg and "Neri:" in msg:
                        try:
                            self.disegna_risultato_pioli(1, 1) 
                            self.tentativo_corrente += 1
                        except: pass

                # risultato della mossa (Singolo e PvP)
                elif op == protocollo_mm.OP_RISULTATO:
                    if "messaggio" in pacchetto and not ("neri" in pacchetto):
                        # Caso vittoria a tavolino o sconfitta passiva
                        messagebox.showinfo("Fine Partita", pacchetto["messaggio"])
                        self.mostra_menu_principale()
                    else:
                        neri = pacchetto.get("neri", 0)
                        bianchi = pacchetto.get("bianchi", 0)
                        vittoria = pacchetto.get("vittoria", False)

                        self.disegna_risultato_pioli(neri, bianchi)
                        self.disegna_log_messaggi(f"-> Esito: {neri} Neri, {bianchi} Bianchi")
                        
                        self.current_guess.clear()
                        self.tentativo_corrente += 1

                        if vittoria:
                            messagebox.showinfo("Vittoria!", "🏆 Partita Conclusa con Successo!")
                            self.mostra_menu_principale()
                        elif "messaggio" in pacchetto:
                            # l'avversario ha indovinato prima di me
                            messagebox.showinfo("Partita Terminata", pacchetto["messaggio"])
                            self.mostra_menu_principale()

                elif op == protocollo_mm.OP_ERRORE:
                    messagebox.showerror("Errore Server", pacchetto.get("messaggio", "Si è verificato un errore."))
                    self.mostra_menu_principale()

                self.network_queue.task_done()
        except queue.Empty:
            pass

        if self.running:
            self.root.after(100, self.processa_coda_rete)

    def on_closing(self):
        self.running = False
        try:
            self.socket_client.send(json.dumps({"op": protocollo_mm.OP_ESCI}).encode())
        except: pass
        self.root.destroy()