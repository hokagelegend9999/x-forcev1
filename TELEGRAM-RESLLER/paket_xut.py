# paket_xut.py

from api_request import get_family

PACKAGE_FAMILY_CODE = "08a3b1e6-8e78-4e45-a540-b40f06871cfe" # Kode untuk XUT

def get_package_xut_data(api_key: str, tokens: dict):
    """Mengambil data paket XUT dan menyiapkannya untuk ditampilkan."""
    data, new_tokens = get_family(api_key, tokens, PACKAGE_FAMILY_CODE)
    if not data or "package_variants" not in data:
        return None, "Gagal memuat data paket XUT saat ini.", new_tokens

    packages = []
    response_text = "📦 **Paket Xtra Unlimited Turbo Tersedia** 📦\n\n"
    start_number = 1
    
    for variant in data["package_variants"]:
        for option in variant["package_options"]:
            friendly_name = option["name"]
            
            # Mengubah nama agar lebih mudah dibaca
            if friendly_name.lower() == "basic":
                friendly_name = "Xtra Combo Unli Turbo Basic"
            elif friendly_name.lower() == "vidio":
                friendly_name = "Unli Turbo Vidio 30 Hari"
            elif friendly_name.lower() == "iflix":
                friendly_name = "Unli Turbo Iflix 30 Hari"
            
            packages.append({
                "number": start_number,
                "name": friendly_name,
                "price": option["price"],
                "code": option["package_option_code"]
            })
            response_text += f"`{start_number}`. {friendly_name} - Rp {option['price']:,}\n"
            start_number += 1

    response_text += "\nKetik nomor paket yang ingin Anda beli, atau kirim /cancel untuk batal."
    return packages, response_text, new_tokens