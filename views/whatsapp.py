import streamlit as st
import os


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


main()