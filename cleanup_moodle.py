#!/usr/bin/env python3
import os
import re
import sys
import argparse
import shutil

def sanitize_name(name):
    """
    Rimuove i caratteri non supportati su Windows/macOS/Linux
    e gestisce gli spazi vuoti o i punti finali.
    """
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', name)
    sanitized = sanitized.strip(' .')
    
    if not sanitized:
        sanitized = "unnamed"
        
    return sanitized

def check_and_convert_html(file_path):
    """
    Legge un file .html. Se è un semplice redirect (come quelli generati da edu-sync)
    ne estrae il link, sovrascrive il file inserendoci solo il link come testo semplice,
    e restituisce True (così che l'estensione diventi .txt).
    Se è un HTML strutturato (es. una vera pagina), restituisce False.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Cerchiamo il meta tag refresh
        match = re.search(r'<meta\s+http-equiv="refresh"\s+content="0;\s*url=([^"]+)"', content, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Sovrascrive il file salvando solo l'URL in chiaro
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(url + '\n')
            return True
            

            
    except Exception:
        pass
        
    return False

def get_unique_path(parent_dir, desired_name, original_name):
    """
    Assicura che il nuovo percorso sia univoco.
    Se il nome desiderato esiste già (ed è un file diverso),
    aggiunge un suffisso numerico _1, _2, ecc.
    """
    if desired_name == original_name:
        return os.path.join(parent_dir, desired_name)
        
    target_path = os.path.join(parent_dir, desired_name)
    
    if not os.path.exists(target_path):
        return target_path
    
    name, ext = os.path.splitext(desired_name)
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        target_path = os.path.join(parent_dir, new_name)
        if not os.path.exists(target_path):
            return target_path
        counter += 1

def cleanup_directory(root_dir, strip_all_numbers=False):
    """
    Attraversa la directory partendo dalle foglie (bottom-up) per rinominare 
    prima il contenuto e poi i contenitori, evitando di rompere i percorsi.
    Inoltre, appiattisce le cartelle che contengono 1 solo elemento
    e rimuove eventuali cartelle vuote.
    """
    files_renamed = 0
    dirs_renamed = 0
    items_moved = 0
    empty_dirs_removed = 0

    for dirpath, dirnames, filenames in os.walk(root_dir, topdown=False):
        
        # Funzione helper per elaborare sia i file che le cartelle nello stesso modo
        def process_items(items, is_dir):
            nonlocal files_renamed, dirs_renamed
            parsed_items = []
            clean_name_counts = {}
            
            # Passaggio 1: Estrazione ID e calcolo del nome pulito base
            for item in items:
                if item.startswith('.'):
                    continue
                    
                old_path = os.path.join(dirpath, item)
                if not os.path.exists(old_path):
                    continue
                    
                if is_dir:
                    name, ext = item, ""
                else:
                    name, ext = os.path.splitext(item)
                    # Verifica i file .html: se sono redirect/link li converte in .txt
                    if ext.lower() == '.html':
                        if check_and_convert_html(old_path):
                            ext = '.txt'
                
                if strip_all_numbers:
                    match = re.match(r'^(\d+)\s+(.*)$', name)
                else:
                    # Consideriamo ID di Moodle solo i numeri di almeno 4 cifre senza zeri iniziali.
                    # Questo previene falsi positivi (es. "12 maggio", "09 - Appunti", ecc.)
                    match = re.match(r'^([1-9]\d{3,})\s+(.*)$', name)
                if match:
                    item_id = match.group(1)
                    clean_base = sanitize_name(match.group(2).strip())
                else:
                    item_id = None
                    clean_base = sanitize_name(name)
                    
                clean_full = f"{clean_base}{ext}"
                
                parsed_items.append({
                    'original': item,
                    'id': item_id,
                    'clean_base': clean_base,
                    'ext': ext,
                    'clean_full': clean_full
                })
                
                clean_name_counts[clean_full] = clean_name_counts.get(clean_full, 0) + 1
                
            # Passaggio 2: Ridenominazione e gestione conflitti
            for info in parsed_items:
                original = info['original']
                clean_full = info['clean_full']
                
                old_path = os.path.join(dirpath, original)
                if not os.path.exists(old_path):
                    continue
                
                target_path = os.path.join(dirpath, clean_full)
                
                conflict = False
                if clean_name_counts[clean_full] > 1:
                    conflict = True
                elif os.path.exists(target_path) and original != clean_full:
                    conflict = True
                    
                if conflict and info['id'] is not None:
                    desired_name = f"{info['clean_base']} [{info['id']}]{info['ext']}"
                else:
                    desired_name = clean_full
                    
                new_path = get_unique_path(dirpath, desired_name, original)
                
                if old_path != new_path:
                    os.rename(old_path, new_path)
                    icon = "Dir:" if is_dir else "File:"
                    print(f"{icon} '{original}'\n   -> '{os.path.basename(new_path)}'\n")
                    if is_dir:
                        dirs_renamed += 1
                    else:
                        files_renamed += 1

        # 1. & 2. Processa ed eventualmente rinomina il contenuto della cartella
        process_items(filenames, is_dir=False)
        process_items(dirnames, is_dir=True)

        # 3. Appiattimento e pulizia cartelle vuote
        if dirpath != root_dir:
            try:
                current_items = [f for f in os.listdir(dirpath) if not f.startswith('.')]
                if len(current_items) == 0:
                    shutil.rmtree(dirpath)
                    empty_dirs_removed += 1
                    print(f"Delete: cartella vuota '{os.path.basename(dirpath)}' eliminata\n")
                elif len(current_items) == 1:
                    single_item = current_items[0]
                    old_item_path = os.path.join(dirpath, single_item)
                    parent_dir = os.path.dirname(dirpath)
                    
                    # Calcoliamo un nome univoco nel genitore in caso di conflitti
                    new_item_path = get_unique_path(parent_dir, single_item, "")
                    
                    os.rename(old_item_path, new_item_path)
                    shutil.rmtree(dirpath)
                    
                    items_moved += 1
                    print(f"Move: '{single_item}'\n   -> risalito in '{os.path.basename(parent_dir)}'\n   (cartella '{os.path.basename(dirpath)}' eliminata)\n")
            except Exception as e:
                pass

    return files_renamed, dirs_renamed, items_moved, empty_dirs_removed

def main():
    parser = argparse.ArgumentParser(
        description="Pulisce i nomi dei file e delle cartelle scaricati da Moodle tramite edu-sync.",
        epilog="""
