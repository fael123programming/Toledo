from dotenv import load_dotenv
import streamlit as st
import os


load_dotenv()


auth_ok = bool(
    st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
)


def load_ultramsg_env():
    ultramsg_vars = []
    i = 0
    for key, value in st.secrets["ultramsg"].items():
        if f"ULTRAMSG_INSTANCE_ID_{i+1}" in os.environ:
            ultramsg_vars.append({
                "instance_id": os.environ[f"ULTRAMSG_INSTANCE_ID_{i+1}"],
                "instance_token": os.environ[f"ULTRAMSG_INSTANCE_TOKEN_{i+1}"],
                "phone_number": os.environ[f"ULTRAMSG_INSTANCE_PHONE_NUMBER_{i+1}"]
            })
            i += 1
        else:
            break
    if ultramsg_vars:
        st.session_state["ultramsg_vars"] = ultramsg_vars
    else:
        st.session_state["ultramsg_vars"] = None
        st.warning("⚠️ Nenhuma variável de ambiente ULTRAMSG encontrada.")


def main():
    load_ultramsg_env()
    st.markdown("# 🟩 WhatsApp")
    st.subheader("📤 Envie as suas mensagens para os contatos das planilhas automaticamente.")
    if not st.session_state["ultramsg_vars"]:
        st.warning(
            "⚠️ Defina as variáveis para comunicação com a API do WhatsApp para habilitar o envio automático de mensagens."
        )
    st.write(st.session_state["ultramsg_vars"])
    st.write(st.secrets["ultramsg"])


main()