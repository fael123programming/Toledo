from supabase import create_client
from dotenv import load_dotenv
from utils import assertiva
from typing import Optional
import streamlit as st
from io import BytesIO
import pandas as pd
import requests
import httpx
import uuid
import time


load_dotenv()

BUCKET = "planilhas"

auth_ok = bool(st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"])
client = create_client(st.secrets["connections"]["supabase"]["SUPABASE_URL"], st.secrets["connections"]["supabase"]["SUPABASE_KEY"]) if auth_ok else None


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


def _download_cloud_file(name: str) -> Optional[BytesIO]:
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


def _worksheet_to_df(name: str) -> Optional[pd.DataFrame]:
    if not client:
        return None
    try:
        buf = _download_cloud_file(name)
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


@st.fragment
def download_button(name: str):
    if f'gen_down_btn_{name}' in st.session_state and st.session_state[f'gen_down_btn_{name}']:
        with st.spinner(''):
            st.session_state[f'gen_down_btn_{name}_bytes'] = _download_cloud_file(name)
            st.session_state[f'gen_down_btn_{name}'] = False
        st.download_button(
            label="🡇",
            data=st.session_state[f'gen_down_btn_{name}_bytes'],
            file_name=name,
            mime="application/octet-stream",
            key=f"download_{name}",
            help="Baixar planilha",
            type="primary"
        )
    else:
        gen_down_btn = st.button(
            label="🡇",
            key=f"gen_down_btn_{name}",
            help="Gerar botão de download"
        )
        if gen_down_btn:
            st.session_state[f'gen_down_btn_{name}'] = True
            st.rerun(scope='fragment')


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
def visu_button(name: str):
    if st.button(
        label="⬆️",
        key=f"visu_{name}",
        help="Visualizar planilha"
    ):
        st.session_state.dialog_postfix = str(uuid.uuid4().hex[:8])
        df = _worksheet_to_df(name)
        show_worksheet(df, name)


@st.dialog(title="Visualizar Planilha", width="large")
def show_worksheet(df, name: str):
    st.markdown(f"# Planilha {name}")
    if df is None:
        st.error("Erro ao ler a planilha.")
        return
    cols = df.columns.tolist()
    may_access, msg = assertiva.check_assertiva_access()
    col_name_col, search_assertiva_col = st.columns([3, 1], vertical_alignment="bottom")
    with col_name_col:
        col_name = st.selectbox(
            'Nome da coluna',
            options=cols,
            key=f"col_name_{name}_{st.session_state.dialog_postfix}",
            help="Selecione a coluna que contém os nomes completos" if may_access else msg,
            disabled=not may_access
        )
    with search_assertiva_col:
        search_assertiva = st.button(
            "🔍 Buscar Telefone",
            key=f"search_assertiva_{name}_{st.session_state.dialog_postfix}",
            help="Buscar telefone mais recente usando Assertiva" if may_access else msg,
            disabled=not may_access
        )
    df_edited = st.data_editor(
        df,
        key=f"data_editor_{name}_{st.session_state.dialog_postfix}",
        use_container_width=True,
        hide_index=True
    )
    if st.button(
        "Salvar Alterações",
        key=f"save_button_{name}_{st.session_state.dialog_postfix}",
        disabled=df_edited.equals(df)
    ):
        try:
            buf = BytesIO()
            if name.lower().endswith((".xlsx", ".xls")):
                df_edited.to_excel(buf, index=False)
            else:
                df_edited.to_csv(buf, index=False)
            buf.name = name
            _delete_cloud_file(name)
            if _upload_to_cloud(buf):
                st.success(f"Alterações salvas em {name}!")
                st.rerun(scope="app")
        except Exception as e:
            st.error(f"Erro ao salvar alterações: {e}")


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


def main():
    st.markdown("# 📈 Planilhas na Nuvem")
    st.subheader("🤝🏻 Armazene, acesse e gerencie suas planilhas de qualquer lugar — com segurança e praticidade.")
    if not auth_ok:
        st.warning(
            "⚠️ Defina SUPABASE_URL e SUPABASE_KEY em variáveis de ambiente ou em st.secrets para habilitar o armazenamento."
        )
        return
    st.session_state.files = _list_cloud_files()
    if st.session_state.files:
        _, upload_col = st.columns([10, 3], vertical_alignment="center")
        with upload_col:
            upload_button()
        with st.container(border=True):
            search_query = st.text_input(
                "🔍 Pesquisar planilhas",
                placeholder="Digite o nome da planilha...",
                key="search_sheets"
            )
        searched_files = st.session_state.files
        if search_query:
            searched_files = [f for f in st.session_state.files if search_query.lower() in f.lower()]
            if not searched_files:
                st.warning("Nenhuma planilha encontrada com esse termo.")
        for i, file in enumerate(searched_files):
            with st.container(border=True, key=f'worksheet_container_{i}'):
                file_name_header_col, action_header_col = st.columns([3, 1], vertical_alignment="center")
                with file_name_header_col:
                    st.markdown("**Nome**")
                with action_header_col:
                    _, action_name_col, _ = st.columns(3, vertical_alignment="center")
                    with action_name_col:
                        st.markdown("**Ações**")
                file_name_col, action_col = st.columns([3, 1], vertical_alignment="center")
                with file_name_col:
                    st.markdown(file)
                with action_col:
                    visu_col, download_col, del_col = st.columns(3, vertical_alignment="center")
                    with visu_col:
                        visu_button(file)
                    with download_col:
                        download_button(file)
                    with del_col:
                        del_button(file)
    else:
        st.warning("Nenhuma planilha armazenada. Faça upload para começar.")
        upload_button()


main()