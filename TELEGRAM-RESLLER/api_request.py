# api_request.py - VERSI FINAL LENGKAP

import json
import uuid
import requests
import time
import logging
from datetime import datetime, timezone, timedelta

import config
from crypto_helper import encryptsign_xdata, java_like_timestamp, ts_gmt7_without_colon, ax_api_signature, decrypt_xdata, make_x_signature_payment, build_encrypted_field

BASE_URL = "https://api.myxl.xlaxiata.co.id"

# =============================================================================
# FUNGSI-FUNGSI AUTENTIKASI DASAR
# =============================================================================

def validate_contact(contact: str) -> bool:
    """Memvalidasi format nomor HP."""
    if not contact.startswith("628") or len(contact) > 14:
        return False
    return True

def request_otp(contact: str) -> str:
    """Meminta OTP dari server XL."""
    if not validate_contact(contact): return None
    url = "https://gede.ciam.xlaxiata.co.id/realms/xl-ciam/auth/otp"
    querystring = {"contact": contact, "contactType": "SMS", "alternateContact": "false"}
    now = datetime.now(timezone(timedelta(hours=7)))
    headers = {
        "Authorization": "Basic OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z",
        "Ax-Device-Id": "92fb44c0804233eb4d9e29f838223a14",
        "Ax-Fingerprint": "YmQLy9ZiLLBFAEVcI4Dnw9+NJWZcdGoQyewxMF/9hbfk/8GbKBgtZxqdiiam8+m2lK31E/zJQ7kjuPXpB3EE8naYL0Q8+0WLhFV1WAPl9Eg=",
        "Ax-Request-At": java_like_timestamp(now), "Ax-Request-Id": str(uuid.uuid4()),
        "User-Agent": "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13)",
        "Content-Type": "application/json", "Host": "gede.ciam.xlaxiata.co.id",
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        return response.json().get("subscriber_id")
    except requests.RequestException as e:
        logging.error(f"Error requesting OTP: {e}")
        return None

def verify_otp(contact: str, code: str) -> dict:
    """Memverifikasi OTP dan mendapatkan token awal."""
    if not (contact and code and len(code) == 6): return None
    url = "https://gede.ciam.xlaxiata.co.id/realms/xl-ciam/protocol/openid-connect/token"
    now_gmt7 = datetime.now(timezone(timedelta(hours=7)))
    signature = ax_api_signature(ts_gmt7_without_colon(now_gmt7), contact, code, "SMS")
    payload = f"contactType=SMS&code={code}&grant_type=password&contact={contact}&scope=openid"
    headers = {
        "Authorization": "Basic OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z",
        "Ax-Api-Signature": signature, "Ax-Device-Id": "92fb44c0804233eb4d9e29f838223a14",
        "Ax-Fingerprint": "YmQLy9ZiLLBFAEVcI4Dnw9+NJWZcdGoQyewxMF/9hbfk/8GbKBgtZxqdiiam8+m2lK31E/zJQ7kjuPXpB3EE8naYL0Q8+0WLhFV1WAPl9Eg=",
        "Ax-Request-At": ts_gmt7_without_colon(now_gmt7 - timedelta(minutes=5)),
        "Ax-Request-Id": str(uuid.uuid4()), "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13)",
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
        json_body = response.json()
        return None if "error" in json_body else json_body
    except requests.RequestException as e:
        logging.error(f"Error submitting OTP: {e}")
        return None

def get_new_token(refresh_token: str) -> dict:
    """Memperbarui token menggunakan refresh_token."""
    url = "https://gede.ciam.xlaxiata.co.id/realms/xl-ciam/protocol/openid-connect/token"
    headers = {
        "Host": "gede.ciam.xlaxiata.co.id", "ax-request-at": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0700",
        "ax-device-id": "92fb44c0804233eb4d9e29f838223a15", "ax-request-id": str(uuid.uuid4()),
        "authorization": "Basic OWZjOTdlZDEtNmEzMC00OGQ1LTk1MTYtNjBjNTNjZTNhMTM1OllEV21GNExKajlYSUt3UW56eTJlMmxiMHRKUWIyOW8z",
        "user-agent": "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13)",
        "content-type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    logging.info("Refreshing token...")
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=30)
        resp.raise_for_status()
        body = resp.json()
    except requests.RequestException as e:
        logging.error(f"Error saat request refresh token: {e}")
        return {"error": "Request failed", "error_description": str(e)}

    if "id_token" not in body:
        logging.error(f"Refresh token ditolak server: {body.get('error_description', body)}")
        return body
    
    logging.info("Token refreshed successfully.")
    return body

# =============================================================================
# LOGIKA INTI PERMINTAAN API DENGAN REFRESH TOKEN
# =============================================================================

def _internal_send_request(api_key, path, payload_dict, id_token, method):
    """Fungsi helper internal untuk melakukan request API terenkripsi."""
    try:
        encrypted_payload = encryptsign_xdata(api_key, method, path, id_token, payload_dict)
        xtime = int(encrypted_payload["encrypted_body"]["xtime"])
        body = encrypted_payload["encrypted_body"]
        x_sig = encrypted_payload["x_signature"]
        headers = {
            "host": "api.myxl.xlaxiata.co.id", "content-type": "application/json; charset=utf-8",
            "user-agent": "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13)",
            "x-api-key": config.CRYPTO_API_KEY, "authorization": f"Bearer {id_token}", "x-hv": "v3",
            "x-signature-time": str(xtime // 1000), "x-signature": x_sig, "x-request-id": str(uuid.uuid4()),
            "x-request-at": java_like_timestamp(datetime.now(timezone.utc).astimezone()), "x-version-app": "8.6.0",
        }
        url = f"{BASE_URL}/{path}"
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logging.error(f"Error di dalam _internal_send_request: {e}")
        return json.dumps({"status": "FAILED", "message": "Error saat request internal."})

def send_api_request(
    api_key: str, path: str, payload_dict: dict, tokens: dict, method: str = "POST"
) -> tuple[dict, dict]:
    """Mencoba request, merefresh token jika gagal, lalu mencoba lagi."""
    resp_text = _internal_send_request(api_key, path, payload_dict, tokens["id_token"], method)
    
    try:
        decrypted_body = decrypt_xdata(api_key, json.loads(resp_text))
        if decrypted_body and decrypted_body.get("status") == "SUCCESS":
            return decrypted_body, tokens
    except (json.JSONDecodeError, AttributeError, ValueError, TypeError):
        logging.warning("Gagal decrypt/parse respon awal, mencoba refresh token...")
        pass

    logging.info("Permintaan awal gagal atau token kedaluwarsa. Mencoba refresh token...")
    try:
        new_tokens = get_new_token(tokens["refresh_token"])
        if not new_tokens or "id_token" not in new_tokens:
            raise ValueError("Gagal mendapatkan token baru dari refresh token.")
        
        logging.info("Mencoba ulang permintaan dengan token baru...")
        resp_text_retry = _internal_send_request(api_key, path, payload_dict, new_tokens["id_token"], method)
        decrypted_body_retry = decrypt_xdata(api_key, json.loads(resp_text_retry))
        
        return decrypted_body_retry, new_tokens
        
    except Exception as e:
        logging.error(f"Gagal total setelah mencoba refresh token: {e}")
        return {"status": "FAILED", "message": f"Gagal total: {e}"}, tokens

# =============================================================================
# FUNGSI-FUNGSI SPESIFIK UNTUK ENDPOINT
# =============================================================================

def get_family(api_key: str, tokens: dict, family_code: str) -> tuple[dict, dict]:
    path = "api/v8/xl-stores/options/list"
    payload_dict = {"package_family_code": family_code, "lang": "en"}
    res, new_tokens = send_api_request(api_key, path, payload_dict, tokens, "POST")
    family_data = res.get("data") if res and res.get("status") == "SUCCESS" else None
    return family_data, new_tokens

def get_package(api_key: str, tokens: dict, package_option_code: str) -> tuple[dict, dict]:
    path = "api/v8/xl-stores/options/detail"
    raw_payload = {"package_option_code": package_option_code, "lang": "en"}
    res, new_tokens = send_api_request(api_key, path, raw_payload, tokens, "POST")
    package_data = res.get("data") if res and "data" in res else None
    return package_data, new_tokens

def purchase_package(api_key: str, tokens: dict, package_option_code: str) -> tuple[dict, dict]:
    package_details_data, new_tokens = get_package(api_key, tokens, package_option_code)
    if not package_details_data:
        return {"status": "FAILED", "message": "Gagal mendapatkan detail paket."}, new_tokens
    tokens = new_tokens

    token_confirmation = package_details_data.get("token_confirmation")
    payment_target = package_details_data.get("package_option", {}).get("package_option_code")
    price = package_details_data.get("package_option", {}).get("price")
    if not all([token_confirmation, payment_target, price is not None]):
        return {"status": "FAILED", "message": "Data detail paket tidak lengkap."}, tokens

    payment_path = "payments/api/v8/payment-methods-option"
    payment_payload = {
        "payment_type": "PURCHASE", "payment_target": payment_target,
        "lang": "en", "token_confirmation": token_confirmation
    }
    
    payment_res, new_tokens = send_api_request(api_key, payment_path, payment_payload, tokens, "POST")
    if not payment_res or payment_res.get("status") != "SUCCESS":
        return {"status": "FAILED", "message": "Gagal memulai pembayaran."}, new_tokens
    tokens = new_tokens

    token_payment = payment_res["data"]["token_payment"]
    ts_to_sign = payment_res["data"]["timestamp"]
    
    settlement_payload = {
        "total_amount": price, "payment_for": "BUY_PACKAGE", "payment_method": "BALANCE",
        "token_payment": token_payment, "access_token": tokens["access_token"],
        "timestamp": ts_to_sign,
        "items": [{"item_code": payment_target, "item_price": price}]
    }

    # Untuk settlement, kita perlu fungsi request khusus dengan signature berbeda.
    purchase_result_text = _internal_send_payment_request(api_key, settlement_payload, tokens, token_payment)
    try:
        purchase_result = decrypt_xdata(api_key, json.loads(purchase_result_text))
    except Exception as e:
        purchase_result = {"status": "FAILED", "message": "Gagal decrypt hasil akhir."}

    return purchase_result, tokens

def _internal_send_payment_request(api_key: str, payload_dict: dict, tokens: dict, token_payment: str):
    path = "payments/api/v8/settlement-balance"
    package_code = payload_dict["items"][0]["item_code"]
    access_token, id_token = tokens['access_token'], tokens['id_token']
    
    encrypted_payload = encryptsign_xdata(api_key, "POST", path, id_token, payload_dict)
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    ts_to_sign = payload_dict["timestamp"]
    x_sig_payment = make_x_signature_payment(access_token, ts_to_sign, package_code, token_payment)
    
    headers = {
        "host": "api.myxl.xlaxiata.co.id", "content-type": "application/json; charset=utf-8",
        "user-agent": "myXL / 8.6.0(1179); com.android.vending; (samsung; SM-N935F; SDK 33; Android 13)",
        "x-api-key": config.CRYPTO_API_KEY, "authorization": f"Bearer {id_token}", "x-hv": "v3",
        "x-signature-time": str(xtime // 1000), "x-signature": x_sig_payment,
        "x-request-id": str(uuid.uuid4()), "x-request-at": java_like_timestamp(datetime.fromtimestamp(xtime // 1000, tz=timezone.utc).astimezone()),
        "x-version-app": "8.6.0",
    }
    
    url = f"{BASE_URL}/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(encrypted_payload["encrypted_body"]), timeout=30)
    return resp.text