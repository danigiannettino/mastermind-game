def calcola_punteggio(codice_segreto, combinazione_utente):
    neri=0
    bianchi=0
    #creo delle copie per poterle modificare senza distruggere il codice originale
    copia_segreto=list(codice_segreto)
    copia_proposta=list(combinazione_utente)

    #neri posizione esatta
    for i in range(4):
        if copia_proposta[i]== copia_segreto[i]:
            neri += 1
            copia_segreto[i]= None
            copia_proposta[i]= None

    #bianchi colore giusto posizione sbagliata
    for i in range(4):
        if copia_proposta[i] is not None:
            if copia_proposta[i] in copia_segreto:
                bianchi += 1
                indice= copia_segreto.index(copia_proposta[i])
                copia_segreto[indice] = None

    ha_vinto = (neri == 4)
    return neri, bianchi, ha_vinto

