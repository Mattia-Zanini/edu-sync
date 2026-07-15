import argparse
import os
import re
from pathlib import Path
import yt_dlp
import requests
import urllib.parse

def is_mediaspace_link_only(filepath: Path) -> str | None:
    """
    Legge il file txt e controlla se contiene solo e unicamente un link a mediaspace.unipd.it o kaltura.
    Ritorna il link se valido, altrimenti None.
    """
    try:
        # Apre il file in lettura con codifica utf-8
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"Errore nella lettura di {filepath}: {e}")
        return None

    # Divide il contenuto del file in righe e rimuove eventuali righe vuote
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    
    # Se il file contiene più di una riga (o nessuna), lo ignoriamo
    # perché cerchiamo solo file che contengano esclusivamente il link.
    if len(lines) != 1:
        return None
    
    link = lines[0]
    
    # Espressione regolare per verificare che il link sia effettivamente di Mediaspace Unipd o Kaltura.
    # Controlla che inizi con http:// o https:// e contenga i domini corretti.
    if re.match(r'^https?://(mediaspace\.unipd\.it|.*kaltura\.com)/.*$', link):
        return link
        
    return None

def extract_mediaspace_direct_url(link: str) -> tuple[str, str]:
    """
    Estrae l'URL diretto del file video MP4 e il titolo.
    Se è un link di Mediaspace, effettua il fetch della pagina per trovare il link interno.
    Se è già un link diretto a kaltura, lo restituisce direttamente.
    """
    # 1. GESTIONE LINK KALTURA DIRETTI
    # Se l'utente ha incollato un URL che punta già al server cfvod.kaltura.com
    if "cfvod.kaltura.com" in link:
        # Sostituiamo la parte "scf/" per ottenere l'URL diretto senza segmentazione in spezzoni
        direct_url = link.replace("cfvod.kaltura.com/scf/", "cfvod.kaltura.com/")
        return direct_url, "video_kaltura"

    # 2. GESTIONE LINK MEDIASPACE UNIPD
    title = "video_mediaspace"
    
    # Proviamo a estrarre il titolo direttamente dall'URL di mediaspace 
    # (es. /media/Titolo_del_video/ID_Video)
    match = re.search(r'mediaspace\.unipd\.it/media/([^/]+)/', link)
    if match:
        title_encoded = match.group(1)
        # Decodifichiamo i caratteri speciali dell'URL (es. i + diventano spazi)
        title = urllib.parse.unquote_plus(title_encoded)
        # Rimuoviamo eventuali caratteri che potrebbero dare problemi al sistema operativo nel salvataggio del file
        title = re.sub(r'[\\/*?:"<>|]', "", title)

    # Impostiamo un User-Agent per simulare un browser reale e prevenire blocchi da parte del server
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    # Facciamo una richiesta GET per scaricare il codice sorgente della pagina web
    response = requests.get(link, headers=headers)
    response.raise_for_status()
    html = response.text

    # Tramite espressioni regolari (regex) cerchiamo due parametri fondamentali nascosti nel JSON della pagina:
    # - dataUrl: è l'endpoint delle API di kaltura (playManifest)
    # - ks: è il token di sessione necessario per essere autorizzati a scaricare il video
    data_url_match = re.search(r'"dataUrl"\s*:\s*"([^"]+)"', html)
    ks_match = re.search(r'"ks"\s*:\s*"([^"]+)"', html)

    if not data_url_match or not ks_match:
        raise ValueError("Impossibile trovare i parametri 'dataUrl' o 'ks' nella pagina HTML. Assicurati che il video non sia privato e richieda il login.")

    # All'interno del JSON gli slash sono spesso escaped (es. \/), quindi li ripristiniamo (/)
    data_url = data_url_match.group(1).replace('\\/', '/')
    ks = ks_match.group(1)

    # Costruiamo l'URL completo per l'API aggiungendo il token come parametro della query string (?ks=...)
    play_manifest_url = f"{data_url}?ks={ks}"

    # Effettuiamo una richiesta all'API. Usiamo allow_redirects=False perché non vogliamo scaricare
    # subito il file, ma vogliamo solo intercettare dove ci manda (header Location).
    redirect_resp = requests.get(play_manifest_url, headers=headers, allow_redirects=False)
    
    # Controlliamo che il server ci stia effettivamente reindirizzando (codici HTTP 3xx)
    if redirect_resp.status_code not in (301, 302, 303, 307, 308):
        raise ValueError(f"Ci si aspettava un redirect al file MP4, ma si è ottenuto lo status code {redirect_resp.status_code}")

    # Estraiamo l'URL del file video dall'header Location
    location = redirect_resp.headers.get("Location")
    if not location:
        raise ValueError("L'header 'Location' (con il link al video) non è presente nella risposta.")

    # Infine, applichiamo la regola manuale: rimuoviamo "scf/" per forzare il download del file unico mp4 
    # anziché i singoli spezzoni o frame
    direct_mp4_url = location.replace("cfvod.kaltura.com/scf/", "cfvod.kaltura.com/")

    return direct_mp4_url, title

