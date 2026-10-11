import threading

chiave_stanza = threading.Lock()
attesa = None

def cerca_avversario(socket_giocatore, username):
    global attesa

    # entra un solo thread alla volta
    with chiave_stanza:
        if attesa is None:
            # tutto libero, primo ad arrivare
            print(f"{username} è entrato in attesa")

            # cercapersone per mettermi in pausa
            mio_evento = threading.Event()

            # lascio i miei dati
            attesa = {
                "socket": socket_giocatore,
                "username": username,
                "evento": mio_evento,
                "avversario_socket": None,
                "avversario_username": None
            }

            sono_il_primo = True
            miei_dati = attesa

        else:
            # caso in cui c'è già qualcuno e lo sfido
            print(f"{username} ha trovato l'avversario {attesa['username']}")

            # salvo i dati del primo
            primo_giocatore = attesa

            primo_giocatore["avversario_socket"] = socket_giocatore
            primo_giocatore["avversario_username"] = username

            # libero l'attesa per i prossimi giocatori
            attesa = None
            sono_il_primo = False

    if sono_il_primo:
        # se sono il primo metto in pausa il thread finché non trovo qualcuno
        mio_evento.wait()

        # la partita inizia quando suona l'event
        return {
            "ruolo": "Giocatore 1",
            "mio_socket": socket_giocatore,
            "mio_username": username,
            "avversario_socket": miei_dati["avversario_socket"],
            "avversario_username": miei_dati["avversario_username"]
        }
    else:
        # se sono il secondo faccio scattare il cercapersone del giocatore 1
        primo_giocatore["evento"].set()

        return {
            "ruolo": "Giocatore 2",
            "mio_socket": socket_giocatore,
            "mio_username": username,
            "avversario_socket": primo_giocatore["socket"],
            "avversario_username": primo_giocatore["username"]
        }
