import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import io
import csv
import time
import unicodedata
from typing import List, Dict, Tuple

# Tenta carregar as configurações do arquivo config.py
try:
    from config import GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH, GOOGLE_DRIVE_FOLDER_ID, GEMINI_API_KEY
except ImportError:
    st.error("Erro: Arquivo config.py não encontrado. Certifique-se de que ele existe e está configurado corretamente.")
    st.stop()

# --- Configuração da Gemini API ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Erro ao configurar a Gemini API. Verifique sua API Key. Detalhes: {e}")
    st.stop()

# --- Funções de Acesso ao Google Drive/Sheets ---
@st.cache_resource
def get_google_apis_services():
    """Autentica com as APIs do Google usando a conta de serviço."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH,
            scopes=['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return sheets_service, drive_service
    except Exception as e:
        st.error(f"Erro de autenticação com o Google. Verifique o caminho do arquivo 'service_account.json' e se a API está habilitada. Detalhes: {e}")
        st.stop()
        return None, None

def _normalize_colname(name: str) -> str:
    text = str(name).strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    for ch in ['/', '\\', '-', '.', ',', ';', ':', '(', ')', '[', ']', '{', '}', '  ']:
        text = text.replace(ch, ' ')
    text = '_'.join(text.split())
    return text

def _standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    # Renomeia colunas para formato normalizado
    df = df.rename(columns={c: _normalize_colname(c) for c in df.columns})
    # Mapeia sinônimos para nomes canônicos
    alias_map = {
        'data': {'data', 'date', 'dt'},
        'quantidade': {'quantidade', 'qtd', 'quant', 'qte'},
        'preco_unitario': {'preco_unitario', 'preco', 'preco_unit', 'valor_unitario', 'preco_unitário', 'preco_venda'},
        'receita_total': {'receita_total', 'receita', 'faturamento', 'valor_total', 'total'},
        'produto': {'produto', 'item', 'sku', 'descricao', 'descricao_produto'},
        'regiao': {'regiao', 'regiao_venda', 'regiao_geografica', 'regiao_', 'regioes', 'regional', 'regiao_cliente'}
    }
    current = set(df.columns)
    for canon, alts in alias_map.items():
        found = [c for c in current if c in alts]
        if found and canon not in df.columns:
            df = df.rename(columns={found[0]: canon})
    return df

def _clean_numeric_series(s: pd.Series) -> pd.Series:
    # Remove separadores de milhar comuns e padroniza decimal para ponto
    return pd.to_numeric(
        s.astype(str)
         .str.replace('\u00A0', '', regex=False)  # NBSP
         .str.replace(' ', '', regex=False)
         .str.replace('.', '', regex=False)
         .str.replace(',', '.', regex=False),
        errors='coerce'
    )

def _prepare_analysis_payload(df: pd.DataFrame, max_rows: int = 1000) -> Tuple[str, str]:
    """Retorna (resumo_textual, csv_amostra) para enviar ao LLM."""
    parts = []
    # KPIs básicos
    total_linhas = len(df)
    parts.append(f"Linhas totais: {total_linhas}")

    if 'data' in df.columns:
        try:
            min_dt = df['data'].min()
            max_dt = df['data'].max()
            if pd.notna(min_dt) and pd.notna(max_dt):
                parts.append(f"Período: {min_dt.date()} a {max_dt.date()}")
        except Exception:
            pass

    # Receita
    receita_col = None
    if 'receita_total' in df.columns:
        receita_col = 'receita_total'
    elif {'quantidade', 'preco_unitario'}.issubset(df.columns):
        df['receita_total_calc'] = df['quantidade'] * df['preco_unitario']
        receita_col = 'receita_total_calc'
    if receita_col:
        receita_sum = df[receita_col].sum(skipna=True)
        parts.append(f"Receita total (estimada): {receita_sum:.2f}")

    # Agregações por mês, produto e região (se existirem)
    try:
        if 'data' in df.columns:
            by_month = (
                df.dropna(subset=['data'])
                  .assign(mes=lambda x: x['data'].dt.to_period('M').astype(str))
            )
            agg_cols = [c for c in ['quantidade', 'preco_unitario', 'receita_total'] if c in by_month.columns]
            if 'receita_total' not in agg_cols and {'quantidade','preco_unitario'}.issubset(by_month.columns):
                by_month['receita_total'] = by_month['quantidade'] * by_month['preco_unitario']
                agg_cols = list(set(agg_cols + ['receita_total']))
            if agg_cols:
                g = by_month.groupby('mes')[agg_cols].sum(numeric_only=True).reset_index().head(24)
                parts.append("Receita por mês (até 24 períodos):\n" + g.to_csv(index=False))
    except Exception:
        pass

    try:
        if 'produto' in df.columns:
            gprod = (
                df.groupby('produto')[['quantidade']].sum(numeric_only=True).sort_values(by='quantidade', ascending=False).head(10)
            )
            parts.append("Top 10 produtos por quantidade:\n" + gprod.to_csv())
    except Exception:
        pass

    try:
        if 'regiao' in df.columns:
            greg = (
                df.groupby('regiao')[['quantidade']].sum(numeric_only=True).sort_values(by='quantidade', ascending=False).head(10)
            )
            parts.append("Top 10 regiões por quantidade:\n" + greg.to_csv())
    except Exception:
        pass

    resumo = "\n\n".join(parts)
    # Amostra
    sample_df = df.head(max_rows)
    return resumo, sample_df.to_csv(index=False)


@st.cache_data(ttl=3600) # Cache de dados por 1 hora
def load_sales_data(_drive_folder_id):
    """Carrega e consolida dados de vendas de múltiplas planilhas do Google Drive.
    Retorna: (df_consolidado, lista_arquivos, stats)
    lista_arquivos: List[Dict[name,id,mimeType,linhas]]
    stats: {file_count, row_count, load_seconds}
    """
    sheets_service, drive_service = get_google_apis_services()
    if not sheets_service or not drive_service:
        return pd.DataFrame(), [], {"file_count": 0, "row_count": 0, "load_seconds": 0.0}

    start_ts = time.time()
    all_data = []
    loaded_files: List[Dict[str, str]] = []
    
    with st.spinner("Buscando planilhas na sua pasta do Google Drive..."):
        try:
            query = f"'{_drive_folder_id}' in parents and (mimeType='application/vnd.google-apps.spreadsheet' or mimeType='text/csv')"
            items: List[Dict] = []
            page_token = None
            while True:
                results = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token
                ).execute()
                items.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            if not items:
                st.warning(f"Nenhuma planilha ou arquivo CSV encontrado na pasta do Drive. Verifique o ID da pasta em config.py.")
                return pd.DataFrame(), []

            progress_bar = st.progress(0, text="Iniciando o carregamento dos dados...")
            
            for i, item in enumerate(items):
                file_name = item['name']
                file_id = item['id']
                mime_type = item['mimeType']
                
                progress_bar.progress((i + 1) / len(items), text=f"Lendo arquivo: {file_name}")
                
                try:
                    df = None
                    if mime_type == 'application/vnd.google-apps.spreadsheet':
                        # Lê TODAS as abas (sheets) da planilha e concatena
                        meta = sheets_service.spreadsheets().get(spreadsheetId=file_id, fields='sheets(properties(title))').execute()
                        sheet_titles = [s['properties']['title'] for s in meta.get('sheets', [])]
                        sub_frames = []
                        for title in sheet_titles:
                            try:
                                rng = f"{title}!A1:ZZZ"  # evita truncar colunas
                                result = sheets_service.spreadsheets().values().get(spreadsheetId=file_id, range=rng).execute()
                                values = result.get('values', [])
                                if not values or len(values) < 2:
                                    continue
                                headers = values[0]
                                tmp = pd.DataFrame(values[1:], columns=headers)
                                tmp = _standardize_dataframe(tmp)
                                sub_frames.append(tmp)
                            except Exception:
                                continue
                        if sub_frames:
                            df = pd.concat(sub_frames, ignore_index=True)
                        else:
                            st.info(f"Arquivo '{file_name}' sem dados utilizáveis. Pulado.")
                            df = None
                            
                    elif mime_type == 'text/csv':
                        # --- INÍCIO DA LÓGICA FLEXÍVEL DE LEITURA ---
                        request = drive_service.files().get_media(fileId=file_id)
                        csv_content_bytes = request.execute()
                        
                        detected_delimiter = ',' # Padrão
                        detected_decimal = '.' # Padrão
                        
                        try:
                            # Tenta detectar o formato lendo uma amostra
                            sample_text = csv_content_bytes[:2048].decode('utf-8', errors='ignore')
                            dialect = csv.Sniffer().sniff(sample_text, delimiters=',;')
                            detected_delimiter = dialect.delimiter
                            
                            # Regra de negócio: infere o decimal baseado no delimitador
                            if detected_delimiter == ';':
                                detected_decimal = ','
                            elif detected_delimiter == ',':
                                detected_decimal = '.'
                                
                        except (csv.Error, UnicodeDecodeError):
                            # Se o 'sniff' falhar, apenas assume o padrão (vírgula/ponto)
                            st.info(f"Não foi possível detectar o formato de '{file_name}'. Tentando com delimitador ',' e decimal '.'.")
                            detected_delimiter = ','
                            detected_decimal = '.'

                        # Definir separador de milhar com base no decimal inferido
                        thousands = '.' if detected_decimal == ',' else ','
                        # Rebobina o stream e lê com o pandas usando os parâmetros detectados
                        csv_content = io.BytesIO(csv_content_bytes)
                        df = pd.read_csv(
                            csv_content, 
                            delimiter=detected_delimiter, 
                            decimal=detected_decimal,
                            thousands=thousands
                        )
                        # --- FIM DA LÓGICA FLEXÍVEL ---
                        
                        # Normaliza colunas para verificar presença de 'data'
                        df = _standardize_dataframe(df)
                        if 'data' not in df.columns:
                            st.warning(f"O arquivo CSV '{file_name}' foi lido mas não possui coluna de data reconhecida. Será incluído mesmo assim.")
                    
                    if df is not None:
                        df = _standardize_dataframe(df)
                        # Tratamento de datas e numéricos
                        if 'data' in df.columns:
                            df['data'] = pd.to_datetime(df['data'], dayfirst=True, errors='coerce')
                        for col in ['quantidade', 'preco_unitario', 'receita_total']:
                            if col in df.columns:
                                df[col] = _clean_numeric_series(df[col])
                        all_data.append(df)
                        loaded_files.append({"name": file_name, "id": file_id, "mimeType": mime_type, "rows": len(df)})
                
                except Exception as file_error:
                    st.error(f"Erro ao processar o arquivo {file_name}: {file_error}. Pulando...")

            
            progress_bar.empty()

            if not all_data:
                st.error("Nenhum dado válido foi carregado. Todas as planilhas estão vazias ou com formato incorreto.")
                elapsed = time.time() - start_ts
                return pd.DataFrame(), loaded_files, {"file_count": len(items), "row_count": 0, "load_seconds": elapsed}

            consolidated_df = pd.concat(all_data, ignore_index=True)
            # Garante colunas em padrão canônico
            consolidated_df = _standardize_dataframe(consolidated_df)
            if 'data' in consolidated_df.columns:
                consolidated_df['data'] = pd.to_datetime(consolidated_df['data'], dayfirst=True, errors='coerce')
            for col in ['quantidade', 'preco_unitario', 'receita_total']:
                if col in consolidated_df.columns:
                    consolidated_df[col] = _clean_numeric_series(consolidated_df[col])
            # Calcula receita_total se ausente e possível
            if 'receita_total' not in consolidated_df.columns and {'quantidade','preco_unitario'}.issubset(consolidated_df.columns):
                consolidated_df['receita_total'] = consolidated_df['quantidade'] * consolidated_df['preco_unitario']

            elapsed = time.time() - start_ts
            stats = {"file_count": len(items), "row_count": len(consolidated_df), "load_seconds": elapsed}
            return consolidated_df, loaded_files, stats
        
        except Exception as e:
            st.error(f"Ocorreu um erro crítico ao ler os arquivos do Google Drive: {e}")
            return pd.DataFrame(), [], {"file_count": 0, "row_count": 0, "load_seconds": 0.0}


def get_gemini_analysis(user_query, sales_df, model_name: str = 'models/gemini-2.5-pro'):
    """Envia a pergunta e os dados para o Gemini para análise."""
    if sales_df.empty:
        return "Os dados de vendas não foram carregados. Não consigo analisar."

    csv_data = sales_df.to_csv(index=False)
    
    prompt_master = f"""
    # CONTEXTO & PERSONA
    Você é o "AlphaBot", um analista de vendas sênior da empresa Alpha Insights. Sua função é analisar os dados de vendas anuais fornecidos em formato CSV e responder a perguntas de negócios com precisão e clareza, baseando-se EXCLUSIVAMENTE nos dados.

    # REGRAS DE OPERAÇÃO
    1.  **Fidelidade aos Dados:** Responda APENAS com base nos dados. Se a pergunta não pode ser respondida (ex: "Qual a margem de lucro?"), responda: "Não tenho acesso a essa informação nos dados de vendas."
    2.  **Clareza:** Forneça respostas diretas. Para valores monetários, use o formato R$ X.XXX,XX.
    3.  **Cálculos:** Realize cálculos como somas, médias, contagens, máximos/mínimos, variações percentuais e agrupamentos por trimestre (Q1: Jan-Mar, Q2: Abr-Jun, etc.), região, produto, etc.
    4.  **Não alucine:** Não invente dados ou tendências.

    # DADOS DE VENDAS
    {csv_data}

    # PERGUNTA DO USUÁRIO
    {user_query}

    # SUA RESPOSTA (seja direto e informativo):
    """
    
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt_master)
        return response.text
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao contatar o serviço de IA: {e}"

# --- Interface do Usuário com Streamlit ---
st.set_page_config(page_title="AlphaBot - Analista de Vendas", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
    /* Aumenta contraste e visibilidade do input de chat */
    .stChatFloatingInputContainer, .stChatInputContainer { 
        border: 1px solid #e91e63 !important; 
        box-shadow: 0 0 10px rgba(233,30,99,0.35);
    }
    .stChatInput > div > div textarea {
        font-size: 1rem !important;
    }
    /* Sidebar estilizada para lista de arquivos */
    section[data-testid="stSidebar"] .stMarkdown ul {
        list-style: none; padding-left: 0;
    }
    section[data-testid="stSidebar"] li { 
        margin: .25rem 0; padding: .35rem .5rem; background: #1f2023; border-radius: .35rem;
    }
    section[data-testid="stSidebar"] li small { color: #bbb; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("🤖 AlphaBot | Analista de Vendas")

sales_data_df, loaded_files, load_stats = load_sales_data(GOOGLE_DRIVE_FOLDER_ID)

# Sidebar: configurações e lista de arquivos
with st.sidebar:
    st.subheader("Configurações")
    model_options = [
        'models/gemini-2.5-pro',
        'models/gemini-2.5-flash',
        'models/gemini-pro-latest',
        'models/gemini-flash-latest',
    ]
    selected_model = st.selectbox(
        "Modelo do Gemini",
        options=model_options,
        index=model_options.index('models/gemini-2.5-pro'),
        key="model_name",
        help="Escolha o modelo para responder às suas perguntas. Recomendado: gemini-2.5-pro."
    )
    if st.button("Recarregar dados", use_container_width=True, help="Limpa o cache e recarrega os arquivos do Drive"):
        st.cache_data.clear()
        st.rerun()

    st.header("Arquivos carregados")
    if loaded_files:
        for f in loaded_files:
            icon = "📄" if f.get("mimeType") == 'text/csv' else "🧮"
            rows_info = f" - {f.get('rows', 0)} linhas" if isinstance(f.get('rows'), int) else ""
            st.markdown(f"- {icon} **{f['name']}**{rows_info}")
    else:
        st.info("Nenhum arquivo listado ainda.")

    st.divider()
    st.subheader("Resumo da carga")
    st.write(f"Arquivos encontrados: {load_stats.get('file_count', 0)}")
    st.write(f"Linhas consolidadas: {load_stats.get('row_count', 0)}")
    st.write(f"Tempo de carga: {load_stats.get('load_seconds', 0):.2f}s")

if not sales_data_df.empty:
    st.success(f"Dados de {len(sales_data_df)} transações carregados com sucesso!")
    with st.expander("Prévia dos dados (25 linhas)"):
        st.dataframe(sales_data_df.head(25), use_container_width=True)
    st.download_button(
        label="Baixar CSV consolidado",
        data=sales_data_df.to_csv(index=False),
        file_name="vendas_consolidado.csv",
        mime="text/csv"
    )
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_query := st.chat_input("Qual a sua pergunta sobre as vendas?"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Analisando os dados..."):
                # Prepara um resumo e amostra para reduzir payload ao LLM
                resumo, csv_amostra = _prepare_analysis_payload(sales_data_df, max_rows=1000)
                # Monta prompt compacto com resumo + amostra
                compact_query = f"""
                CONTEXTO: Abaixo há um resumo estatístico dos dados de vendas e uma amostra de linhas.
                Use APENAS essas informações para responder. Caso precise de algo fora disso, diga que não está disponível.

                RESUMO DOS DADOS
                {resumo}

                AMOSTRA (CSV - até 1000 linhas)
                {csv_amostra}

                PERGUNTA DO USUÁRIO
                {user_query}
                """
                response = get_gemini_analysis(compact_query, sales_data_df, model_name=st.session_state.get("model_name", 'models/gemini-2.5-pro'))
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.error("Não foi possível carregar os dados de vendas. Verifique as configurações e a estrutura das planilhas.")       