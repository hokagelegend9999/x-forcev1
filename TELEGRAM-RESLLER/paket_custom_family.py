# paket_custom_family.py

from api_request import get_family, purchase_package, get_package

def get_packages_by_family_data(api_key: str, tokens: dict, family_code: str) -> tuple:
    """Mengambil data paket dan menyiapkannya, juga mengembalikan token baru jika ada."""
    
    # Perbaikan: Terima DUA nilai dari get_family
    data, new_tokens = get_family(api_key, tokens, family_code)
    
    if not data:
        return None, "Gagal memuat data family. Pastikan family code benar.", new_tokens

    package_variants = data.get("package_variants")
    if not package_variants:
        return None, f"Tidak ada paket yang ditemukan untuk family code `{family_code}`.", new_tokens

    packages = []
    response_text = f"📦 **Paket Tersedia untuk Family: {data['package_family']['name']}** 📦\n\n"
    
    option_number = 1
    variant_number = 1
    
    for variant in package_variants:
        variant_name = variant["name"]
        response_text += f"**Varian {variant_number}: {variant_name}**\n"
        for option in variant["package_options"]:
            packages.append({
                "number": option_number,
                "name": option["name"],
                "price": option["price"],
                "code": option["package_option_code"]
            })
            response_text += f"`{option_number}`. {option['name']} - Rp {option['price']:,}\n"
            option_number += 1
        variant_number += 1
        response_text += "\n"

    response_text += "Ketik nomor paket yang ingin Anda beli, atau kirim /cancel untuk batal."
    
    # Perbaikan: Kembalikan TIGA nilai (termasuk token baru)
    return packages, response_text, new_tokens

# Di dalam paket_custom_family.py

def get_package_details_as_string(api_key: str, tokens: dict, package_code: str) -> tuple[dict, dict]:
    """
    Mengambil detail paket dan mengembalikannya sebagai dictionary yang berisi
    bagian-bagian pesan dan token baru.
    """
    package, new_tokens = get_package(api_key, tokens, package_code)
    
    if not package:
        # Kembalikan dictionary dengan pesan error
        return {"error": "Gagal memuat detail paket."}, new_tokens

    name1 = package.get("package_family", {}).get("name", "")
    name2 = package.get("package_detail_variant", {}).get("name", "")
    name3 = package.get("package_option", {}).get("name", "")
    title = f"{name1} {name2} {name3}".strip()
    
    price = package["package_option"]["price"]
    detail = package["package_option"]["tnc"]
    # Bersihkan teks T&C
    tnc_text = detail.replace("<p>", "").replace("</p>", "").replace("<strong>", "").replace("</strong>", "").replace("<br>", "\n").replace("<br />", "").strip()

    # Buat pesan utama
    main_details_text = (
        f"**Detail Paket**\n"
        f"Nama: {title}\n"
        f"Harga: Rp {price:,}\n\n"
        f"Ketik **YA** untuk konfirmasi pembelian, atau /cancel untuk batal."
    )
    
    # Kembalikan dictionary berisi dua bagian pesan dan token baru
    return {
        "main_details": main_details_text,
        "tnc": tnc_text
    }, new_tokens