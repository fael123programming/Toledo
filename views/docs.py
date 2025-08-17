# app_reurb_gemini.py
# Requisitos:
#   pip install streamlit google-genai pandas
# Execução:
#   export GEMINI_API_KEY="sua_chave"
#   streamlit run app_reurb_gemini.py

import os
import re
import json
import tempfile
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Optional

import pandas as pd
import streamlit as st
from google import genai  # SDK oficial google-genai (Developer API)
from google.genai import types
# -----------------------------
# Configuração inicial
# -----------------------------
st.set_page_config(page_title="REURB — Analisador Gemini", page_icon="🏗️", layout="wide")
st.title("🏗️ REURB — Analisador de Documentos com Gemini")

API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets["google_gemini"]["GEMINI_API_KEY"]
if not API_KEY:
    st.error("Defina GEMINI_API_KEY no ambiente ou em st.secrets para continuar.")
    st.stop()

client = genai.Client(api_key=API_KEY)
GEMINI_MODEL = "gemini-2.0-flash"  # rápido e multimodal

# -----------------------------
# Prompt do modelo (jurídico)
# -----------------------------
SYSTEM_PROMPT = """
Você é um assistente jurídico especializado em Regularização Fundiária Urbana (REURB) no Brasil.
Base normativa: Lei 13.465/2017 e Decreto 9.310/2018.

Tarefas:
1) Para CADA arquivo enviado, identificar o tipo de documento (ex.: RG, CPF, certidão, contrato, escritura,
   matrícula, IPTU, carnê, planta, memorial descritivo, ART/RRT, projeto urbanístico, requerimento, termo
   de compromisso, lista/qualificação de ocupantes, CRF, etc.), com confiança 0–1.
2) Extrair campos-chave úteis (nome, CPF/CNPJ, endereço, matrícula/cartório, datas, nº de processo, município, etc.).
3) Indicar se é RELEVANTE para REURB e por quê.
4) Considerando o conjunto, sugerir a MODALIDADE PROVÁVEL (REURB-S, REURB-E ou indeterminada)
   e LISTAR DOCUMENTOS PROVAVELMENTE FALTANTES, cada um com:
   - prioridade (alta/média/baixa),
   - por que é necessário,
   - base legal sucinta (art./§ da Lei 13.465/2017 ou Decreto 9.310/2018, quando aplicável).
5) Responda **estritamente** em JSON neste schema:

{
  "files": [
    {
      "file_name": "string",
      "detected_type": "string",
      "confidence": 0.0,
      "relevant_for_reurb": true,
      "key_fields": {},
      "notes": "string"
    }
  ],
  "likely_modality": "REURB-S" | "REURB-E" | null,
  "missing_documents": [
    {
      "name": "string",
      "why_needed": "string",
      "legal_basis": "string|null",
      "priority": "alta" | "média" | "baixa"
    }
  ]
}

Regras:
- Se algo não puder ser afirmado, use null ou explique em "notes".
- Não escreva nada fora do JSON.
"""

# -----------------------------
# Utilitários
# -----------------------------
def _resp_to_text(resp) -> str:
    # tenta .output_text ou .text
    text = getattr(resp, "output_text", None) or getattr(resp, "text", None)
    if text:
        return text.strip()

    # concatena candidates[].content.parts[].text
    chunks = []
    for c in getattr(resp, "candidates", []) or []:
        content = getattr(c, "content", None)
        if not content:
            continue
        for p in getattr(content, "parts", []) or []:
            t = getattr(p, "text", None)
            if t:
                chunks.append(t)
    if chunks:
        return "\n".join(chunks).strip()

    pf = getattr(resp, "prompt_feedback", None)
    if pf:
        raise RuntimeError(f"Saída bloqueada pelo modelo (prompt_feedback): {pf}")
    raise ValueError("Modelo não retornou texto para análise.")

