import streamlit as st


auth_ok = bool(
    st.secrets["connections"]["supabase"]["SUPABASE_URL"] and st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
)


def main():
    st.markdown("# 🟩 WhatsApp")
    st.subheader("📤 Envie as suas mensagens para os contatos das planilhas automaticamente.")
    if not auth_ok:
        st.warning(
            "⚠️ Defina SUPABASE_URL e SUPABASE_KEY em variáveis de ambiente ou em st.secrets para habilitar o armazenamento."
        )
        return


main()