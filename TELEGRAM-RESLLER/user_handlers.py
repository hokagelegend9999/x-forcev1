# user_handlers.py - VERSI FINAL LENGKAP

import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)
import config
from session_manager import save_sessions
from keyboards import get_main_menu_keyboard

# --- Impor Fungsi Logika ---
from api_request import request_otp, verify_otp, purchase_package
from my_package import fetch_my_packages_as_string
from paket_xut import get_package_xut_data
from paket_custom_family import get_packages_by_family_data, get_package_details_as_string
from atlantic_api import get_deposit_methods, create_deposit_request

# =============================================================================
# DEFINISI STATE UNTUK SEMUA CONVERSATION HANDLER
# =============================================================================
# Alur Login
ASK_PHONE, ASK_OTP = range(2)
# Alur Beli Paket Family
ASK_FAMILY_CODE, CHOOSE_FAMILY_PACKAGE, CONFIRM_FAMILY_PURCHASE = range(2, 5)
# Alur Beli Paket XUT
CHOOSE_XUT_PACKAGE, CONFIRM_XUT_PURCHASE = range(5, 7)
# Alur Top Up
CHOOSE_TOPUP_METHOD, ENTER_TOPUP_AMOUNT = range(7, 9)

# =============================================================================
# HANDLER UTAMA & LOGIN
# =============================================================================

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_sessions = context.bot_data.get('user_sessions', {})

    if chat_id in user_sessions and user_sessions[chat_id].get("is_logged_in"):
        user_data = user_sessions[chat_id]
        phone = user_data.get("phone_number")
        bot_balance = user_data.get("bot_balance", 0)
        await update.message.reply_text(
            f"👋 Halo *{user.first_name}*!\n\n"
            f"📞 Nomor Terhubung: `{phone}`\n"
            f"💰 Saldo Bot Anda: *Rp {bot_balance:,.0f}*\n\n"
            f"Selamat bertransaksi kembali! ✨",
            parse_mode='Markdown',
            reply_markup=get_main_menu_keyboard()
        )
    else:
        welcome_message = (
            f"🎉 Selamat Datang, *{user.first_name}*!\n\n"
            f"🆔 ID Telegram Anda: `{user.id}`\n\n"
            "Untuk membuka semua fitur, Anda perlu menghubungkan akun ini dengan nomor telepon Anda.\n\n"
            "✨ *Silakan klik tombol di bawah untuk memulai proses login*."
        )
        keyboard = [[InlineKeyboardButton("🔐 LOGIN DENGAN OTP 🔐", callback_data="start_login")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        photos = await user.get_profile_photos(limit=1)
        if photos and photos.photos:
            await context.bot.send_photo(
                chat_id=chat_id, photo=photos.photos[0][0].file_id, 
                caption=welcome_message, parse_mode='Markdown', reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                welcome_message, parse_mode='Markdown', reply_markup=reply_markup
            )

async def login_start(update: Update, context: CallbackContext) -> int:
    message_text = "Silakan masukkan nomor HP Anda (contoh: 081234567890). Kirim /cancel untuk batal."
    if update.callback_query:
        await update.callback_query.message.reply_text(message_text, reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text(message_text, reply_markup=ReplyKeyboardRemove())
    return ASK_PHONE

async def ask_phone_handler(update: Update, context: CallbackContext) -> int:
    phone_number = update.message.text.strip()
    if phone_number.startswith("08"):
        phone_number = "62" + phone_number[1:]
        await update.message.reply_text(f"Format nomor diubah menjadi: {phone_number}")
    context.user_data['phone_number'] = phone_number
    await update.message.reply_text(f"Mengirim kode OTP ke {phone_number}...")
    subscriber_id = request_otp(phone_number)
    if subscriber_id:
        await update.message.reply_text("Kode OTP terkirim. Silakan masukkan kodenya.")
        return ASK_OTP
    else:
        await update.message.reply_text("Gagal mengirim OTP. Coba lagi dengan /login.")
        return ConversationHandler.END

async def ask_otp_handler(update: Update, context: CallbackContext) -> int:
    otp_code = update.message.text
    phone_number = context.user_data.get('phone_number')
    chat_id = update.effective_chat.id
    user_sessions = context.bot_data.get('user_sessions', {})
    await update.message.reply_text("Memverifikasi kode OTP...")
    login_data = verify_otp(phone_number, otp_code)
    if login_data and not login_data.get("error"):
        existing_data = user_sessions.get(chat_id)
        current_bot_balance = existing_data.get('bot_balance', 0) if existing_data else 0
        formatted_user_data = {
            "is_logged_in": True, "phone_number": phone_number,
            "bot_balance": current_bot_balance, "tokens": login_data
        }
        user_sessions[chat_id] = formatted_user_data
        context.bot_data['user_sessions'] = user_sessions
        save_sessions(context)
        await update.message.reply_text("✅ Login berhasil!", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ OTP salah atau terjadi error. Silakan /login lagi.")
        return ConversationHandler.END

async def login_button_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    return await login_start(update, context)

# =============================================================================
# HANDLER MENU & UTILITAS
# =============================================================================

async def user_menu_handler(update: Update, context: CallbackContext) -> None:
    choice = update.message.text
    chat_id = update.effective_chat.id
    user_sessions = context.bot_data.get('user_sessions', {})
    if not (chat_id in user_sessions and user_sessions[chat_id].get("is_logged_in")):
        await update.message.reply_text("Sesi Anda tidak valid. Silakan /login ulang.")
        return
    user_data = user_sessions[chat_id]
    if choice == "Cek Paket Saya":
        await update.message.reply_text("⏳ Mohon tunggu...")
        original_tokens = user_data.get("tokens")
        packages_info_string, new_tokens = fetch_my_packages_as_string(config.CRYPTO_API_KEY, original_tokens)
        if new_tokens and new_tokens.get("id_token") != original_tokens.get("id_token"):
            user_data['tokens'] = new_tokens
            save_sessions(context)
            logging.info(f"Token untuk user {chat_id} telah diperbarui.")
            await update.message.reply_text("💡 Info: Sesi Anda telah diperbarui secara otomatis.")
        await update.message.reply_text(packages_info_string, parse_mode='Markdown')

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('Proses dibatalkan.', reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def logout(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    user_sessions = context.bot_data.get('user_sessions', {})
    if chat_id in user_sessions:
        del user_sessions[chat_id]
        save_sessions(context)
    await update.message.reply_text("Anda telah logout.", reply_markup=ReplyKeyboardRemove())

# =============================================================================
# ALUR PERCAKAPAN: BELI PAKET BY FAMILY
# =============================================================================

async def family_purchase_start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Silakan masukkan Kode Family Paket (contoh: XTRACOMBO_PLUS). Kirim /cancel untuk batal.")
    return ASK_FAMILY_CODE

async def ask_family_code_handler(update: Update, context: CallbackContext) -> int:
    family_code = update.message.text
    chat_id = update.effective_chat.id
    user_data = context.bot_data['user_sessions'][chat_id]
    await update.message.reply_text(f"Mencari paket untuk family code: `{family_code}`...", parse_mode='Markdown')
    packages, response_text, new_tokens = get_packages_by_family_data(config.CRYPTO_API_KEY, user_data['tokens'], family_code)
    if new_tokens and new_tokens.get("id_token") != user_data['tokens'].get("id_token"):
        user_data['tokens'] = new_tokens
        save_sessions(context)
        await update.message.reply_text("💡 Info: Sesi Anda telah diperbarui secara otomatis.")
    if packages is None:
        await update.message.reply_text(response_text, parse_mode='Markdown')
        return ConversationHandler.END
    context.user_data['family_packages'] = packages
    await update.message.reply_text(response_text, parse_mode='Markdown')
    return CHOOSE_FAMILY_PACKAGE

async def choose_family_package_handler(update: Update, context: CallbackContext) -> int:
    choice = update.message.text
    if not choice.isdigit():
        await update.message.reply_text("Pilihan tidak valid. Harap masukkan nomor paket.")
        return CHOOSE_FAMILY_PACKAGE
    packages = context.user_data.get('family_packages', [])
    selected_pkg = next((p for p in packages if p["number"] == int(choice)), None)
    if not selected_pkg:
        await update.message.reply_text("Nomor paket tidak ditemukan. Silakan pilih nomor yang benar.")
        return CHOOSE_FAMILY_PACKAGE
    context.user_data.update({'selected_package_code': selected_pkg['code'], 'selected_package_price': selected_pkg['price']})
    chat_id = update.effective_chat.id
    user_data = context.bot_data['user_sessions'][chat_id]
    await update.message.reply_text("Mengambil detail paket...")
    details_dict, new_tokens = get_package_details_as_string(config.CRYPTO_API_KEY, user_data['tokens'], selected_pkg['code'])
    if new_tokens and new_tokens.get("id_token") != user_data['tokens'].get("id_token"):
        user_data['tokens'] = new_tokens
        save_sessions(context)
        await update.message.reply_text("💡 Info: Sesi Anda telah diperbarui secara otomatis.")
    if "tnc" in details_dict and details_dict["tnc"]:
        await update.message.reply_text(f"📜 **Terms & Conditions** 📜\n\n{details_dict['tnc']}", parse_mode='Markdown')
    await update.message.reply_text(details_dict["main_details"], parse_mode='Markdown')
    return CONFIRM_FAMILY_PURCHASE

async def confirm_purchase_handler(update: Update, context: CallbackContext, fee_logic: bool) -> int:
    """Fungsi generik untuk konfirmasi pembelian (Family & XUT)."""
    if update.message.text.lower() != 'ya':
        await update.message.reply_text("Pembelian dibatalkan.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    package_code = context.user_data.get('selected_package_code')
    package_price = context.user_data.get('selected_package_price', 0)
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    user_data = context.bot_data['user_sessions'][chat_id]

    TRANSACTION_FEE = 2000 if fee_logic and user_id not in config.ADMIN_IDS else 0
    if user_data['bot_balance'] < TRANSACTION_FEE:
        await update.message.reply_text(f"❌ Saldo bot Anda tidak mencukupi. Butuh Rp {TRANSACTION_FEE:,.0f}, saldo Anda Rp {user_data['bot_balance']:,.0f}.")
        return ConversationHandler.END

    await update.message.reply_text("Memproses pembelian, mohon tunggu...")
    result, new_tokens = purchase_package(config.CRYPTO_API_KEY, user_data['tokens'], package_code)
    if new_tokens and new_tokens.get("id_token") != user_data['tokens'].get("id_token"):
        user_data['tokens'] = new_tokens
        save_sessions(context)

    if result and result.get('status') == 'SUCCESS':
        user_data['bot_balance'] -= TRANSACTION_FEE
        save_sessions(context)
        success_message = "✅ Pembelian berhasil!"
        if TRANSACTION_FEE > 0:
            success_message += f"\nBiaya admin Rp {TRANSACTION_FEE:,.0f} telah dipotong dari saldo bot Anda."
        await update.message.reply_text(success_message, reply_markup=get_main_menu_keyboard())
    else:
        error_msg = result.get('message', 'Terjadi kesalahan.') if result else 'Terjadi kesalahan.'
        await update.message.reply_text(f"❌ Gagal membeli paket: {error_msg}", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def confirm_family_purchase_handler(update: Update, context: CallbackContext) -> int:
    return await confirm_purchase_handler(update, context, fee_logic=True)

# =============================================================================
# ALUR PERCAKAPAN: BELI PAKET XUT
# =============================================================================

async def xut_purchase_start(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id
    user_data = context.bot_data['user_sessions'][chat_id]
    await update.message.reply_text("⏳ Mencari paket Xtra Unlimited Turbo...")
    packages, response_text, new_tokens = get_package_xut_data(config.CRYPTO_API_KEY, user_data['tokens'])
    if new_tokens and new_tokens.get("id_token") != user_data['tokens'].get("id_token"):
        user_data['tokens'] = new_tokens
        save_sessions(context)
        await update.message.reply_text("💡 Info: Sesi Anda telah diperbarui secara otomatis.")
    if packages is None:
        await update.message.reply_text(response_text)
        return ConversationHandler.END
    context.user_data['xut_packages'] = packages
    await update.message.reply_text(response_text, parse_mode='Markdown')
    return CHOOSE_XUT_PACKAGE

async def choose_xut_package_handler(update: Update, context: CallbackContext) -> int:
    choice = update.message.text
    if not choice.isdigit():
        await update.message.reply_text("Pilihan tidak valid. Harap masukkan nomor paket.")
        return CHOOSE_XUT_PACKAGE
    packages = context.user_data.get('xut_packages', [])
    selected_pkg = next((p for p in packages if p["number"] == int(choice)), None)
    if not selected_pkg:
        await update.message.reply_text("Nomor paket tidak ditemukan. Silakan pilih nomor yang benar.")
        return CHOOSE_XUT_PACKAGE
    context.user_data.update({'selected_package_code': selected_pkg['code'], 'selected_package_price': selected_pkg['price']})
    chat_id = update.effective_chat.id
    user_data = context.bot_data['user_sessions'][chat_id]
    await update.message.reply_text("Mengambil detail paket...")
    details_dict, new_tokens = get_package_details_as_string(config.CRYPTO_API_KEY, user_data['tokens'], selected_pkg['code'])
    if new_tokens and new_tokens.get("id_token") != user_data['tokens'].get("id_token"):
        user_data['tokens'] = new_tokens
        save_sessions(context)
        await update.message.reply_text("💡 Info: Sesi Anda telah diperbarui secara otomatis.")
    if "tnc" in details_dict and details_dict["tnc"]:
        await update.message.reply_text(f"📜 **Terms & Conditions** 📜\n\n{details_dict['tnc']}", parse_mode='Markdown')
    await update.message.reply_text(details_dict["main_details"], parse_mode='Markdown')
    return CONFIRM_XUT_PURCHASE

async def confirm_xut_purchase_handler(update: Update, context: CallbackContext) -> int:
    return await confirm_purchase_handler(update, context, fee_logic=True)

# =============================================================================
# ALUR PERCAKAPAN: TOP UP SALDO (VERSI FINAL DENGAN TOMBOL INLINE)
# =============================================================================

def format_payment_instructions(data: dict, method_type: str) -> str:
    """Memformat data respon dari API menjadi pesan yang mudah dibaca."""
    try:
        get_balance = data.get('get_balance', 0)
        nominal = data.get('nominal', 0)
        fee = data.get('fee', 0)
        expired_at = data.get('expired_at', 'N/A')
        base_info = (
            f"Jumlah: *Rp {nominal:,}*\n"
            f"Biaya Admin: *Rp {fee:,}*\n"
            f"Saldo Diterima: *Rp {get_balance:,}*\n"
            f"Berlaku hingga: *{expired_at}*\n"
        )
        if method_type == 'ewallet' and 'qr_image' in data:
            return f"✅ *Top Up QRIS Berhasil!*\n\n{base_info}\nLink QR: {data['qr_image']}"
        elif method_type == 'bank':
            return (f"✅ *Top Up Bank Berhasil!*\n\nBank: *{data['bank']}*\n"
                    f"No. Rek: `{data['tujuan']}`\nAtas Nama: *{data['atas_nama']}*\n\n"
                    f"Jumlah Transfer (HARUS PAS): *Rp {nominal:,}*")
        elif method_type == 'va':
            return f"✅ *Top Up VA Berhasil!*\n\nBank: *{data['bank']}*\nNomor VA: `{data['nomor_va']}`\n\n{base_info}"
        elif method_type == 'ewallet' and 'url' in data:
            return f"✅ *Top Up E-Wallet Berhasil!*\n\n{base_info}\nSelesaikan di: {data['url']}"
    except KeyError as e:
        return f"Error memformat instruksi: {e}"
    return "Gagal memproses instruksi."

# Di dalam user_handlers.py

async def topup_start(update: Update, context: CallbackContext) -> int:
    """Memulai alur topup, menampilkan daftar metode dengan tombol inline."""
    message = update.effective_message
    await message.reply_text("⏳ Mencari metode top up yang tersedia...", reply_markup=ReplyKeyboardRemove())
    methods = get_deposit_methods()
    
    if not methods:
        await message.reply_text("Gagal mengambil metode top up saat ini. Coba lagi nanti.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    context.user_data['deposit_methods'] = methods
    
    keyboard = []
    # Buat tombol untuk setiap metode yang aktif
    for index, method in enumerate(methods):
        button_text = f"{method.get('name')} (Min: Rp {int(method.get('min',0)):,})"
        callback_data = f"topup_{index}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("❌ Batal", callback_data="topup_cancel")])
    
    await message.reply_text(
        "✨ Silakan pilih metode pembayaran:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_TOPUP_METHOD

# Di dalam user_handlers.py

async def choose_topup_method_handler(update: Update, context: CallbackContext) -> int:
    """Menangani pilihan metode dari tombol inline."""
    query = update.callback_query
    await query.answer()

    if query.data == 'topup_cancel':
        await query.edit_message_text("Top up dibatalkan.")
        # Kirim pesan baru untuk menampilkan menu utama lagi
        await query.message.reply_text("Anda kembali ke menu utama.", reply_markup=get_main_menu_keyboard())
        return ConversationHandler.END

    choice_index = int(query.data.split('_')[1])
    selected_method = context.user_data['deposit_methods'][choice_index]
    context.user_data['selected_method'] = selected_method
    
    min_amount, max_amount = int(selected_method.get('min', 0)), int(selected_method.get('max', 0))
    
    # Edit pesan yang ada, ganti dengan pertanyaan baru
    await query.edit_message_text(
        text=f"Anda memilih *{selected_method['name']}*.\n"
             f"Silakan masukkan jumlah top up (antara Rp {min_amount:,} dan Rp {max_amount:,}).\n\n"
             "Atau kirim /cancel untuk batal.",
        parse_mode='Markdown'
    )
    return ENTER_TOPUP_AMOUNT

async def enter_topup_amount_handler(update: Update, context: CallbackContext) -> int:
    """Menangani input jumlah dan membuat request API."""
    amount_text = update.message.text
    selected_method = context.user_data.get('selected_method')
    min_amount, max_amount = int(selected_method.get('min', 0)), int(selected_method.get('max', 0))
    
    if not amount_text.isdigit() or not (min_amount <= int(amount_text) <= max_amount):
        await update.message.reply_text(f"Jumlah harus angka antara Rp {min_amount:,} dan Rp {max_amount:,}.")
        return ENTER_TOPUP_AMOUNT
        
    await update.message.reply_text("⏳ Membuat permintaan deposit...")
    result = create_deposit_request(
        chat_id=update.effective_chat.id, method=selected_method['metode'],
        type=selected_method['type'], amount=int(amount_text)
    )
    if result and "error" not in result:
        instructions = format_payment_instructions(result, selected_method['type'])
        await update.message.reply_text(instructions, parse_mode='Markdown', reply_markup=get_main_menu_keyboard())
    else:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {result.get('error', 'Gagal membuat permintaan.')}", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

# Daftarkan ConversationHandler untuk Top Up
# Di dalam user_handlers.py

topup_conversation = ConversationHandler(
    entry_points=[CommandHandler('topup', topup_start)],
    states={
        # State ini sekarang menangani KLIK TOMBOL, bukan TEKS
        CHOOSE_TOPUP_METHOD: [
            CallbackQueryHandler(choose_topup_method_handler, pattern='^topup_cancel$'),
            CallbackQueryHandler(choose_topup_method_handler, pattern='^topup_')
        ],
        ENTER_TOPUP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_topup_amount_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('logout', logout)],
)
# Di dalam user_handlers.py (letakkan di paling bawah)

# =============================================================================
# PENDAFTARAN SEMUA CONVERSATION HANDLER
# =============================================================================

login_conversation = ConversationHandler(
    entry_points=[CommandHandler('login', login_start), CallbackQueryHandler(login_button_callback, pattern='^start_login$')],
    states={
        ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone_handler)],
        ASK_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_otp_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('logout', logout)],
)

family_purchase_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Text(["Beli Paket by Family"]), family_purchase_start)],
    states={
        ASK_FAMILY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_family_code_handler)],
        CHOOSE_FAMILY_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_family_package_handler)],
        CONFIRM_FAMILY_PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_family_purchase_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('logout', logout)],
)

xut_purchase_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.Text(["Beli Paket XUT"]), xut_purchase_start)],
    states={
        CHOOSE_XUT_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_xut_package_handler)],
        CONFIRM_XUT_PURCHASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_xut_purchase_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('logout', logout)],
)

topup_conversation = ConversationHandler(
    entry_points=[CommandHandler('topup', topup_start)],
    states={
        CHOOSE_TOPUP_METHOD: [
            CallbackQueryHandler(choose_topup_method_handler, pattern='^topup_cancel$'),
            CallbackQueryHandler(choose_topup_method_handler, pattern='^topup_')
        ],
        ENTER_TOPUP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_topup_amount_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel), CommandHandler('logout', logout)],
)