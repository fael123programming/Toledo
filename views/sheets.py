import streamlit.components.v1 as components
from supabase import create_client
from dotenv import load_dotenv
import plotly.express as px
from datetime import datetime
import streamlit as st
from io import BytesIO
import pandas as pd
import httpx
import uuid
import os


load_dotenv()

BUCKET = "planilhas"

auth_ok = bool(st.session_state['SUPABASE_URL'] and st.session_state['SUPABASE_KEY'])
client = create_client(st.session_state['SUPABASE_URL'], st.session_state['SUPABASE_KEY']) if auth_ok else None


def _upload_to_cloud(file) -> bool:
    if not client:
        return False
    try:
        data = file.getvalue()
        client.storage.from_(BUCKET).upload(file.name, data)
        return True
    except Exception as e:
        st.error(f"Erro Supabase: {e}")
        return False


def _list_cloud_files() -> list[str]:
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


def _delete_cloud_file(name: str) -> bool:
    if not client:
        return False
    try:
        client.storage.from_(BUCKET).remove(name)
        return True
    except Exception as e:
        st.error(f"Erro Supabase: {e}")
        return False


def _download_cloud_file(name: str):
    if not client:
        return None
    data = client.storage.from_(BUCKET).download(name)
    return BytesIO(data) if data else None


@st.fragment
def download_button(name: str):
    st.download_button(
        label="🡇",
        data=_download_cloud_file(name),
        file_name=name,
        mime="application/octet-stream",
        key=f"download_{name}",
        help="Baixar planilha"
    )


@st.fragment
def del_button(name: str):
    if st.button(
        label="🗑️",
        key=f"delete_{name}",
        help="Deletar planilha"
    ):
        st.session_state.dialog_postfix = str(uuid.uuid4().hex[:8])
        show_delete_confirmation(name)


@st.dialog(title="Confirmação de Deleção")
def show_delete_confirmation(name: str):
    st.warning(f"**Você tem certeza que deseja deletar `{name}`?**")
    if st.button(
        "Confirmar", 
        key=f'delete_button_{st.session_state.dialog_postfix}_{name}', 
        type="primary",
        use_container_width=True
    ):
        if _delete_cloud_file(name):
            st.rerun(scope='app')


@st.fragment
def upload_button():
    if st.button(
        label="➕ Upload Planilha",
        key="upload",
        help="Fazer upload de planilha"
    ):
        st.session_state.dialog_postfix = str(uuid.uuid4().hex[:8])
        show_upload_dialog()


@st.dialog(title="Fazer Upload de Planilha")
def show_upload_dialog():
    new_file = st.file_uploader(
        "Selecionar arquivo",
        type=["csv", "xlsx"],
        key=f"cloud_upload_{st.session_state.dialog_postfix}"
    )
    if new_file and st.button(
        "Enviar",
        key=f'upload_button_{st.session_state.dialog_postfix}',
        help="Enviar planilha para a nuvem",
        type="primary",
        use_container_width=True
    ):
        if _upload_to_cloud(new_file):
            st.success(f"{new_file.name} enviado!")
            st.rerun(scope='app')


