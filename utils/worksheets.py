from supabase import create_client
from dotenv import load_dotenv
from typing import Optional
import streamlit as st
from io import BytesIO
import pandas as pd
import requests
import httpx
import time


load_dotenv()

BUCKET = "planilhas"

auth_ok = bool(st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"])
client = create_client(st.secrets["connections"]["supabase"]["SUPABASE_URL"], st.secrets["connections"]["supabase"]["SUPABASE_KEY"]) if auth_ok else None


def upload_to_cloud(file) -> bool:
    if not client:
        return False
    try:
        data = file.getvalue()
        client.storage.from_(BUCKET).upload(file.name, data)
        return True
    except Exception as e:
        st.error(f"Erro Supabase: {e}")
        return False


def list_cloud_files() -> list[str]:
    if not client:
        return []
    try:
        objs = client.storage.from_(BUCKET).list("")
    except httpx.HTTPError as e:
        st.error(f"Erro de conexão com Supabase: {e}")
        return []
    except Exception as e:
        st.error(f"Erro Supabase: {e}")
        return []
    return [
        obj["name"] for obj in objs
        if obj["name"] not in [".emptyFolderPlaceholder", "."]
        and not obj["name"].endswith("/")
    ]


def delete_cloud_file(name: str) -> bool:
    if not client:
        return False
    try:
        client.storage.from_(BUCKET).remove(name)
        return True
    except Exception as e:
        st.error(f"Erro Supabase: {e}")
        return False


def download_cloud_file(name: str) -> Optional[BytesIO]:
    try:
        signed = client.storage.from_(BUCKET).create_signed_url(name, 60)
        url = signed["signedURL"]
        url = f"{url}&v={int(time.time())}"
        r = requests.get(url, headers={"Cache-Control": "no-cache"})
        r.raise_for_status()
        return BytesIO(r.content) if r.content else None
    except Exception as e:
        st.error(f"Erro ao baixar {name}: {e}")
        return None


def worksheet_to_df(name: str) -> Optional[pd.DataFrame]:
    if not client:
        return None
    try:
        buf = download_cloud_file(name)
        if buf is None:
            return None
        if name.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(buf)
        else:
            try:
                df = pd.read_csv(buf, encoding="utf-8")
            except UnicodeDecodeError:
                buf.seek(0)
                df = pd.read_csv(buf, encoding="latin1")
        return df
    except Exception as e:
        st.error(f"Erro ao baixar {name}: {e}")
        return None