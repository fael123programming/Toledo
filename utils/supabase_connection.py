from st_supabase_connection import SupabaseConnection
import streamlit as st
import supabase
import time


@st.cache_resource
def init_supabase_connection():
    max_retries = 3
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
            supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
            if not supabase_url or not supabase_key:
                st.error("Variáveis SUPABASE_URL e SUPABASE_KEY não configuradas")
                return None
            try:
                sb = SupabaseConnection(
                    connection_name="supabase",
                    url=supabase_url,
                    key=supabase_key
                )
                sb.client.table('_test').select('*').limit(1).execute()
                return sb
            except:
                sb = supabase.create_client(supabase_url, supabase_key)
                return sb
        except Exception as e:
            st.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"Falha na conexão após {max_retries} tentativas")
                return None