Esempi di utilizzo:

  python3 cleanup_moodle.py ./moodle-scraper
        Pulisce la cartella ./moodle-scraper usando un percorso relativo.
        
  python3 cleanup_moodle.py "/Users/mattia/Downloads/moodle-scraper"
        Pulisce la cartella usando un percorso assoluto.
        
  python3 cleanup_moodle.py "~/Downloads/moodle-scraper copy"
        Pulisce la cartella usando la scorciatoia home (~), anche se messa tra virgolette.

Cosa fa il programma:
  1. Rimuove l'ID numerico di Moodle all'inizio dei file e cartelle (solo se composto da almeno 4 cifre senza zeri iniziali, per evitare falsi positivi come date o numeri di lezione). Usare --strip-all-numbers per disabilitare questo controllo.
  2. Analizza i file .html: se sono semplici redirect/link creati da edu-sync, 
     estrae l'URL in chiaro e converte l'estensione in .txt. Le vere pagine HTML
     strutturate vengono invece preservate.
  3. Sanitizza i nomi per renderli compatibili in modo nativo su Linux, macOS e Windows.
  4. Appiattisce le cartelle contenenti un solo file/sottocartella, spostando il contenuto
     nella directory madre ed eliminando la cartella vuota.
  5. Rimuove eventuali cartelle completamente vuote.
  6. Gestione conflitti intelligente: se due risorse finiscono per avere lo stesso nome, 
     il programma utilizzerà l'ID numerico rimosso e lo accoderà alla fine (es. nome [118586].pdf).
  7. Sicurezza aggiuntiva: se anche i nomi post-spostamento ID dovessero entrare 
     in conflitto, il file verrà preservato aggiungendo un contatore (_1, _2).
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        "path",
        help="Percorso relativo o assoluto della cartella da pulire"
    )
    
    parser.add_argument(
        "--strip-all-numbers",
        action="store_true",
        help="Disabilita il controllo di sicurezza e rimuove QUALSIASI numero all'inizio di file/cartelle."
    )
    
    args = parser.parse_args()
    
    expanded_path = os.path.expanduser(args.path)
    target_dir = os.path.abspath(expanded_path)
    
    if not os.path.isdir(target_dir):
        print(f"Errore: '{target_dir}' non è una cartella valida o non esiste.")
        sys.exit(1)
        
    print(f"Inizio pulizia della cartella: {target_dir}\n")
    f_count, d_count, m_count, e_count = cleanup_directory(target_dir, strip_all_numbers=args.strip_all_numbers)
    print(f"Pulizia completata! Rinominati {f_count} file e {d_count} cartelle. Effettuati {m_count} spostamenti di appiattimento e rimosse {e_count} cartelle vuote.")

if __name__ == "__main__":
    main()
