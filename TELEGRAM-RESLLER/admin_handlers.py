# admin_handlers.py

from functools import wraps
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from keyboards import get_admin_menu_keyboard, get_main_menu_keyboard
from session_manager import save_sessions, load_sessions

# Definisikan state untuk alur top up
ASK_USER_ID, ASK_TOPUP_AMOUNT, CONFIRM_TOPUP = range(10, 13)

# --- Decorator (tidak berubah) ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("Maaf, Anda tidak memiliki akses ke perintah ini.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- Handler Utama Admin ---
@admin_only
async def admin_panel(update: Update, context: CallbackContext) -> None:
    """Menampilkan panel admin."""
    await update.message.reply_text(
        "Selamat datang di Panel Admin. Pilih salah satu opsi di bawah.",
        reply_markup=get_admin_menu_keyboard()
    )

# --- Alur Percakapan Top Up ---
@admin_only
async def topup_user_start(update: Update, context: CallbackContext) -> int:
    """Memulai alur top up saldo pengguna."""
    await update.message.reply_text(
        "Masukkan ID Telegram pengguna yang ingin di-top up. Kirim /cancel untuk batal.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_USER_ID

@admin_only
async def handle_user_id(update: Update, context: CallbackContext) -> int:
    """Menangani input ID pengguna dan meminta jumlah top up."""
    target_user_id = update.message.text
    if not target_user_id.isdigit():
        await update.message.reply_text("ID tidak valid. Harap masukkan angka saja.")
        return ASK_USER_ID

    # Cek apakah user ada di database sesi
    user_sessions = load_sessions()
    if int(target_user_id) not in user_sessions:
        await update.message.reply_text("ID Pengguna tidak ditemukan di sistem. Pastikan pengguna pernah berinteraksi dengan bot.")
        return ASK_USER_ID

    context.user_data['target_user_id'] = int(target_user_id)
    await update.message.reply_text("ID ditemukan. Sekarang masukkan jumlah saldo yang ingin ditambahkan (contoh: 50000).")
    return ASK_TOPUP_AMOUNT

@admin_only
async def handle_topup_amount(update: Update, context: CallbackContext) -> int:
    """Menangani jumlah top up dan meminta konfirmasi."""
    amount_text = update.message.text
    if not amount_text.isdigit() or int(amount_text) <= 0:
        await update.message.reply_text("Jumlah tidak valid. Harap masukkan angka positif.")
        return ASK_TOPUP_AMOUNT

    context.user_data['topup_amount'] = int(amount_text)
    target_user_id = context.user_data['target_user_id']
    
    await update.message.reply_text(
        f"KONFIRMASI:\n"
        f"Anda akan menambahkan saldo sebesar *Rp {int(amount_text):,}* "
        f"ke pengguna dengan ID `{target_user_id}`.\n\n"
        f"Ketik *YA* untuk melanjutkan, atau /cancel untuk batal.",
        parse_mode='Markdown'
    )
    return CONFIRM_TOPUP

@admin_only
async def handle_topup_confirmation(update: Update, context: CallbackContext) -> int:
    """Mengonfirmasi, mengeksekusi top up, dan memberi notifikasi."""
    if update.message.text.lower() != 'ya':
        await update.message.reply_text("Top up dibatalkan.", reply_markup=get_admin_menu_keyboard())
        return ConversationHandler.END

    target_user_id = context.user_data['target_user_id']
    amount = context.user_data['topup_amount']
    
    # Langsung manipulasi data dari bot_data
    user_sessions = context.bot_data.get('user_sessions', {})
    
    if target_user_id not in user_sessions:
         await update.message.reply_text("Error: Sesi pengguna target tidak ditemukan saat konfirmasi.")
         return ConversationHandler.END

    # Tambahkan saldo
    user_sessions[target_user_id]['bot_balance'] = user_sessions[target_user_id].get('bot_balance', 0) + amount
    save_sessions(context) # Simpan perubahan ke file
    
    await update.message.reply_text(
        f"✅ Berhasil! Saldo sebesar Rp {amount:,} telah ditambahkan ke pengguna `{target_user_id}`.",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode='Markdown'
    )

    # Kirim notifikasi ke pengguna yang di-top up
    try:
        user_phone = user_sessions[target_user_id].get('phone_number', 'N/A')
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"🎉 Selamat! Saldo bot Anda telah di-top up sebesar *Rp {amount:,}* oleh admin.\n"
                 f"Saldo Anda sekarang: *Rp {user_sessions[target_user_id]['bot_balance']:,}*",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Gagal mengirim notifikasi top up ke {target_user_id}: {e}")
        await update.message.reply_text(f"Info: Gagal mengirim notifikasi ke pengguna.")
        
    return ConversationHandler.END

# --- Handler untuk tombol lain (placeholder) ---
@admin_only
async def placeholder_handler(update: Update, context: CallbackContext) -> None:
    """Handler sementara untuk fitur yang belum dibuat."""
    await update.message.reply_text(f"Fitur '{update.message.text}' sedang dalam pengembangan.", reply_markup=get_admin_menu_keyboard())

# --- Gabungkan menjadi ConversationHandler ---
topup_user_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Text(["Top Up Saldo User"]), topup_user_start)],
    states={
        ASK_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id)],
        ASK_TOPUP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topup_amount)],
        CONFIRM_TOPUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topup_confirmation)],
    },
    fallbacks=[CommandHandler('cancel', admin_panel)], # Kembali ke menu admin jika cancel
)