# keyboards.py - VERSI FINAL

from telegram import ReplyKeyboardMarkup

def get_main_menu_keyboard():
    """Mengembalikan keyboard untuk menu utama PENGGUNA BIASA."""
    keyboard = [
        ["Cek Paket Saya", "Beli Paket XUT"],
        ["Beli Paket by Family", "/topup"],
        ["/logout"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_admin_menu_keyboard():
    """Mengembalikan keyboard komprehensif untuk menu ADMIN."""
    keyboard = [
        # --- Baris Fitur Pengguna ---
        ["Cek Paket Saya", "Beli Paket XUT"],
        ["Beli Paket by Family", "/topup"],
        # --- Baris Fitur Admin ---
        ["Top Up Saldo User", "Cek Data User"],
        ["Broadcast Pesan", "/logout"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)