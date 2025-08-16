from typing import Any, Dict, List, Optional, Tuple
import time, base64, requests
from typing import Optional
import datetime as dt
import streamlit as st
import requests
import time
import re


ASSERTIVA_CLIENT_ID  = st.secrets["assertiva"]["ASSERTIVA_CLIENT_ID"]
ASSERTIVA_SECRET     = st.secrets["assertiva"]["ASSERTIVA_SECRET"]
AUTH_URL             = "https://api.assertivasolucoes.com.br/oauth2/v3/token"
PRODUCT_BASE         = "https://api.assertivasolucoes.com.br"
LOCALIZE_PHONE_PATH  = "/localize/v3/mais-telefones"
PRODUCT_BASE = "https://api.assertivasolucoes.com.br"
ENDPOINT_CPF  = f"{PRODUCT_BASE}/localize/v3/cpf"
ENDPOINT_CNPJ = f"{PRODUCT_BASE}/localize/v3/cnpj"


_token_cache: dict = {"access_token": None, "exp": 0}


def _get_access_token() -> str:
    if _token_cache["access_token"] and _token_cache["exp"] > time.time():
        return _token_cache["access_token"]
    basic = base64.b64encode(f"{ASSERTIVA_CLIENT_ID}:{ASSERTIVA_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    _token_cache["access_token"] = payload["access_token"]
    TOKEN_EXPIRES_MINS = 30
    ERROR_MARGIN_MINS = 1
    expires_in = int(payload.get("expires_in", TOKEN_EXPIRES_MINS * 60))
    expires_in = max(0, expires_in - ERROR_MARGIN_MINS * 60)
    _token_cache["exp"] = time.time() + expires_in
    return _token_cache["access_token"]


_only_digits = lambda s: re.sub(r"\D", "", s or "")


def _doc_kind(doc: str) -> Tuple[str, str]:
    digits = _only_digits(doc)
    if len(digits) == 11:
        return "cpf", digits
    if len(digits) == 14:
        return "cnpj", digits
    raise ValueError("Documento deve conter 11 (CPF) ou 14 (CNPJ) dígitos.")


def _normalize_br_phone(raw: str) -> Dict[str, Optional[str]]:
    digits = _only_digits(raw)
    if digits.startswith("55") and len(digits) in (12, 13):
        nat = digits[2:]
    else:
        nat = digits
    e164 = None
    if len(nat) in (10, 11):  # 2 DDD + 8/9
        e164 = f"+55{nat}"
    elif digits.startswith("55") and len(digits) in (12, 13):
        e164 = f"+{digits}"
    return {
        "raw": raw,
        "digits": digits,
        "nat": nat,
        "e164": e164,
    }

def _phone_match_key(raw: str) -> Tuple[str, str]:
    """Gera chaves (10 e 11 dígitos) para casar feedback por número."""
    nat = _normalize_br_phone(raw)["nat"]
    return (nat[-10:], nat[-11:])  # útil p/ fixo (10) e móvel (11)

# --- Parsing de recência ---
def _parse_pt_datetime(s: str) -> Optional[dt.datetime]:
    # exemplo: "12/06/2020 às 10:14"
    if not s:
        return None
    m = re.search(r"(\d{2})/(\d{2})/(\d{4}).*?(\d{2}):(\d{2})", s)
    if not m:
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s)
        if not m:
            return None
        d, mth, y = map(int, m.groups())
        return dt.datetime(y, mth, d)
    d, mth, y, hh, mm = map(int, m.groups())
    return dt.datetime(y, mth, d, hh, mm)


def _parse_ultimo_contato(s: str) -> Optional[int]:
    """Converte 'Contato feito há 6 meses...' em dias aproximados."""
    if not s:
        return None
    m = re.search(r"há\s+(\d+)\s*(dia|dias|semana|semanas|m[eê]s|m[eê]ses|ano|anos)", s, re.I)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith("dia"):
        return val
    if unit.startswith("semana"):
        return val * 7
    if unit.startswith("m"):
        return val * 30
    if unit.startswith("ano"):
        return val * 365
    return None