def download_video(direct_url: str, title: str, output_dir: Path):
    """
    Scarica il video diretto utilizzando yt-dlp nella directory specificata.
    """
    # Configuriamo le opzioni di download per yt-dlp
    ydl_opts = {
        # Specifica il percorso completo e il nome del file (Titolo_estratto.mp4)
        'outtmpl': str(output_dir / f"{title}.%(ext)s"),
        # Mostra a schermo l'output di avanzamento del download
        'quiet': False,
        # Aggiunge delle pause randomiche per evitare di sovraccaricare il server ed essere bloccati
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        # EVITA di riscaricare (sovrascrivere) il file se questo è già stato completamente scaricato in precedenza
        'nooverwrites': True,
        # 'restrictfilenames': True,  # Facoltativo, utile se vuoi limitare ai soli caratteri ASCII
    }
    
    # Inizializziamo yt-dlp con le opzioni e avviamo il download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([direct_url])

def main():
    # Definisce il parser per gli argomenti a riga di comando
    parser = argparse.ArgumentParser(
        description="""
        Cerca file .txt contenenti un singolo link a Mediaspace Unipd o Kaltura 
        in modo ricorsivo, estrae l'URL diretto (rimuovendo 'scf/' in automatico) e scarica il video.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Aggiunge l'argomento obbligatorio 'path' (es. './cartella')
    parser.add_argument("path", help="Percorso relativo o assoluto della cartella da elaborare")
    args = parser.parse_args()

    # Risolve il percorso inserito ottenendo il percorso assoluto
    base_path = Path(args.path).resolve()
    
    # Verifica che il percorso sia valido e che sia effettivamente una cartella
    if not base_path.exists() or not base_path.is_dir():
        print(f"Errore: Il percorso '{base_path}' non esiste o non è una cartella.")
        return

    print(f"Inizio ricerca di file .txt in: {base_path}")
    print("Premi Ctrl+C per interrompere in qualsiasi momento.\n")
    
    # Inizializza i contatori per il resoconto finale
    txt_files_processed = 0
    videos_downloaded = 0
    
    # Itera su tutti i file con estensione .txt nella cartella e in tutte le sottocartelle
    for txt_file in base_path.rglob("*.txt"):
        # Controlla se il file contiene un link valido
        link = is_mediaspace_link_only(txt_file)
        
        if link:
            txt_files_processed += 1
            print(f"[TROVATO] {txt_file.name}")
            print(f"  -> Link trovato: {link}")
            print(f"  -> Cartella di destinazione: {txt_file.parent}")
            
            try:
                print("  -> Estrazione dell'URL diretto del video...")
                # Lancia la funzione per ottenere link MP4 e titolo
                direct_url, title = extract_mediaspace_direct_url(link)
                
                print(f"  -> Titolo video: '{title}'")
                print(f"  -> Download in corso...")
                
                # Scarica il video
                download_video(direct_url, title, txt_file.parent)
                
                videos_downloaded += 1
                print(f"[SUCCESSO] Processamento di {txt_file.name} terminato.\n")
            except Exception as e:
                # Intercetta e stampa eventuali errori per non bloccare il loop sui file successivi
                print(f"[ERRORE] Impossibile scaricare da {link}: {e}\n")

    # Stampa il riepilogo al termine del processo
    print("--- Riepilogo ---")
    print(f"File .txt con link analizzati: {txt_files_processed}")
    print(f"Video scaricati/processati con successo: {videos_downloaded}")

if __name__ == "__main__":
    main()
