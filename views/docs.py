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
from google import genai
from google.genai import types

# -----------------------------
# Configuração inicial
# -----------------------------
st.set_page_config(page_title="REURB — Analisador Gemini", page_icon="🏗️", layout="wide")
st.title("🏗️ REURB — Analisador de Documentos com Gemini")

# Configuração da API key com tratamento de erro melhorado
try:
    API_KEY = os.getenv("GEMINI_API_KEY")
    if not API_KEY and "google_gemini" in st.secrets:
        API_KEY = st.secrets["google_gemini"]["GEMINI_API_KEY"]
    
    if not API_KEY:
        st.error("⚠️ Defina GEMINI_API_KEY no ambiente ou em st.secrets para continuar.")
        st.info("Para obter uma API key, acesse: https://makersuite.google.com/app/apikey")
        st.stop()
except Exception as e:
    st.error(f"Erro ao configurar API key: {str(e)}")
    st.stop()

# Inicializar cliente Gemini
try:
    client = genai.Client(api_key=API_KEY)
    GEMINI_MODEL = "gemini-2.0-flash-exp"  # Modelo mais atualizado
except Exception as e:
    st.error(f"Erro ao inicializar cliente Gemini: {str(e)}")
    st.stop()

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

Responda ESTRITAMENTE em JSON válido seguindo este schema:

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
  "likely_modality": "REURB-S" ou "REURB-E" ou null,
  "missing_documents": [
    {
      "name": "string",
      "why_needed": "string", 
      "legal_basis": "string ou null",
      "priority": "alta" ou "média" ou "baixa"
    }
  ]
}

