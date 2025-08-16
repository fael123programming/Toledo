# streamlit_app.py
import os
import io
import json
import re
import tempfile
from pathlib import Path
import streamlit as st

# --- Gemini (SDK oficial nova) ---
# pip install google-genai
from google import genai

# --------------------------
# Config
# --------------------------
GEMINI_MODEL = "gemini-2.0-flash"  # rápido e multimodal
API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets["google_gemini"]["GEMINI_API_KEY"]

if not API_KEY:
    st.error("Config missing: defina GEMINI_API_KEY no ambiente ou em st.secrets.")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.set_page_config(page_title="Analisador REURB (Gemini)", page_icon="🏗️")
st.title("Analisador de Documentos para Regularização Fundiária (REURB)")

st.caption(
    "Envie **PDF/DOCX**. O Gemini irá classificar cada arquivo e sugerir "
    "quais documentos faltam para instruir um procedimento de REURB, com base na legislação."
)

# --------------------------
# Upload
# --------------------------
files = st.file_uploader(
    "Selecione arquivos (PDF ou DOCX)",
    accept_multiple_files=True,
    type=["pdf", "docx"],
)

if not files:
    st.info("Aguardando arquivos…")
    st.stop()

# --------------------------
# Upload para a Files API (48h)
# --------------------------
uploaded = []
progress = st.progress(0, text="Enviando arquivos para a Gemini Files API…")

for i, f in enumerate(files, start=1):
    # Salva em disco temporário para o método upload por caminho (mais robusto)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / f.name
        p.write_bytes(f.getvalue())
        # A API infere MIME pelo sufixo; este caminho é o recomendado nos exemplos oficiais
        up = client.files.upload(file=p)
        uploaded.append(up)
    progress.progress(int(i * 100 / len(files)), text=f"Enviado: {f.name}")

progress.empty()
st.success(f"{len(uploaded)} arquivo(s) enviados com sucesso.")

# --------------------------
# Prompt (instrução ao modelo)
# --------------------------
SYSTEM_PROMPT = f"""
Você é um assistente jurídico especializado em Regularização Fundiária no Brasil.
Considere principalmente a Lei 13.465/2017 e o Decreto 9.310/2018 (REURB).
Tarefa:
1) Para CADA arquivo enviado, identificar o tipo de documento (ex.: RG, CPF, certidão, contrato, escritura,
   matrícula, IPTU, carnê, planta, memorial descritivo, ART/RRT, projeto urbanístico, Requerimento dos legitimados,
   Termo de Compromisso, lista/qualificação de ocupantes, CRF, etc.), com confiança 0–1.
2) Extrair campos-chave úteis (ex.: nome, CPF/CNPJ, endereço, matrícula e cartório, datas, nº do processo, município).
3) Dizer se é RELEVANTE para um processo padrão de REURB e por quê.
4) Com base no conjunto total, sugerir a MODALIDADE PROVÁVEL (REURB-S, REURB-E ou indeterminada) e
   LISTAR DOCUMENTOS PROVAVELMENTE FALTANTES para instruir um processo administrativo típico de REURB,
   com PRIORIDADE (alta/média/baixa) e, quando possível, a BASE LEGAL sucinta (art./§),
   lembrando: Lei 13.465/2017 e Decreto 9.310/2018.
5) Responda ESTRITAMENTE em JSON no schema:

{{
  "files": [
    {{
      "file_name": "string",
      "detected_type": "string",
      "confidence": 0.0,
      "relevant_for_reurb": true,
      "key_fields": {{}},
      "notes": "string"
    }}
  ],
  "likely_modality": "REURB-S" | "REURB-E" | null,
  "missing_documents": [
    {{
      "name": "string",
      "why_needed": "string",
      "legal_basis": "string|null",
      "priority": "alta" | "média" | "baixa"
    }}
  ]
}}

Regras:
- Se algo não puder ser afirmado, use null ou explique em "notes".
- Não escreva comentários fora do JSON.
"""

# --------------------------
# Chamada ao modelo
# --------------------------
with st.spinner("Analisando com Gemini…"):
    # A Files API permite passar os arquivos diretamente como partes de conteúdo
    contents = []
    contents.extend(uploaded)        # todos os arquivos
    contents.append("\n\n" + SYSTEM_PROMPT)  # instruções

    result = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
    )

# --------------------------
# Parse robusto do JSON
# --------------------------
def extract_json(text: str):
    # remove cercas ```json … ```
    m = re.search(r"```json(.*?)```", text, flags=re.S)
    if m:
        return json.loads(m.group(1))
    # tenta pegar o primeiro bloco JSON "nu"
    m2 = re.search(r"\{.*\}\s*\Z", text, flags=re.S)
    if m2:
        return json.loads(m2.group(0))
    # por fim, tenta parse direto
    return json.loads(text)

raw_text = getattr(result, "text", "") or getattr(result, "output_text", "")
try:
    payload = extract_json(raw_text)
except Exception as e:
    st.error("Falha ao interpretar o JSON retornado pelo modelo.")
    st.code(raw_text)
    st.stop()

st.subheader("Resultado")
st.json(payload)

st.caption(
    "⚠️ Esta análise é assistiva e não substitui parecer jurídico. "
    "Verifique normas locais e exigências específicas do município e do Registro de Imóveis."
)