# ——————————————————————————————————————————————————————————————
# 2) Parser tolerante para JSON
# ——————————————————————————————————————————————————————————————
def _extract_json(text: str):
    """
    Aceita:
      - JSON puro
      - bloco entre ```json ... ```
      - pega o primeiro { ... } até o último } (heurística)
    Lança erro detalhado em caso de falha.
    """
    if not text or not text.strip():
        raise ValueError("Resposta vazia do modelo (string em branco).")

    s = text.strip()

    # cercas ```json
    m = re.search(r"```json\s*(.*?)\s*```", s, flags=re.S | re.I)
    if m:
        return json.loads(m.group(1))

    # captura do primeiro bloco JSON "nu"
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = s[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass  # tenta por último o loads direto

    # tentativa direta
    return json.loads(s)

# ——————————————————————————————————————————————————————————————
# 3) Chamada ao Gemini forçando JSON puro
# ——————————————————————————————————————————————————————————————
# REURB_SCHEMA: use os tipos do SDK (STRING, NUMBER, BOOLEAN, OBJECT, ARRAY)
REURB_SCHEMA = {
    "type": "OBJECT",
    "required": ["files", "missing_documents"],
    "properties": {
        "files": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": [
                    "file_name", "detected_type", "confidence",
                    "relevant_for_reurb", "key_fields", "notes"
                ],
                "properties": {
                    "file_name": {"type": "STRING"},
                    "detected_type": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                    "relevant_for_reurb": {"type": "BOOLEAN"},
                    "key_fields": {"type": "OBJECT"},
                    "notes": {"type": "STRING"},
                },
            },
        },
        # não há "nullable" no schema; trate null na aplicação
        "likely_modality": {"type": "STRING"},
        "missing_documents": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["name", "why_needed", "priority"],
                "properties": {
                    "name": {"type": "STRING"},
                    "why_needed": {"type": "STRING"},
                    "legal_basis": {"type": "STRING"},
                    "priority": {"type": "STRING"},
                },
            },
        },
    },
}


def _upload_files_to_gemini(uploaded_files) -> List[Any]:
    """Faz upload de cada arquivo (PDF/DOCX) para a Files API e retorna os handles."""
    refs = []
    pb = st.progress(0, text="Enviando arquivos para o Gemini (Files API)…")
    for i, f in enumerate(uploaded_files, start=1):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / f.name
            p.write_bytes(f.getvalue())
            up = client.files.upload(file=p)  # Files API (armazenamento temporário)
            refs.append(up)
        pb.progress(int(i * 100 / len(uploaded_files)), text=f"Enviado: {f.name}")
    pb.empty()
    return refs

def _call_gemini(files_refs) -> dict:
    """
    Chama o modelo com Files API + system_instruction via config,
    e força retorno em JSON usando response_schema.
    """
    # Dica: inclua um prompt curto no contents (além do system_instruction) para “ancorar” a intenção do usuário
    user_prompt = "Analise os arquivos conforme as instruções do sistema e retorne SOMENTE o JSON solicitado."

    resp = client.models.generate_content(
        model=GEMINI_MODEL,  # ex.: "gemini-2.0-flash" / "gemini-2.5-flash"
        contents=[user_prompt, *files_refs],  # texto + arquivos (padrão do SDK)
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,                 # << aqui é o lugar certo
            response_mime_type="application/json",           # força JSON puro
            response_schema=REURB_SCHEMA,                    # estrutura esperada
            temperature=0,                                   # (opcional) deixar mais determinístico
            max_output_tokens=2048,                          # (opcional) se a saída for longa
        ),
    )

    text = _resp_to_text(resp)      # seu helper de extração continua valendo
    return _extract_json(text) 

