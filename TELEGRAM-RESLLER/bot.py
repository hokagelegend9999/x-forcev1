# bot.py - VERSI FINAL LENGKAP

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Impor konfigurasi dan semua handler yang kita buat
import config
from session_manager import load_sessions

from user_handlers import (
    start, logout, user_menu_handler,
    login_conversation, family_purchase_conversation,
    xut_purchase_conversation, topup_conversation
)
from admin_handlers import (
    admin_panel, topup_user_conversation, placeholder_handler
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Fungsi utama untuk menjalankan bot."""
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()
    
    # Muat sesi dari file saat bot dimulai
    application.bot_data['user_sessions'] = load_sessions()

    # --- DAFTARKAN HANDLER PENGGUNA ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("topup", topup_conversation.entry_points[0].callback)) # Agar /topup langsung berfungsi
    
    # Daftarkan semua alur percakapan pengguna
    application.add_handler(login_conversation)
    application.add_handler(family_purchase_conversation)
    application.add_handler(xut_purchase_conversation)
    application.add_handler(topup_conversation)

    # --- DAFTARKAN HANDLER ADMIN ---
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Daftarkan alur percakapan untuk top up oleh admin
    application.add_handler(topup_user_conversation)
    
    # Daftarkan handler untuk tombol admin lainnya sebagai placeholder
    admin_other_buttons = ["Cek Data User", "Broadcast Pesan", "Kembali ke Menu User"]
    application.add_handler(MessageHandler(filters.Text(admin_other_buttons), placeholder_handler))

    # --- DAFTARKAN HANDLER UNTUK TOMBOL MENU UTAMA PENGGUNA ---
    user_menu_choices = ["Cek Paket Saya", "Beli Paket XUT", "Beli Paket by Family"]
    application.add_handler(MessageHandler(filters.Text(user_menu_choices), user_menu_handler))
    
    # Mulai Bot
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == '__main__':
    main()