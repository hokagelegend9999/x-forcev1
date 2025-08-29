# session_manager.py

import json
import logging

SESSION_FILE = "user_sessions.json"

def save_sessions(context):
    """Menyimpan data sesi dari bot_data ke file JSON."""
    try:
        sessions_to_save = {}
        # Konversi chat_id dari integer ke string karena JSON hanya bisa key string
        for chat_id, data in context.bot_data.get('user_sessions', {}).items():
            sessions_to_save[str(chat_id)] = data
            
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions_to_save, f, indent=4)
        logging.info("Sesi berhasil disimpan ke disk.")
    except Exception as e:
        logging.error(f"Gagal menyimpan sesi: {e}")

def load_sessions():
    """Membaca data sesi dari file JSON."""
    try:
        with open(SESSION_FILE, 'r') as f:
            sessions_from_disk = json.load(f)
            # Konversi kembali chat_id dari string ke integer
            return {int(chat_id): data for chat_id, data in sessions_from_disk.items()}
    except FileNotFoundError:
        logging.warning(f"File sesi {SESSION_FILE} tidak ditemukan. Memulai dengan sesi kosong.")
        return {}
    except (json.JSONDecodeError, ValueError):
        logging.error(f"Gagal membaca file {SESSION_FILE}. File mungkin rusak. Memulai dengan sesi kosong.")
        return {}