def _build_dashboard(payload: Dict[str, Any]):
    """Monta o dashboard completo a partir do JSON."""
    files = payload.get("files", []) or []
    missing = payload.get("missing_documents", []) or []
    likely_modality = payload.get("likely_modality")

    # Status/feedback do carregamento (UI)
    with st.status("Carregando análise…", expanded=False) as s:  # st.status para feedback :contentReference[oaicite:2]{index=2}
        s.update(label="Análise carregada", state="complete", expanded=False)

    # ---------------- KPIs ----------------
    total_files = len(files)
    relevant_files = sum(1 for f in files if f.get("relevant_for_reurb"))
    st.subheader("Resumo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Arquivos recebidos", total_files)
    c2.metric("Relevantes p/ REURB", relevant_files)
    c3.metric("Não relevantes", total_files - relevant_files)
    c4.metric("Documentos faltantes", len(missing))

    # Distribuição por tipo
    type_counts = Counter([(f.get("detected_type") or "—") for f in files])
    if type_counts:
        type_df = pd.DataFrame(
            {"Tipo": list(type_counts.keys()), "Quantidade": list(type_counts.values())}
        ).set_index("Tipo")
        st.bar_chart(type_df)

    # Abas
    tab_files, tab_missing, tab_raw = st.tabs(
        ["📄 Arquivos analisados", "✅ Checklist de faltantes", "🧾 JSON bruto"]
    )

    # --------- Arquivos analisados ----------
    with tab_files:
        st.subheader("Arquivos analisados")
        df = pd.DataFrame(files)
        if df.empty:
            st.info("Sem arquivos para exibir.")
        else:
            df["confidence_pct"] = (df.get("confidence", 0.0).fillna(0.0) * 100).round(0)
            df["relevante"] = df.get("relevant_for_reurb", False).fillna(False)
            df["tipo"] = df.get("detected_type").fillna("—")
            df["arquivo"] = df.get("file_name").fillna("—")
            df["notas"] = df.get("notes").fillna("")
            key_fields_text = df.get("key_fields").apply(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else ""
            ).fillna("")

            # Filtros
            f1, f2, f3 = st.columns([1, 1, 2])
            with f1:
                filtro_relev = st.selectbox(
                    "Filtrar por relevância", ["Todos", "Apenas relevantes", "Apenas não relevantes"]
                )
            with f2:
                tipos = sorted(df["tipo"].unique().tolist())
                filtro_tipos = st.multiselect("Tipos", tipos, default=tipos)
            with f3:
                termo = st.text_input("Buscar (arquivo / notas / campos-chave)")

            mask = df["tipo"].isin(filtro_tipos)
            if filtro_relev == "Apenas relevantes":
                mask &= df["relevante"] == True
            elif filtro_relev == "Apenas não relevantes":
                mask &= df["relevante"] == False
            if termo.strip():
                t = termo.lower()
                mask &= (
                    df["arquivo"].str.lower().str.contains(t)
                    | df["notas"].str.lower().str.contains(t)
                    | key_fields_text.str.lower().str.contains(t)
                )

            view = df.loc[mask, ["arquivo", "tipo", "confidence_pct", "relevante", "notas"]].reset_index(drop=True)

            # Tabela com barra de progresso de confiança (ProgressColumn) :contentReference[oaicite:3]{index=3}
            st.dataframe(
                view,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "arquivo": st.column_config.TextColumn("Arquivo"),
                    "tipo": st.column_config.TextColumn("Tipo detectado"),
                    "confidence_pct": st.column_config.ProgressColumn(
                        "Confiança (%)", min_value=0, max_value=100, format="%d%%"
                    ),
                    "relevante": st.column_config.CheckboxColumn("Relevante p/ REURB"),
                    "notas": st.column_config.TextColumn("Notas"),
                },
            )

            # Expanders com key_fields
            with st.expander("Ver campos-chave extraídos (por arquivo)"):
                for row in df.loc[mask].to_dict(orient="records"):
                    kf = row.get("key_fields") or {}
                    if not kf:
                        continue
                    with st.expander(f"{row.get('file_name', 'Arquivo')}"):
                        st.json(kf)

            # Export
            st.download_button(
                "Baixar CSV (arquivos filtrados)",
                data=view.to_csv(index=False).encode("utf-8"),
                file_name="reurb_arquivos.csv",
                mime="text/csv",
            )  # st.download_button para exportar :contentReference[oaicite:4]{index=4}

    # --------- Checklist faltantes ----------
    with tab_missing:
        st.subheader("Checklist de documentos faltantes")
        if likely_modality:
            st.markdown(f"**Modalidade provável:** `{likely_modality}`")
        else:
            st.markdown("**Modalidade provável:** `Indeterminada`")

        if not missing:
            st.success("Nenhum documento faltante listado pelo modelo.")
        else:
            miss_df = pd.DataFrame(missing)
            miss_df["priority"] = (
                miss_df.get("priority", "")
                .fillna("")
                .str.lower()
                .map({"alta": "Alta 🔴", "média": "Média 🟡", "media": "Média 🟡", "baixa": "Baixa 🟢"})
                .fillna("—")
            )
            miss_df["legal_basis"] = miss_df.get("legal_basis").fillna("—")
            miss_df.rename(
                columns={
                    "name": "Documento",
                    "why_needed": "Por que necessário",
                    "legal_basis": "Base legal",
                    "priority": "Prioridade",
                },
                inplace=True,
            )

            prioridades = ["Alta 🔴", "Média 🟡", "Baixa 🟢", "—"]
            sel_prior = st.multiselect("Prioridades", prioridades, default=prioridades[:-1])
            miss_view = miss_df[miss_df["Prioridade"].isin(sel_prior)]

            st.dataframe(
                miss_view[["Documento", "Prioridade", "Base legal", "Por que necessário"]],
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Baixar JSON (faltantes filtrados)",
                data=miss_view.to_json(orient="records", force_ascii=False).encode("utf-8"),
                file_name="reurb_faltantes.json",
                mime="application/json",
            )
            st.download_button(
                "Baixar CSV (faltantes filtrados)",
                data=miss_view.to_csv(index=False).encode("utf-8"),
                file_name="reurb_faltantes.csv",
                mime="text/csv",
            )

    # --------- JSON bruto ----------
    with tab_raw:
        st.subheader("JSON bruto")
        st.json(payload, expanded=False)

