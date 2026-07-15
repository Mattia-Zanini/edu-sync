import argparse
from pathlib import Path
import yt_dlp
import re

def is_zoom_link_only(filepath: Path) -> str | None:
    """
    Legge il file txt e controlla se contiene solo e unicamente un link a zoom.us.
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
    
    # Espressione regolare per verificare che il link sia effettivamente 
    # un URL di condivisione registrazione di Zoom.
    # Controlla che inizi con http:// o https://, contenga zoom.us/rec/share/ o zoom.us/rec/play/.
    if re.match(r'^https?://([a-zA-Z0-9-]+\.)?zoom\.us/rec/(share|play)/.*$', link):
        return link
        
    return None

def download_video(url: str, output_dir: Path):
    """
    Scarica il video di Zoom utilizzando yt-dlp nella directory specificata.
    NOTA: Funziona solo se il video non è protetto da password.
    """
    # Configuriamo le opzioni di download per yt-dlp
    ydl_opts = {
        # Usa il titolo del video ricavato da yt-dlp per il nome del file e lo salva nella cartella target
        'outtmpl': str(output_dir / "%(title)s.%(ext)s"),
        # Mostra a schermo l'output di avanzamento del download
        'quiet': False,
        # Aggiunge delle pause randomiche per evitare di sovraccaricare il server ed essere bloccati
        'sleep_interval': 5,
        'max_sleep_interval': 10,
        # EVITA di riscaricare (sovrascrivere) il file se questo è già stato completamente scaricato in precedenza
        'nooverwrites': True,
    }
    
    # Inizializziamo yt-dlp con le opzioni e avviamo il download
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def main():
    # Definisce il parser per gli argomenti a riga di comando
    parser = argparse.ArgumentParser(
        description="""
        Cerca file .txt contenenti un singolo link a Zoom (registrazioni condivise)
        in modo ricorsivo e scarica il video usando yt-dlp.
        
        ATTENZIONE: Il download funziona solo per i video di Zoom pubblici, 
        ovvero NON protetti da password.
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
    print("Nota: Verranno saltati o andranno in errore i video protetti da password.")
    print("Premi Ctrl+C per interrompere in qualsiasi momento.\n")
    
    # Inizializza i contatori per il resoconto finale
    txt_files_processed = 0
    videos_downloaded = 0
    
    # Itera su tutti i file con estensione .txt nella cartella e in tutte le sottocartelle
    for txt_file in base_path.rglob("*.txt"):
        # Controlla se il file contiene un link valido
        link = is_zoom_link_only(txt_file)
        
        if link:
            txt_files_processed += 1
            print(f"[TROVATO] {txt_file.name}")
            print(f"  -> Link trovato: {link}")
            print(f"  -> Cartella di destinazione: {txt_file.parent}")
            
            try:
                print(f"  -> Download in corso...")
                # Scarica il video
                download_video(link, txt_file.parent)
                
                videos_downloaded += 1
                print(f"[SUCCESSO] Processamento di {txt_file.name} terminato.\n")
            except Exception as e:
                # Intercetta e stampa eventuali errori per non bloccare il loop sui file successivi
                print(f"[ERRORE] Impossibile scaricare da {link} (possibile video privato/protetto): {e}\n")

    # Stampa il riepilogo al termine del processo
    print("--- Riepilogo ---")
    print(f"File .txt con link analizzati: {txt_files_processed}")
    print(f"Video scaricati/processati con successo: {videos_downloaded}")

if __name__ == "__main__":
    main()
