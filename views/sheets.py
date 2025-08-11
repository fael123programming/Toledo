import pandas as pd
from utils import assertiva, algorithms
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
from utils import worksheets
import streamlit as st
from io import BytesIO
import uuid


load_dotenv()

BUCKET = "planilhas"

auth_ok = bool(st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"])
client = create_client(st.secrets["connections"]["supabase"]["SUPABASE_URL"], st.secrets["connections"]["supabase"]["SUPABASE_KEY"]) if auth_ok else None


@st.fragment
def download_button(name: str):
    if f'gen_down_btn_{name}' in st.session_state and st.session_state[f'gen_down_btn_{name}']:
        with st.spinner(''):
            st.session_state[f'gen_down_btn_{name}_bytes'] = worksheets.download_cloud_file(name)
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
        if worksheets.delete_cloud_file(name):
            st.rerun(scope='app')


@st.fragment
def visu_button(name: str):
    if st.button(
        label="↗️",
        key=f"visu_{name}",
        help="Visualizar planilha"
    ):
        st.session_state.dialog_postfix = str(uuid.uuid4().hex[:8])
        df = worksheets.worksheet_to_df(name)
        show_worksheet(df, name)


@st.fragment
def wpp_button(name: str):
    if st.button(
        label="🟩",
        key=f"wpp_{name}",
        help="Disparar para o WhatsApp"
    ):
        df = worksheets.worksheet_to_df(name)
        st.session_state.show_wpp_view = True
        st.session_state.df_wpp = df
        st.session_state.df_name = name
        st.rerun(scope='app')


@st.dialog(title="Visualizar Planilha", width="large")
def show_worksheet(df, name: str):
    st.markdown(f"# Planilha {name}")
    if df is None:
        st.error("Erro ao ler a planilha.")
        return
    cols = df.columns.tolist()
    may_access, msg = assertiva.check_assertiva_access()
    col_name_col, search_assertiva_col = st.columns([3, 1], vertical_alignment="bottom")
    detected_col = algorithms.detect_name_column(df)[0]
    st.write(may_access, msg, datetime.now())
    with col_name_col:
        col_name = st.selectbox(
            'Nome da coluna',
            options=cols,
            index=cols.index(detected_col) if detected_col in cols else 0,
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
        hide_index=True,
        num_rows="dynamic"
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
            worksheets.delete_cloud_file(name)
            if worksheets.upload_to_cloud(buf):
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
        if worksheets.upload_to_cloud(new_file):
            st.success(f"{new_file.name} enviado!")
            st.rerun(scope='app')


@st.fragment
def render_whatsapp_fragment():
    if "df_wpp" in st.session_state and type(st.session_state['df_wpp']) is pd.DataFrame:
        with st.form("send_messages_form", border=False):
            st.subheader(f"📊 Planilha {st.session_state['df_name']}")
            st.dataframe(st.session_state['worksheet'], use_container_width=True, hide_index=False, key=f"loaded_worksheet_df_{st.session_state['df_name']}")
            st.subheader("📝 Modelo de mensagem")
            message_template = st.text_area(
                "Mensagem",
                placeholder="Use {nome da coluna} para referenciar cada coluna na planilha. O valor será substituído pelo conteúdo da célula correspondente.",
                key="message_template",
                help="Use {nome} para referenciar uma coluna da planilha.",
                max_chars=5000
            )
            st.caption(f"Estas são as colunas disponíveis na planilha: {', '.join(st.session_state['df_wpp'].columns)}")
            from_col, to_col = st.columns(2, vertical_alignment="center")
            with from_col:
                from_col_select = st.number_input(
                    "📍 Enviar de (linha)",
                    min_value=0,
                    max_value=len(st.session_state['df_wpp']),
                    value=1,
                    step=1
                )
            with to_col:
                to_col_select = st.number_input(
                    "📍 Enviar até (linha)",
                    min_value=from_col_select,
                    max_value=len(st.session_state['df_wpp']),
                    value=len(st.session_state['df_wpp']),
                    step=1
                )
            if st.form_submit_button(
                "Enviar mensagens",
                help="Enviar mensagens para os contatos da planilha selecionada.",
                type="primary"
            ):
                pass


def main():
    st.markdown("# 📊 Planilhas na Nuvem")
    st.subheader("🤝🏻 Armazene, acesse e gerencie suas planilhas de qualquer lugar — com segurança e praticidade.")
    if not auth_ok:
        st.warning(
            "⚠️ Defina SUPABASE_URL e SUPABASE_KEY em variáveis de ambiente ou em st.secrets para habilitar o armazenamento."
        )
        return
    st.session_state.files = worksheets.list_cloud_files()
    if "show_wpp_view" in st.session_state and st.session_state.show_wpp_view:
        render_whatsapp_fragment()
    elif st.session_state.files:
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
                    visu_col, whatsapp_col, download_col, del_col = st.columns(4, vertical_alignment="center")
                    with visu_col:
                        visu_button(file)
                    with whatsapp_col:
                        wpp_button(file)
                    with download_col:
                        download_button(file)
                    with del_col:
                        del_button(file)
    else:
        st.warning("Nenhuma planilha armazenada. Faça upload para começar.")
        upload_button()


main()