# -----------------------------
# UI principal — Upload & Ação
# -----------------------------
st.caption(
    "Envie **PDF/DOCX**. Os arquivos são enviados à Files API do Gemini para análise multimodal "
    "(armazenamento temporário)."
)

uploaded_files = st.file_uploader(
    "Selecione arquivos PDF/DOCX",
    type=["pdf", "docx"],                # restrição de tipos (Streamlit) :contentReference[oaicite:5]{index=5}
    accept_multiple_files=True,
)

ready_to_analyze = bool(uploaded_files)
if not ready_to_analyze:
    st.info("Aguardando arquivos…")
else:
    # Botão para disparar a análise
    if st.button("Analisar no Gemini", type="primary"):
        # 1) Upload dos arquivos
        with st.status("1/2 — Enviando arquivos…", expanded=False) as s1:
            refs = _upload_files_to_gemini(uploaded_files)
            s1.update(label="Upload concluído", state="complete")

        # 2) Chamada ao modelo
        with st.status("2/2 — Gerando análise com Gemini…", expanded=False) as s2:
            try:
                payload = _call_gemini(refs)  # generate_content + parse JSON
            except Exception as e:
                st.error("Falha ao obter/interpretar a resposta do modelo.")
                st.exception(e)
                st.stop()
            s2.update(label="Análise concluída", state="complete")

        # 3) Persistir e renderizar dashboard
        st.session_state["gemini_payload"] = payload
        st.success("Análise pronta. Veja o dashboard abaixo 👇")

# Renderiza dashboard se já houver payload na sessão (ou recém-gerado)
if "gemini_payload" in st.session_state:
    _build_dashboard(st.session_state["gemini_payload"])
