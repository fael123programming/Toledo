import streamlit as st
import os


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
    # load_ultramsg_env()
    st.markdown("# 🟩 WhatsApp")
    st.subheader("📤 Envie as suas mensagens para os contatos das planilhas automaticamente.")
    all_ultramsg = st.secrets["ultramsg"].to_dict()
    for chave, creds in all_ultramsg.items():
        st.write(f"Identificador: {chave}")
        st.write(f"ID: {creds['ID']}")
        st.write(f"TOKEN: {creds['TOKEN']}")
        st.write(f"PHONE_NUMBER: {creds['PHONE_NUMBER']}")
        st.write("---")
    # st.write(st.session_state["ultramsg_vars"])
    st.write(st.secrets)
    # if not st.session_state["ultramsg_vars"]:
    #     st.warning(
    #         "⚠️ Defina as variáveis para comunicação com a API do WhatsApp para habilitar o envio automático de mensagens."
    #     )


main()