@st.fragment
def render():
    html = """
    <style>
    /* Cloud backdrop - soft wave */
    .cloud-bg {
    width: 100%;
    min-height: 110px;
    background: linear-gradient(110deg, #e0e7ff 10%, #f1f5f9 100%);
    position: relative;
    margin-bottom: 28px;
    border-radius: 48px 48px 16px 16px/36px 36px 12px 12px;
    overflow: hidden;
    box-shadow: 0 8px 30px 0 rgba(82, 99, 171, 0.09);
    }
    @media (prefers-color-scheme: dark) {
    .cloud-bg {
        background: linear-gradient(120deg, #202646 40%, #1e293b 100%);
        box-shadow: 0 6px 30px 0 rgba(20,30,50,0.26);
    }
    }

    /* Title - gradient text */
    .cloud-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 800;
    font-size: 2.1rem;
    background: linear-gradient(90deg, #647acb 30%, #6366f1 100%);
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    margin: 0 0 16px 0;
    letter-spacing: -1px;
    padding-top: 32px;
    padding-left: 48px;
    padding-bottom: 2px;
    }
    @media (prefers-color-scheme: dark) {
    .cloud-title {
        background: linear-gradient(90deg, #a5b4fc 25%, #60a5fa 90%);
    }
    }

    /* Subtext - icon + faded text */
    .cloud-sub {
    font-size: 1.03rem;
    color: #475569;
    padding-left: 52px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 10px;
    }
    @media (prefers-color-scheme: dark) {
    .cloud-sub { color: #cbd5e1; }
    }

    /* Floating SVG Cloud Decoration */
    .cloud-svg {
    position: absolute;
    left: 0; top: 0; z-index: 0;
    width: 250px; height: 90px;
    opacity: 0.15;
    }
    @media (max-width: 600px) {
    .cloud-title, .cloud-sub { padding-left: 18px;}
    .cloud-title { font-size: 1.25rem; }
    .cloud-bg { border-radius: 24px 24px 10px 10px; }
    }
    </style>
    <div class="cloud-bg">
    <svg class="cloud-svg" viewBox="0 0 250 90" fill="none">
        <ellipse cx="90" cy="65" rx="90" ry="20" fill="#b6c6f7"/>
        <ellipse cx="170" cy="45" rx="60" ry="14" fill="#e0e8f7"/>
    </svg>
    <div style="position:relative;z-index:1;">
        <div class="cloud-title">
        <span>Gerencie suas planilhas na nuvem</span>
        </div>
        <div class="cloud-sub">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M16 16v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2" stroke="#647acb" stroke-width="1.6" stroke-linecap="round"/>
            <path d="M21 15V5a2 2 0 0 0-2-2H10a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2Z" stroke="#6366f1" stroke-width="1.6"/>
            <path d="m16 8.5-2.5 2.5L16 13.5" stroke="#6366f1" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
        <span>
            Armazene, acesse e gerencie suas planilhas de qualquer lugar — com segurança e praticidade.
        </span>
        </div>
    </div>
    </div>
    """
    components.html(html, height=180)
    if not auth_ok:
        st.warning(
            "⚠️ Defina SUPABASE_URL e SUPABASE_KEY em variáveis de ambiente ou em st.secrets para habilitar o armazenamento."
        )
        return
    files = _list_cloud_files()
    if files:
        _, upload_col = st.columns([10, 2], vertical_alignment="center")
        with upload_col:
            upload_button()
        search_query = st.text_input(
            "🔍 Pesquisar planilhas",
            placeholder="Digite o nome da planilha...",
            key="search_sheets"
        )
        for i, file in enumerate(files):
            with st.container(border=True, key=f'worksheet_container_{i}'):
                file_name_header_col, download_header_col, del_header_col = st.columns([3, 1, 1], vertical_alignment="center")
                with file_name_header_col:
                    st.markdown("**Nome**")
                with download_header_col:
                    st.markdown("**Baixar**")
                with del_header_col:
                    st.markdown("**Deletar**")
                file_name_col, download_col, del_col = st.columns([3, 1, 1], vertical_alignment="center")
                with file_name_col:
                    st.markdown(file)
                with download_col:
                    download_button(file)
                with del_col:
                    del_button(file)
    else:
        st.warning("Nenhuma planilha armazenada. Faça upload para começar.")
        upload_button()
    #     st.markdown("#### Upload para nuvem")
    #     new_file = st.file_uploader("Selecionar arquivo", type=["csv", "xlsx"], key="cloud_upload")
    #     if new_file and st.button("Enviar para Supabase", type="primary"):
    #         if _upload_to_cloud(new_file):
    #             st.success(f"{new_file.name} enviado!")
    #             # st.rerun(scope='app')
    # with col_manage:
    #     st.markdown("#### Arquivos no bucket")
    #     if not files:
    #         st.info("Nenhuma planilha armazenada.")
    #     else:
    #         sel = st.selectbox("Selecionar arquivo", files)
    #         action = st.radio("Ação", ["Baixar", "Remover"], horizontal=True)
    #         if st.button("Executar"):
    #             if action == "Baixar":
    #                 data = _download_cloud_file(sel)
    #                 if data:
    #                     st.download_button("Download", data=data, mime="application/octet-stream", file_name=sel)
    #             else:
    #                 if _delete_cloud_file(sel):
    #                     st.success("Arquivo removido.")
    #                     st.rerun(scope='app')