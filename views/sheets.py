from utils import algorithms, worksheets, assertiva
from supabase import create_client
from utils import whatsapp as wpp
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
from io import BytesIO
import pandas as pd
import random
import time
import uuid


load_dotenv()

BUCKET = "planilhas"

auth_ok = bool(st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"])
client = create_client(st.secrets["connections"]["supabase"]["SUPABASE_URL"], st.secrets["connections"]["supabase"]["SUPABASE_KEY"]) if auth_ok else None


def load_ultramsg_env():
    ultramsg_vars = {}
    all_ultramsg = st.secrets["ultramsg"].to_dict()
    for key, creds in all_ultramsg.items():
        ultramsg_vars[key] = {
            "ID": creds["ID"],
            "TOKEN": creds["TOKEN"],
            "PHONE_NUMBER": creds["PHONE_NUMBER"]
        }
    st.session_state["ultramsg_vars"] = ultramsg_vars


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
    if st.button(
        "↩️ Voltar",
        key=f"back_btn_worksheet_{st.session_state['df_name']}",
        help='Voltar para gerenciamento de planilhas'
    ):
        st.session_state.show_wpp_view = False
        st.session_state.df_wpp = None
        st.session_state.df_name = None
        st.rerun(scope='app')
    if "df_wpp" in st.session_state and type(st.session_state['df_wpp']) is pd.DataFrame:
        if "assertiva_edited" not in st.session_state:
            st.session_state['assertiva_edited'] = False
        worksheet_tab, message_tab, lines_tab, time_tab, phone_tab, start_tab = st.tabs(['Planilha', 'Mensagem', 'Linhas', 'Intervalo', 'Telefone', 'Iniciar'])
        with worksheet_tab:
            with st.container(key='worksheet_container_key', border=True):
                st.subheader(f"📊 Planilha {st.session_state['df_name']}")
                st.info("Revise a sua planilha antes de disparar. Quando estiver pronto, passe para a próxima aba ➡️.")
                cols = st.session_state['df_wpp'].columns.tolist()
                may_access, msg = assertiva.check_assertiva_access()
                col_name_col, search_assertiva_col = st.columns([3, 1], vertical_alignment="bottom")
                detected_doc_col = algorithms.detect_polo_passivo_doc_column(st.session_state['df_wpp'])[0]
                with col_name_col:
                    col_name = st.selectbox(
                        'Nome da coluna',
                        options=cols,
                        index=cols.index(detected_doc_col) if detected_doc_col in cols else 0,
                        key="col_name_assertiva_key",
                        help="Selecione a coluna que contém os nomes completos" if may_access else msg,
                        disabled=not may_access
                    )
                with search_assertiva_col:
                    search_assertiva = st.button(
                        "🔍 Buscar Telefone",
                        key="search_assertiva_btn_key",
                        help="Buscar telefone mais recente usando Assertiva" if may_access else msg,
                        disabled=not may_access
                    )
                    if search_assertiva:
                        st.session_state['getting_phones_assertiva'] = True
                        st.session_state['column_getting_phones_assertiva'] = col_name
                        st.rerun(scope='fragment')
                if 'getting_phones_assertiva' in st.session_state and st.session_state['getting_phones_assertiva']:
                    with st.status("Consultando Assertiva..."):
                        phones_list = []
                        for i, valor_column in enumerate(st.session_state['df_wpp'][st.session_state['column_getting_phones_assertiva']].tolist()):
                            try:
                                result = assertiva.get_best_whatsapp_phone(valor_column)
                                phone_e164 = result["e164"] if result else None
                            except Exception as e:
                                with st.container(key=f"getting_assertiva_phones_{i}_{str(valor_column)}", border=True):
                                    st.write(f"Erro ao buscar telefone de \"{valor_column}\".")
                                    st.error(e)
                                    phones_list.append('')
                            else:
                                phones_list.append(phone_e164)
                        st.session_state["df_wpp"][f"Telefone {st.session_state['column_getting_phones_assertiva']}"] = pd.Series(phones_list)
                        st.session_state['assertiva_edited'] = True
                        st.session_state['getting_phones_assertiva'] = False
                        st.rerun(scope='fragment')
                df_edited = st.data_editor(
                    st.session_state['df_wpp'],
                    key=f"data_editor_{st.session_state['df_name']}",
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    disabled='getting_phones_assertiva' in st.session_state and st.session_state['getting_phones_assertiva']
                )
                st.write(st.session_state['assertiva_edited'])
                st.write(df_edited.equals(st.session_state['df_wpp']))
                if st.button(
                    "Salvar Alterações",
                    key=f"save_button_{st.session_state['df_name']}",
                    disabled=df_edited.equals(st.session_state['df_wpp']) and not st.session_state['assertiva_edited']
                ):
                    try:
                        buf = BytesIO()
                        if st.session_state['df_name'].lower().endswith((".xlsx", ".xls")):
                            df_edited.to_excel(buf, index=False)
                        else:
                            df_edited.to_csv(buf, index=False)
                        buf.name = st.session_state['df_name']
                        worksheets.delete_cloud_file(st.session_state['df_name'])
                        if worksheets.upload_to_cloud(buf):
                            st.success(f"Alterações salvas em {st.session_state['df_name']}!")
                            st.session_state['assertiva_edited'] = False
                            st.rerun(scope="app")
                    except Exception as e:
                        st.error(f"Erro ao salvar alterações: {e}")
        with message_tab:
            with st.container(key='message_container_key', border=True):
                st.subheader("📝 Modelo de mensagem")
                st.info("Monte a sua mensagem usando chaves e os nomes das colunas. Quando estiver pronto, passe para a próxima aba ➡️.")
                message_template = st.text_area(
                    "Mensagem",
                    placeholder="Use {nome da coluna} para referenciar cada coluna na planilha. O valor será substituído pelo conteúdo da célula correspondente.",
                    key="message_template_key",
                    help="Use {nome} para referenciar uma coluna da planilha.",
                    max_chars=5000
                )
                st.caption(f"Estas são as colunas disponíveis na planilha: {', '.join(st.session_state['df_wpp'].columns)}")
        with lines_tab:
            with st.container(key='special_params_container_key', border=True):
                st.subheader("📍 Linhas para disparar")
                st.info("Defina quais linhas da planilha devem ser disparadas. Quando estiver pronto, passe para a próxima aba ➡️.")
                from_col, to_col = st.columns(2, vertical_alignment="center")
                with from_col:
                    from_col_select = st.number_input(
                        "Enviar de (linha)",
                        min_value=1,
                        max_value=len(st.session_state['df_wpp']),
                        value=1,
                        step=1,
                        key="from_col_select_key"
                    )
                with to_col:
                    to_col_select = st.number_input(
                        "Enviar até (linha)",
                        min_value=from_col_select,
                        max_value=len(st.session_state['df_wpp']),
                        value=len(st.session_state['df_wpp']),
                        step=1,
                        key="to_col_select_key"
                    )
        with time_tab:
            with st.container(key='time_container_key', border=True):
                st.subheader("⏳ Tempo entre cada disparo")
                st.info("Configure quantos segundos haverá entre cada disparo. Quando estiver pronto, passe para a próxima aba ➡️.")
                start_secs_col, end_secs_col = st.columns(2, vertical_alignment="center")
                with start_secs_col:
                    start_secs_select = st.number_input(
                        "Aguardar de (segundos)",
                        min_value=0,
                        max_value=60,
                        value=1,
                        step=1,
                        key="start_secs_select_key"
                    )
                with end_secs_col:
                    end_secs_select = st.number_input(
                        "Aguardar até (segundos)",
                        min_value=start_secs_select,
                        max_value=60,
                        value=30,
                        step=1,
                        key="end_secs_select_key"
                    )
                st.caption("A cada disparo, será aplicado um atraso aleatório (em segundos) entre Aguardar de e Aguardar até.")
        with phone_tab:
            with st.container(key='phones_container_key', border=True):
                st.subheader("📱 Telefones")
                st.info("Indique quais números de telefone usar nos disparos. Quando estiver pronto, passe para a próxima aba ➡️.")
                phone_owner_opts = list(map(lambda val: val.title(), st.secrets["ultramsg"].keys()))
                owner_select = st.multiselect(
                    "📞 Selecione o(s) remetente(s)",
                    options=phone_owner_opts,
                    default=phone_owner_opts,
                    key="phone_number_select",
                    help="Selecione o(s) remetente(s) para enviar as mensagens."
                )
                for owner in owner_select:
                    st.info(st.secrets["ultramsg"][owner.lower()]["PHONE_NUMBER"])
                st.caption("Os disparos são feitos alternadamente entre um e outro telefone de forma sequencial.")
                detected_col = algorithms.detect_brazil_phone_column(st.session_state['df_wpp'])[0]
                col_name_dest = st.selectbox(
                    '📲 Defina a coluna da planilha com os números de telefone destinatários',
                    options=cols,
                    index=cols.index(detected_col) if detected_col in cols else 0,
                    key="col_name_dest_key",
                    help="Selecione a coluna que contenha os números de telefone para enviar as mensagens"
                )
        with start_tab:
            if st.button(
                "Enviar mensagens",
                help="Enviar mensagens para os contatos da planilha selecionada.",
                type="primary",
                key="send_msgs_btn_key",
                disabled=len(message_template.strip()) == 0 or from_col_select > to_col_select or start_secs_select > end_secs_select
            ):
                df_edited["mensagem"] = df_edited.apply(lambda row: message_template.strip().format(**row.to_dict()), axis=1)
                start_1b = int(from_col_select)
                end_1b = int(to_col_select)
                start = max(0, start_1b - 1)
                end = min(len(df_edited) - 1, end_1b - 1)
                subset = df_edited.iloc[start:end + 1]
                for i, row in subset.iterrows():
                    perfil = random.choice(list(st.secrets["ultramsg"].keys()))
                    token = st.secrets["ultramsg"][perfil]["TOKEN"]
                    response = wpp.send_wpp_msg(row["mensagem"], str(row[col_name_dest]), token)
                    try:
                        if response["sent"] == "true":
                            st.success(f"Mensagem enviada para \"{row[col_name_dest]}\" ✅")
                        else:
                            st.error(f"Mensagem não enviada para \"{row[col_name_dest]}\" ❌")
                    except Exception as e:
                        st.error(f"Mensagem não enviada para \"{row[col_name_dest]}\" ❌ ({str(e)})")
                    if i < len(subset) - 1:
                        r = random.randint(start_secs_select, end_secs_select)
                        st.info(f"Aguardando {r} segundo(s) para o próximo disparo...")
                        time.sleep(r)


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
                    whatsapp_col, download_col, del_col = st.columns(3, vertical_alignment="center")
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