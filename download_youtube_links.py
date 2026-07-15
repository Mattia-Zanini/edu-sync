import argparse
import os
import re
from pathlib import Path
import yt_dlp

def is_youtube_link_only(filepath: Path) -> str | None:
    """
    Legge il file txt e controlla se contiene solo e unicamente un link a YouTube.
    Ritorna il link se valido, altrimenti None.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        print(f"Errore nella lettura di {filepath}: {e}")
        return None

    # Rimuove le righe vuote
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    
    # Se c'è più di una riga (o nessuna), consideriamo che non sia un file con un singolo link
    if len(lines) != 1:
        return None
    
    link = lines[0]
    
    # Regex per verificare che assomigli a un link di YouTube
    youtube_regex = re.compile(r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$')
    if youtube_regex.match(link):
        return link
        
    return None

def download_video(link: str, output_dir: Path):
    """
    Scarica il video di YouTube utilizzando yt-dlp nella directory specificata.
    """
    # Imposta le opzioni per yt-dlp. 
    # outtmpl definisce dove salvare e come chiamare il file.
    ydl_opts = {
        'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
        # Scarica la migliore qualità disponibile e unisci i formati
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'noplaylist': True, # Per sicurezza scarichiamo solo il singolo video
        'quiet': False,
        # Pausa randomica tra i download per evitare blocchi da parte di YouTube
        'sleep_interval': 10,
        'max_sleep_interval': 20,
        'sleep_requests': 0.75,
        'sleep_subtitles': 5,
        
        # Sanitizza i nomi dei file (solo ASCII, sostituisce spazi con underscore)
        'restrictfilenames': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])

def main():
    parser = argparse.ArgumentParser(
        description="""
        Cerca file .txt contenenti un singolo link a YouTube in modo ricorsivo e scarica il video.
        
        CONSIGLIO: È altamente raccomandato eseguire questo script DOPO 
        aver processato la cartella con cleanup_moodle.py.
        """,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", help="Percorso relativo o assoluto della cartella da elaborare")
    args = parser.parse_args()

    base_path = Path(args.path).resolve()
    
    if not base_path.exists() or not base_path.is_dir():
        print(f"Errore: Il percorso '{base_path}' non esiste o non è una cartella.")
        return

    print(f"Inizio ricerca di file .txt in: {base_path}")
    print("Premi Ctrl+C per interrompere in qualsiasi momento.\n")
    
    txt_files_processed = 0
    videos_downloaded = 0
    
    for txt_file in base_path.rglob("*.txt"):
        txt_files_processed += 1
        link = is_youtube_link_only(txt_file)
        
        if link:
            print(f"[TROVATO] {txt_file.name}")
            print(f"  -> Link: {link}")
            print(f"  -> Cartella di destinazione: {txt_file.parent}")
            try:
                download_video(link, txt_file.parent)
                videos_downloaded += 1
                print(f"[SUCCESSO] Video scaricato in: {txt_file.parent}\n")
            except Exception as e:
                print(f"[ERRORE] Impossibile scaricare {link}: {e}\n")

    print("--- Riepilogo ---")
    print(f"File .txt totali analizzati: {txt_files_processed}")
    print(f"Video scaricati: {videos_downloaded}")

if __name__ == "__main__":
    main()
