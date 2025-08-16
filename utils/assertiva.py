import os, time, base64, requests
from dotenv import load_dotenv
from typing import Optional
import streamlit as st


load_dotenv()

ASSERTIVA_CLIENT_ID  = st.secrets["assertiva"]["ASSERTIVA_CLIENT_ID"]
ASSERTIVA_SECRET     = st.secrets["assertiva"]["ASSERTIVA_SECRET"]
AUTH_URL             = "https://api.assertivasolucoes.com.br/oauth2/v3/token"
PRODUCT_BASE         = "https://api.assertivasolucoes.com.br"         # raiz dos produtos
LOCALIZE_PHONE_PATH  = "/localize/v3/pessoas/telefone"                # ajuste p/ seu contrato


_token_cache: dict = {"access_token": None, "exp": 0}


def _get_access_token() -> str:
    if _token_cache["access_token"] and _token_cache["exp"] > time.time():
        return _token_cache["access_token"]
    basic = base64.b64encode(f"{ASSERTIVA_CLIENT_ID}:{ASSERTIVA_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}",
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    _token_cache["access_token"] = payload["access_token"]
    _token_cache["exp"]          = time.time() + payload.get("expires_in", 50)
    return _token_cache["access_token"]


def get_latest_phone_by_name(full_name: str) -> Optional[str]:
    token = _get_access_token()
    url   = f"{PRODUCT_BASE}{LOCALIZE_PHONE_PATH}"
    params = {"nome": full_name, "limite": 1, "ordenarPor": "dataAtualizacaoDesc"}  # ajuste
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/json",
               "Cache-Control": "no-cache"}   # evita cache de CDN
    r = requests.get(url, headers=headers, params=params, timeout=15)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    dados = r.json()    # ← estrutura depende do produto
    if not dados or "telefones" not in dados[0]:
        return None
    return dados[0]["telefones"][0]["numero"]


def check_assertiva_access() -> tuple[bool, str]:
    try:
        _get_access_token()
    except:
        return False, 'Sem permissão para acessar a Assertiva neste horário.'
    else:
        return True, 'Acesso permitido.'