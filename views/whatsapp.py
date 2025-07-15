import streamlit as st
import pandas as pd
import webbrowser
import pyautogui
import time


@st.fragment
def render():
    if "sending" not in st.session_state:
        st.session_state.sending = False
    st.title("📲 WhatsApp Lead")
    if st.session_state.sending:
        df = st.session_state.df
        phone_col = st.session_state.phone_col
        message_template = st.session_state.message_template
        columns = df.columns.tolist()
        progress = st.empty()
        progress.progress(0)
        st.info('Enviado mensagens, aguarde...')
        for index, row in df.iterrows():
            try:
                phone = str(row[phone_col])
                phone = ''.join(filter(str.isdigit, phone))
                message = message_template
                for col in columns:
                    message = message.replace(f"{{{col}}}", str(row[col]))
                url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
                webbrowser.open(url)
                time.sleep(10)
                pyautogui.hotkey('enter')  # Pressiona Enter para enviar a mensagem
                time.sleep(2)
                pyautogui.hotkey('ctrl', 'w')  # Fecha a aba do WhatsApp após enviar
                time.sleep(5)
            except Exception as e:
                st.error(f"Não consegui enviar para {row[phone_col]}: {str(e)}")
            finally:
                progress.progress((index + 1) / len(df))
        progress.progress(1.0)
        st.success('Finalizado!')
        time.sleep(5)
        st.session_state.sending = False
        st.rerun(scope='fragment')
    else:
        uploaded_file = st.file_uploader("Enviar arquivo de dados", type=['xlsx', 'xls', 'csv'])
        if uploaded_file:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith(('xlsx', 'xls')) else pd.read_csv(uploaded_file)
            st.subheader("Visualizar dados")
            st.dataframe(df, use_container_width=True, hide_index=True)
            phone_col = st.selectbox("Selecionar número de telefone:", df.columns.tolist())
            message_template = st.text_area(
                "Compor mensagem (Use {Nome_Coluna} como variável)", 
                "Olá {nome}, você tem o processo {processo} com polo ativo {polo_ativo} e polo passivo {polo_passivo}!"
            )
            if st.button("Enviar"):
                st.session_state.df = df
                st.session_state.phone_col = phone_col
                st.session_state.sending = True
                st.session_state.message_template = message_template
                st.rerun(scope='fragment')
