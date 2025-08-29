# my_package.py

# 1. Impor hanya fungsi yang dibutuhkan dari api_request
from api_request import get_package, send_api_request
# (Impor dari 'ui' sudah tidak diperlukan dan dihapus)

# 2. Ganti nama fungsi agar lebih deskriptif dan perbarui tipe return
def fetch_my_packages_as_string(api_key: str, tokens: dict) -> tuple[str, dict]:
    """
    Mengambil paket aktif pengguna, memformatnya sebagai string,
    dan mengembalikan string tersebut beserta token yang mungkin sudah diperbarui.
    """
    path = "api/v8/packages/quota-details"
    
    payload = {
        "is_enterprise": False,
        "lang": "en",
        "family_member_id": ""
    }
    
    # 3. Panggil send_api_request dengan cara baru (mengirim seluruh dict 'tokens')
    #    dan terima dua nilai balikan (hasil dan token baru).
    res, new_tokens = send_api_request(api_key, path, payload, tokens, "POST")
    
    if not res or res.get("status") != "SUCCESS":
        return "Gagal mengambil data paket Anda saat ini.", new_tokens
    
    quotas = res.get("data", {}).get("quotas", [])
    
    if not quotas:
        return "Anda tidak memiliki paket aktif saat ini.", new_tokens
    
    # 4. Siapkan sebuah string kosong untuk menampung semua output
    response_text = "📦 **Paket Aktif Anda** 📦\n"
    num = 1
    
    # Gunakan token yang mungkin sudah diperbarui untuk panggilan API selanjutnya
    current_tokens = new_tokens

    for quota in quotas:
        quota_code = quota.get("quota_code", "N/A")
        group_code = quota.get("group_code", "N/A")
        name = quota.get("name", "Tanpa Nama")
        family_code = "N/A"
        
        # 5. Panggil get_package dengan cara baru dan terima DUA nilai balikan
        package_details, updated_tokens_after_get_pkg = get_package(api_key, current_tokens, quota_code)
        
        # 6. PENTING: Perbarui token untuk iterasi loop selanjutnya jika ada perubahan
        if updated_tokens_after_get_pkg:
            current_tokens = updated_tokens_after_get_pkg

        if package_details and "package_family" in package_details:
            family_code = package_details["package_family"].get("package_family_code", "N/A")
        
        # 7. Tambahkan informasi ke dalam variabel string, bukan di-print
        response_text += f"\n===============================\n"
        response_text += f"**Paket #{num}**\n"
        response_text += f"**Nama**: {name}\n"
        response_text += f"**Kode Kuota**: `{quota_code}`\n"
        response_text += f"**Kode Family**: `{family_code}`\n"
        response_text += f"**Kode Grup**: `{group_code}`\n"
        
        num += 1
    
    response_text += "===============================\n"

    # 8. Hapus 'pause()' dan kembalikan (return) string dan token terakhir yang valid
    return response_text, current_tokens