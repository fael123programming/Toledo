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


main()