Regras importantes:
- Se algo não puder ser determinado, use null ou explique em "notes"
- Não escreva nada além do JSON válido
- Use apenas os valores exatos especificados para enums (REURB-S, REURB-E, alta, média, baixa)
"""

# -----------------------------
# Utilitários
# -----------------------------
def _resp_to_text(resp) -> str:
    """Extrai texto da resposta do Gemini com múltiplas tentativas."""
    # Primeira tentativa: atributos diretos
    text = getattr(resp, "text", None)
    if text:
        return text.strip()
    
    # Segunda tentativa: candidates
    if hasattr(resp, "candidates") and resp.candidates:
        for candidate in resp.candidates:
            if hasattr(candidate, "content") and candidate.content:
                parts = getattr(candidate.content, "parts", [])
                text_parts = []
                for part in parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return "\n".join(text_parts).strip()
    
    # Verificar bloqueios
    if hasattr(resp, "prompt_feedback"):
        pf = resp.prompt_feedback
        if hasattr(pf, "block_reason") and pf.block_reason:
            raise RuntimeError(f"Conteúdo bloqueado pelo modelo: {pf.block_reason}")
    
    raise ValueError("Modelo não retornou texto válido para análise.")

def _extract_json(text: str) -> dict:
    """
    Parser tolerante para JSON com múltiplas estratégias.
    """
    if not text or not text.strip():
        raise ValueError("Resposta vazia do modelo.")

    text = text.strip()
    
    # Estratégia 1: Bloco de código JSON
    json_match = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError as e:
            st.warning(f"Erro ao parsear JSON do bloco de código: {e}")
    
    # Estratégia 2: Buscar primeiro objeto JSON completo
    brace_count = 0
    start_idx = -1
    
    for i, char in enumerate(text):
        if char == '{':
            if start_idx == -1:
                start_idx = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                try:
                    return json.loads(text[start_idx:i+1])
                except json.JSONDecodeError:
                    continue
    
    # Estratégia 3: Tentativa direta
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Não foi possível extrair JSON válido da resposta. Erro: {e}\n\nTexto recebido: {text[:500]}...")

# Schema corrigido para o Gemini
REURB_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    required=["files", "missing_documents"],
    properties={
        "files": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                required=[
                    "file_name", "detected_type", "confidence",
                    "relevant_for_reurb", "key_fields", "notes"
                ],
                properties={
                    "file_name": types.Schema(type=types.Type.STRING),
                    "detected_type": types.Schema(type=types.Type.STRING),
                    "confidence": types.Schema(type=types.Type.NUMBER),
                    "relevant_for_reurb": types.Schema(type=types.Type.BOOLEAN),
                    "key_fields": types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "nome": types.Schema(type=types.Type.STRING),
                            "cpf": types.Schema(type=types.Type.STRING),
                            "cnpj": types.Schema(type=types.Type.STRING),
                            "endereco": types.Schema(type=types.Type.STRING),
                            "matricula": types.Schema(type=types.Type.STRING),
                            "cartorio": types.Schema(type=types.Type.STRING),
                            "data": types.Schema(type=types.Type.STRING),
                            "numero_processo": types.Schema(type=types.Type.STRING),
                            "municipio": types.Schema(type=types.Type.STRING),
                            "area": types.Schema(type=types.Type.STRING),
                            "valor": types.Schema(type=types.Type.STRING),
                        },
                        additionalProperties=True
                    ),
                    "notes": types.Schema(type=types.Type.STRING),
                },
            ),
        ),
        "likely_modality": types.Schema(type=types.Type.STRING),
        "missing_documents": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                required=["name", "why_needed", "priority"],
                properties={
                    "name": types.Schema(type=types.Type.STRING),
                    "why_needed": types.Schema(type=types.Type.STRING),
                    "legal_basis": types.Schema(type=types.Type.STRING),
                    "priority": types.Schema(type=types.Type.STRING),
                },
            ),
        ),
    },
)

def _get_mime_type(filename: str) -> str:
    """Determina o MIME type baseado na extensão do arquivo."""
    ext = Path(filename).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
    }
    return mime_types.get(ext, 'application/octet-stream')

def _upload_files_to_gemini(uploaded_files) -> List[Any]:
    """Upload de arquivos para a Files API do Gemini com tratamento de erros."""
    refs = []
    progress_bar = st.progress(0, text="Enviando arquivos para o Gemini...")
    
    try:
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                mime_type = _get_mime_type(uploaded_file.name)
                st.info(f"Processando {uploaded_file.name} (MIME: {mime_type})")
                
                # Criar arquivo temporário
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir) / uploaded_file.name
                    temp_path.write_bytes(uploaded_file.getvalue())
                    
                    # Método baseado na documentação oficial do google-genai
                    try:
                        # Usar apenas argumentos nomeados conforme documentação
                        file_ref = client.files.upload(
                            path=str(temp_path)
                        )
                        st.success(f"✅ Upload realizado com sucesso: {uploaded_file.name}")
                        
                    except Exception as e1:
                        st.warning(f"Método 1 falhou: {e1}")
                        
                        # Método alternativo: usando o objeto pathlib.Path
                        try:
                            file_ref = client.files.upload(path=temp_path)
                            st.success(f"✅ Upload realizado (método 2): {uploaded_file.name}")
                            
                        except Exception as e2:
                            st.warning(f"Método 2 falhou: {e2}")
                            
                            # Método 3: forçar mime_type
                            try:
                                # Usar a API mais básica possível
                                import google.genai as genai_alt
                                genai_alt.configure(api_key=API_KEY)
                                file_ref = genai_alt.upload_file(str(temp_path))
                                st.success(f"✅ Upload realizado (método 3): {uploaded_file.name}")
                                
                            except Exception as e3:
                                st.error(f"Método 3 também falhou: {e3}")
                                
                                # Última tentativa: importação alternativa
                                try:
                                    import google.generativeai as genai_old
                                    genai_old.configure(api_key=API_KEY)
                                    file_ref = genai_old.upload_file(str(temp_path))
                                    st.success(f"✅ Upload realizado (método legacy): {uploaded_file.name}")
                                    
                                except Exception as e4:
                                    st.error(f"Todos os métodos falharam para {uploaded_file.name}")
                                    st.error(f"Erros: {e1}, {e2}, {e3}, {e4}")
                                    
                                    # Debug: mostrar a versão da biblioteca
                                    try:
                                        import google.genai
                                        st.info(f"Versão google-genai: {google.genai.__version__}")
                                    except:
                                        st.info("Não foi possível determinar a versão da biblioteca")
                                    
                                    raise Exception(f"Falha em todos os métodos de upload para {uploaded_file.name}")
                
                refs.append(file_ref)
                
                progress_bar.progress(
                    (i + 1) / len(uploaded_files), 
                    text=f"✅ {uploaded_file.name} ({i+1}/{len(uploaded_files)})"
                )
                
            except Exception as e:
                st.error(f"Erro fatal ao enviar {uploaded_file.name}: {str(e)}")
                progress_bar.empty()
                raise
        
        progress_bar.empty()
        st.success(f"🎉 {len(refs)} arquivo(s) enviado(s) com sucesso!")
        return refs
        
    except Exception as e:
        progress_bar.empty()
        st.error(f"Erro durante upload: {str(e)}")
        raise

def _call_gemini(files_refs) -> dict:
    """
    Chamada ao modelo Gemini com configuração robusta.
    """
    user_prompt = "Analise os documentos enviados conforme as instruções do sistema e retorne apenas o JSON estruturado solicitado."
    
    try:
        # Primeira tentativa: com schema completo
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[user_prompt] + files_refs,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=REURB_SCHEMA,
                temperature=0.1,
                max_output_tokens=4096,
            ),
        )
        
        text = _resp_to_text(response)
        return _extract_json(text)
        
    except Exception as e:
        st.warning(f"Schema restritivo falhou: {str(e)}. Tentando sem schema...")
        
        # Segunda tentativa: apenas JSON sem schema
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[user_prompt] + files_refs,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
            )
            
            text = _resp_to_text(response)
            return _extract_json(text)
            
        except Exception as e2:
            st.warning(f"JSON sem schema falhou: {str(e2)}. Tentando texto livre...")
            
            # Terceira tentativa: texto livre
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[user_prompt] + files_refs,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                        max_output_tokens=4096,
                    ),
                )
                
                text = _resp_to_text(response)
                return _extract_json(text)
                
            except Exception as e3:
                st.error(f"Todas as tentativas falharam. Último erro: {str(e3)}")
                raise e3

def _build_dashboard(payload: Dict[str, Any]):
    """Constrói o dashboard de análise."""
    files = payload.get("files", [])
    missing = payload.get("missing_documents", [])
    likely_modality = payload.get("likely_modality")

    # Métricas principais
    total_files = len(files)
    relevant_files = sum(1 for f in files if f.get("relevant_for_reurb", False))
    
    st.subheader("📊 Resumo da Análise")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Arquivos analisados", total_files)
    with col2:
        st.metric("Relevantes p/ REURB", relevant_files)
    with col3:
        st.metric("Não relevantes", total_files - relevant_files)
    with col4:
        st.metric("Documentos faltantes", len(missing))

    # Distribuição por tipo
    if files:
        type_counts = Counter([f.get("detected_type", "Indefinido") for f in files])
        type_df = pd.DataFrame({
            "Tipo": list(type_counts.keys()), 
            "Quantidade": list(type_counts.values())
        }).sort_values("Quantidade", ascending=False)
        
        st.subheader("📈 Distribuição por Tipo de Documento")
        st.bar_chart(type_df.set_index("Tipo"))

    # Tabs organizadas
    tab_files, tab_missing, tab_summary, tab_raw = st.tabs([
        "📄 Arquivos Analisados", 
        "📋 Documentos Faltantes", 
        "📝 Resumo Executivo",
        "🔧 Dados Brutos"
    ])

    # Tab: Arquivos analisados
    with tab_files:
        if not files:
            st.info("Nenhum arquivo foi analisado.")
        else:
            df = pd.DataFrame(files)
            
            # Preparação dos dados para exibição
            df["confidence_pct"] = (df.get("confidence", 0.0) * 100).round(1)
            df["relevante"] = df.get("relevant_for_reurb", False)
            df["tipo"] = df.get("detected_type", "Indefinido")
            df["arquivo"] = df.get("file_name", "Sem nome")
            df["notas"] = df.get("notes", "")

            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                relevance_filter = st.selectbox(
                    "Filtrar por relevância:",
                    ["Todos", "Apenas relevantes", "Apenas não relevantes"]
                )
            with col2:
                available_types = sorted(df["tipo"].unique())
                selected_types = st.multiselect(
                    "Tipos de documento:", 
                    available_types, 
                    default=available_types
                )

            # Aplicar filtros
            filtered_df = df[df["tipo"].isin(selected_types)]
            if relevance_filter == "Apenas relevantes":
                filtered_df = filtered_df[filtered_df["relevante"] == True]
            elif relevance_filter == "Apenas não relevantes":
                filtered_df = filtered_df[filtered_df["relevante"] == False]

            # Exibir tabela
            display_df = filtered_df[["arquivo", "tipo", "confidence_pct", "relevante", "notas"]].copy()
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "arquivo": st.column_config.TextColumn("Arquivo"),
                    "tipo": st.column_config.TextColumn("Tipo"),
                    "confidence_pct": st.column_config.ProgressColumn(
                        "Confiança (%)", 
                        min_value=0, 
                        max_value=100,
                        format="%.1f%%"
                    ),
                    "relevante": st.column_config.CheckboxColumn("Relevante"),
                    "notas": st.column_config.TextColumn("Observações"),
                }
            )

            # Campos extraídos
            if st.expander("🔍 Ver campos extraídos por arquivo"):
                for _, row in filtered_df.iterrows():
                    key_fields = row.get("key_fields", {})
                    if key_fields:
                        st.subheader(row["arquivo"])
                        st.json(key_fields)

    # Tab: Documentos faltantes
    with tab_missing:
        if likely_modality:
            st.info(f"**Modalidade provável:** {likely_modality}")
        
        if not missing:
            st.success("✅ Nenhum documento faltante identificado pelo modelo.")
        else:
            st.subheader(f"📋 {len(missing)} documento(s) faltante(s) identificado(s)")
            
            missing_df = pd.DataFrame(missing)
            
            # Mapeamento de prioridades com ícones
            priority_mapping = {
                "alta": "🔴 Alta",
                "média": "🟡 Média", 
                "media": "🟡 Média",
                "baixa": "🟢 Baixa"
            }
            
            missing_df["priority_display"] = missing_df.get("priority", "").str.lower().map(priority_mapping).fillna("⚪ Indefinida")
            missing_df["legal_basis"] = missing_df.get("legal_basis", "").fillna("N/A")
            
            # Filtro por prioridade
            available_priorities = sorted(missing_df["priority_display"].unique())
            selected_priorities = st.multiselect(
                "Filtrar por prioridade:",
                available_priorities,
                default=available_priorities
            )
            
            filtered_missing = missing_df[missing_df["priority_display"].isin(selected_priorities)]
            
            # Exibir tabela
            display_missing = filtered_missing[[
                "name", "priority_display", "legal_basis", "why_needed"
            ]].rename(columns={
                "name": "Documento",
                "priority_display": "Prioridade", 
                "legal_basis": "Base Legal",
                "why_needed": "Justificativa"
            })
            
            st.dataframe(
                display_missing,
                use_container_width=True,
                hide_index=True
            )

    # Tab: Resumo executivo
    with tab_summary:
        st.subheader("📝 Resumo Executivo")
        
        # Status geral
        if likely_modality:
            st.success(f"**Modalidade REURB identificada:** {likely_modality}")
        else:
            st.warning("**Modalidade REURB:** Indeterminada com base nos documentos enviados")
        
        # Análise de completude
        completeness = (relevant_files / max(total_files, 1)) * 100
        if completeness >= 80:
            st.success(f"**Completude documental:** {completeness:.1f}% - Boa cobertura")
        elif completeness >= 60:
            st.warning(f"**Completude documental:** {completeness:.1f}% - Cobertura adequada")
        else:
            st.error(f"**Completude documental:** {completeness:.1f}% - Documentação insuficiente")
        
        # Próximos passos
        st.subheader("🎯 Próximos Passos Recomendados")
        if missing:
            high_priority = [doc for doc in missing if doc.get("priority", "").lower() == "alta"]
            if high_priority:
                st.error(f"**Urgente:** {len(high_priority)} documento(s) de alta prioridade faltando")
                for doc in high_priority:
                    st.write(f"• **{doc['name']}**: {doc['why_needed']}")
        else:
            st.success("**Documentação aparenta estar completa** para prosseguir com o processo REURB")

    # Tab: Dados brutos
    with tab_raw:
        st.subheader("🔧 JSON Bruto da Análise")
        st.json(payload, expanded=False)
        
        # Download do JSON
        json_str = json.dumps(payload, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Baixar análise completa (JSON)",
            data=json_str.encode("utf-8"),
            file_name="reurb_analise_completa.json",
            mime="application/json"
        )

# -----------------------------
# Interface Principal
# -----------------------------
st.markdown("---")
st.subheader("📤 Upload de Documentos")

st.info(
    "📋 **Tipos suportados:** PDF e DOCX  \n"
    "🔐 **Privacidade:** Arquivos são enviados temporariamente para análise e não são armazenados permanentemente  \n"
    "⚡ **Processamento:** Análise automatizada via IA especializada em REURB"
)

uploaded_files = st.file_uploader(
    "Selecione os documentos para análise:",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    help="Envie documentos relacionados ao processo REURB (RG, CPF, escrituras, plantas, etc.)"
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} arquivo(s) carregado(s)")
    
    # Mostrar lista de arquivos
    with st.expander("📁 Arquivos carregados"):
        for i, file in enumerate(uploaded_files, 1):
            file_size = len(file.getvalue()) / 1024  # KB
            st.write(f"{i}. **{file.name}** ({file_size:.1f} KB)")
    
    # Botão de análise
    if st.button("🚀 Iniciar Análise", type="primary", use_container_width=True):
        try:
            # Upload para Gemini
            with st.status("📤 Enviando arquivos para análise...", expanded=True) as status:
                file_refs = _upload_files_to_gemini(uploaded_files)
                status.update(label="✅ Upload concluído", state="complete")
            
            # Análise
            with st.status("🧠 Analisando documentos com IA...", expanded=True) as status:
                analysis_result = _call_gemini(file_refs)
                status.update(label="✅ Análise concluída", state="complete")
            
            # Salvar na sessão e exibir
            st.session_state["reurb_analysis"] = analysis_result
            st.success("🎉 Análise concluída com sucesso! Veja os resultados abaixo.")
            st.balloons()
            
        except Exception as e:
            st.error("❌ Erro durante a análise:")
            st.exception(e)

else:
    st.info("⬆️ Faça upload dos documentos para começar a análise")

# Exibir dashboard se houver análise
if "reurb_analysis" in st.session_state:
    st.markdown("---")
    _build_dashboard(st.session_state["reurb_analysis"])

# Rodapé
st.markdown("---")
st.caption(
    "🏗️ **REURB Analyzer** - Ferramenta de análise documental para Regularização Fundiária Urbana  \n"
    "⚖️ Base legal: Lei 13.465/2017 e Decreto 9.310/2018  \n"
    "🤖 Powered by Google Gemini AI"
)