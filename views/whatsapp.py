import uuid
from utils import worksheets
import streamlit as st


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
def pre_visu_worksheet(worksheet_name: str):
    if st.button(
        label="📊 Visualizar planilha",
        key="pre_visu_worksheet",
        use_container_width=True
    ):
        st.session_state.dialog_postfix = str(uuid.uuid4().hex[:8])
        df = worksheets.worksheet_to_df(worksheet_name)
        show_worksheet(df, worksheet_name)


@st.dialog(title="📊 Visualização da Planilha")
def show_worksheet(df, name: str):
    st.subheader(f"Planilha: {name}")
    st.dataframe(df, use_container_width=True, hide_index=True, key=f'worksheet_df_{st.session_state.dialog_postfix}')


def main():
    load_ultramsg_env()
    st.markdown("# 🟩 WhatsApp")
    st.subheader("📤 Envie as suas mensagens para os contatos das planilhas automaticamente.")
    if not st.session_state["ultramsg_vars"]:
        st.warning(
            "⚠️ Defina as variáveis para comunicação com a API do WhatsApp para habilitar o envio automático de mensagens."
        )
    owner_col, phone_number_col = st.columns(2, vertical_alignment="center")
    with owner_col:
        owner_col_select = st.selectbox(
            "📞 Selecione o remetente",
            options=list(map(lambda val: val.title(), st.session_state["ultramsg_vars"].keys())),
            key="phone_number_select",
            help="Selecione o remetente para enviar as mensagens."
        )
    with phone_number_col:
        phone_number = st.text_input(
            "📱 Número de telefone",
            value=st.session_state["ultramsg_vars"][owner_col_select.lower()]["PHONE_NUMBER"],
            key="phone_number_input",
            help="Este é o número de telefone que enviará as mensagens.",
            disabled=True
        )
    st.session_state.files = worksheets.list_cloud_files()
    if st.session_state.files:
        worksheet_whatsapp_col, pre_visu_worksheet_col = st.columns(2, vertical_alignment="bottom")
        with worksheet_whatsapp_col:
            worksheet_select = st.selectbox(
                "📈 Selecione a planilha",
                options=st.session_state.files,
                key="worksheet_whatsapp_select",
                help="Selecione a planilha para enviar as mensagens.",
                use_container_width=True
            )
        with pre_visu_worksheet_col:
            st.write(worksheet_select)
    else:
        st.warning("Nenhuma planilha armazenada. Faça upload na opção \"Planilhas\" no menu lateral para começar.")


main()