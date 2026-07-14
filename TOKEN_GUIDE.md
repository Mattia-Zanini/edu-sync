# Guida per ottenere il Token Moodle (UniPD SSO)

Quando il portale Moodle utilizza un'autenticazione Single Sign-On (SSO) come Shibboleth (come nel caso dell'Università di Padova), l'autenticazione standard tramite username e password tramite l'opzione `--username` di `edu-sync-cli` non funziona. È necessario recuperare manualmente il token di sessione ed inserirlo nel programma.

Ecco i passaggi dettagliati per intercettare il token dal browser.

---

## Passaggi per ottenere il Token

0. **Assicurati di non essere loggato su Moodle:**
   Prima di iniziare, è fondamentale effettuare il **logout** dal sito di Moodle nel tuo browser (oppure utilizzare una finestra di navigazione in incognito). Se sei già loggato, il portale potrebbe saltare la schermata di login SSO, rendendo impossibile catturare la richiesta corretta.

1. **Visita il link di autenticazione dell'app mobile:**
   Apri una scheda nel tuo browser e visita il seguente URL (che simula la richiesta di login per l'app mobile ufficiale):
   ```text
   https://stem.elearning.unipd.it/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=123&urlscheme=moodlemobile
   ```

2. **Apri la console sviluppatori (Network):**
   Prima di fare qualsiasi altra cosa, apri gli Strumenti per Sviluppatori del browser premendo **F12** (o facendo click destro sulla pagina -> *Ispeziona*) e spostati nella scheda **Rete** (o *Network*).

3. **Effettua il login:**
   Inserisci le tue credenziali di ateneo ed effettua l'accesso tramite la pagina del Single Sign-On (SSO).

4. **Trova il redirect negli header di rete:**
   - Al termine del login, Moodle proverà a reindirizzarti all'applicazione Moodle Mobile utilizzando uno schema speciale (`moodlemobile://`).
   - Nel browser, questa richiesta non andrà a buon fine (poiché il sistema non sa come gestire questo indirizzo) e comparirà come una **risorsa segnata in rosso** nella scheda **Rete**.
   - Clicca sulla risorsa rossa e spostati nella scheda **Headers**.
   - Scorri fino alla sottosezione **Response Headers** (Intestazioni di risposta) e cerca il campo **`Location:`**. Il suo valore sarà nel formato:
     ```text
     moodlemobile://token=STRINGA_IN_BASE64
     ```
   - Copia la `STRINGA_IN_BASE64` (tutto ciò che si trova dopo `token=`).

5. **Decodifica la stringa Base64:**
   Apri il terminale del tuo PC ed esegui la decodifica della stringa copiata:
   ```bash
   echo "INCOLLA_QUI_LA_STRINGA_BASE64" | base64 -d
   ```
   L'output decodificato avrà questa struttura:
   ```text
   [firma_esadecimale]:::[token_esadecimale_32_caratteri]:::[token_privato]
   ```

6. **Estrai il token di sessione:**
   Il token di cui hai bisogno è la stringa esadecimale centrale composta da esattamente **32 caratteri** (compresa tra il primo ed il secondo gruppo di `:::`).

---

## Configurazione di `edu-sync-cli`

Una volta ottenuto il token di 32 caratteri:

1. Esegui il comando `add` **senza** specificare l'opzione `--username`:
   ```bash
   ./edu-sync-cli add https://stem.elearning.unipd.it ~/Downloads/moodle-scraper
   ```
2. Quando il programma richiede il `Token:`, incollalo e premi **Invio**.
