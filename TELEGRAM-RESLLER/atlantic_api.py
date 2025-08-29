# atlantic_api.py

import requests
import logging
import config
import time

def get_deposit_methods():
    """Mengambil daftar metode deposit dari Atlantic H2H."""
    url = f"{config.ATLANTIC_BASE_URL}/deposit/metode"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'api_key': config.ATLANTIC_API_KEY}
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("status") is True:
            return data.get("data", [])
        else:
            logging.error(f"Atlantic API Error (get_methods): {data.get('message')}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Gagal menghubungi Atlantic API (get_methods): {e}")
        return None

def create_deposit_request(chat_id: int, method: str, type: str, amount: int):
    """Membuat permintaan deposit baru ke Atlantic H2H."""
    url = f"{config.ATLANTIC_BASE_URL}/deposit/create"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    # Buat ID Referensi unik untuk setiap transaksi
    reff_id = f"TOPUP-{chat_id}-{int(time.time())}"
    
    payload = {
        'api_key': config.ATLANTIC_API_KEY,
        'reff_id': reff_id,
        'nominal': amount,
        'type': type,
        'metode': method
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("status") is True:
            return data.get("data")
        else:
            logging.error(f"Atlantic API Error (create_deposit): {data.get('message')}")
            return {"error": data.get('message', 'Terjadi kesalahan yang tidak diketahui.')}
    except requests.exceptions.RequestException as e:
        logging.error(f"Gagal menghubungi Atlantic API (create_deposit): {e}")
        return {"error": "Tidak dapat terhubung ke server pembayaran."}