# --- Construção de candidatos e ranqueamento ---
def _collect_candidates(resposta: Dict[str, Any], is_cnpj: bool) -> List[Dict[str, Any]]:
    cand: List[Dict[str, Any]] = []

    def add_from(path: List[str], tipo: str, fonte: str):
        node = resposta
        for p in path:
            node = node.get(p, {})
        if not isinstance(node, list):
            return
        for item in node:
            numero = item.get("numero")
            if not numero:
                continue
            apps = item.get("aplicativos", {}) or {}
            sup_wa  = bool(apps.get("whatsApp") or apps.get("whatsAppBusiness"))
            wa_biz  = bool(apps.get("whatsAppBusiness"))
            is_mob  = (tipo == "moveis")
            nao_pert = bool(item.get("naoPerturbe", False))
            hot = bool(item.get("hotphone", False))
            plus = bool(item.get("plus", False))
            gmb = bool(item.get("temGoogleMeuNegocio", False)) if is_cnpj else False
            ultimo = item.get("ultimoContato")

            created = (item.get("alteradoPor", {}) or {}).get("dataHora") or (item.get("criadoPor", {}) or {}).get("dataHora")
            created_dt = _parse_pt_datetime(created)

            cand.append({
                "numero": numero,
                "norm": _normalize_br_phone(numero),
                "is_mobile": is_mob,
                "supports_whatsapp": sup_wa,
                "whatsapp_business": wa_biz,
                "nao_perturbe": nao_pert,
                "hotphone": hot,
                "plus": plus,
                "tem_gmb": gmb,
                "ultimo_contato_txt": ultimo,
                "ultimo_contato_days": _parse_ultimo_contato(ultimo),
                "fonte": fonte,  # 'telefones' ou 'telefonesAdicionados'
                "created_dt": created_dt,
                "feedback": None,  # preencheremos depois
            })

    # telefones principais
    add_from(["telefones", "moveis"], "moveis", "telefones")
    add_from(["telefones", "fixos"],  "fixos",  "telefones")

    # adicionados manualmente
    add_from(["telefonesAdicionados", "moveis"], "moveis", "telefonesAdicionados")
    add_from(["telefonesAdicionados", "fixos"],  "fixos",  "telefonesAdicionados")

    # mapear feedback por número
    fb_map: Dict[str, str] = {}
    for tipo in ("moveis", "fixos"):
        for fb in (resposta.get("feedbackTelefones", {}) or {}).get(tipo, []) or []:
            num = fb.get("numero")
            aval = fb.get("avaliacao")
            if not num or not aval:
                continue
            k10, k11 = _phone_match_key(num)
            fb_map[k10] = aval
            fb_map[k11] = aval

    # aplicar feedback aos candidatos
    for c in cand:
        k10, k11 = _phone_match_key(c["numero"])
        c["feedback"] = fb_map.get(k11) or fb_map.get(k10)

    return cand


def _score_candidate(c: Dict[str, Any]) -> float:
    score = 0.0
    # WHATSAPP é critério principal
    if c["supports_whatsapp"]:
        score += 100
    else:
        score -= 100  # desclassifica, mas pode servir de fallback extremo

    # Feedback
    if c["feedback"] == "Positiva":
        score += 20
    elif c["feedback"] == "Negativa":
        score -= 40

    # Evitar DND
    if c["nao_perturbe"]:
        score -= 25

    # Tipo/priorização
    if c["is_mobile"]:
        score += 12
    elif c["whatsapp_business"]:
        score += 8
    else:
        score += 2

    # Sinais extras
    if c["hotphone"]:
        score += 8
    if c["plus"]:
        score += 4
    if c["tem_gmb"]:
        score += 3

    # Recência de contato (quanto mais recente, melhor)
    days = c["ultimo_contato_days"]
    if isinstance(days, int):
        # escore entre 0 e 36 aprox (quanto mais recente, maior)
        score += max(0, 365 - min(days, 365)) / 10.0

    # Recência de criação/alteração (peso menor)
    if isinstance(c["created_dt"], dt.datetime):
        age_days = (dt.datetime.utcnow() - c["created_dt"]).days
        score += max(0, 365 - min(age_days, 365)) / 20.0

    return score


def _choose_best(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None

    # 1) preferir com WhatsApp e sem DND
    primary = [c for c in candidates if c["supports_whatsapp"] and not c["nao_perturbe"]]
    # 2) se não houver, permitir WhatsApp mesmo com DND
    secondary = [c for c in candidates if c["supports_whatsapp"]]
    # 3) fallback final: quaisquer números
    pool = primary or secondary or candidates

    ranked = sorted(pool, key=_score_candidate, reverse=True)
    best = ranked[0]
    best["score"] = _score_candidate(best)
    best["e164"] = best["norm"]["e164"]
    return best


# --- Função principal ---
def get_best_whatsapp_phone(documento: str, *, finalidade: int = 1, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """
    Consulta CPF/CNPJ na Assertiva e retorna o melhor telefone para WhatsApp.

    Retorno (dict) (ou None se não houver telefones):
      {
        'numero': '(11) 99898-9898',
        'e164': '+5511998989898',
        'is_mobile': True,
        'supports_whatsapp': True,
        'whatsapp_business': False,
        'nao_perturbe': False,
        'hotphone': True,
        'plus': True,
        'tem_gmb': False,
        'feedback': 'Positiva'|'Negativa'|None,
        'ultimo_contato_txt': 'Contato feito há 6 meses via SMS.',
        'ultimo_contato_days': 180,
        'fonte': 'telefones'|'telefonesAdicionados',
        'created_dt': datetime|None,
        'score': float
      }
    """
    kind, digits = _doc_kind(documento)
    url = ENDPOINT_CPF if kind == "cpf" else ENDPOINT_CNPJ
    params = {"idFinalidade": finalidade}
    params[kind] = digits  # 'cpf' ou 'cnpj'

    headers = {
        "Authorization": f"Bearer {_get_access_token()}",
        "Accept": "application/json",
    }

    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        # se possível, exponha texto da API para log
        raise RuntimeError(f"Erro Assertiva {resp.status_code}: {resp.text}") from e

    payload = resp.json() or {}
    resposta = (payload.get("resposta") or {})
    if not resposta:
        return None

    is_cnpj = (kind == "cnpj")
    candidates = _collect_candidates(resposta, is_cnpj=is_cnpj)
    best = _choose_best(candidates)
    return best


def check_assertiva_access() -> tuple[bool, str]:
    try:
        _get_access_token()
    except:
        return False, 'Sem permissão para acessar a Assertiva neste horário.'
    else:
        return True, 'Acesso permitido.'