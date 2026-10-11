import hashlib
import json
import threading
import secrets 

def registra_utente(username, password):
    try:
        with open("utenti.json", "r") as file:
            utenti = json.load(file)
    except:
        utenti = {}

    if username in utenti:
        return False, "username già esistente"

    salt = secrets.token_hex(16)
    
    password_salata = password + salt

    password_cifrata = hashlib.sha256(password_salata.encode()).hexdigest()

    utenti[username] = {"password": password_cifrata, "salt": salt, "punti": 0}

    with open("utenti.json", "w") as file:
        json.dump(utenti, file, indent=4)
        
    return True, "Registrazione completata"

def effettua_login(username, password):
    try:
        with open("utenti.json", "r") as file:
            utenti = json.load(file)
    except:
        utenti = {}

    if username not in utenti:
        return False, "Credenziali errate"

    salt_salvato = utenti[username].get("salt", "")
    
 
    password_salata = password + salt_salvato

    
    password_cifrata = hashlib.sha256(password_salata.encode()).hexdigest()

    
    if utenti[username]["password"] == password_cifrata:
        return True, f"Benvenuto {username}"
    else:
        return False, "Credenziali errate"


lock_file_utenti = threading.Lock()

def aggiorna_punteggio(username, variazione_punti):
   
    with lock_file_utenti:
        try:
            with open("utenti.json", "r") as file:
                utenti = json.load(file)

            #calcola il nuovo punteggio partendo da quello vecchio
            punteggio_attuale = utenti.get(username, {}).get("punti", 0)
            nuovo_punteggio = punteggio_attuale + variazione_punti

            
            if nuovo_punteggio < 0:
                nuovo_punteggio = 0

            #salviamo il nuovo punteggio
            utenti[username]["punti"] = nuovo_punteggio

            with open("utenti.json", "w") as file:
                json.dump(utenti, file, indent=4)

        except Exception as e:
            print(f"[ERRORE] Impossibile aggiornare i punti di {username}: {e}")