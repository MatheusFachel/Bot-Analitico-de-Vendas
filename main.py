import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import os
import io
import csv
import time
import unicodedata
import re
import json
from typing import List, Dict, Tuple, Any
from collections import Counter

# Dependência opcional para Excel
try:
    import openpyxl  # noqa: F401
    _HAS_OPENPYXL = True
except Exception:
    _HAS_OPENPYXL = False

# Tenta carregar as configurações do arquivo config.py
try:
    from config import GOOGLE_DRIVE_FOLDER_ID, GEMINI_API_KEY
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
        # Obtém credenciais como dict (JSON ou arquivo)
        creds_dict = config.get_google_service_account_credentials()
        
        # Cria credenciais a partir do dict
        creds = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        sheets_service = build('sheets', 'v4', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)
        # Guarda o email da conta de serviço para diagnóstico
        try:
            st.session_state['service_account_email'] = getattr(creds, 'service_account_email', '')
        except Exception:
            pass
        return sheets_service, drive_service
    except Exception as e:
        st.error(f"Erro de autenticação com o Google. Verifique o caminho do arquivo 'service_account.json' e se a API está habilitada. Detalhes: {e}")
        st.stop()
        return None, None


def _execute_request_with_retries(request, max_retries: int = 3, backoff: float = 1.5):
    """Executa uma requisição googleapiclient com tentativas e backoff exponencial simples."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return request.execute(num_retries=0)
        except Exception as e:
            last_exc = e
            time.sleep(min(5.0, (backoff ** attempt)))
    # Se falhar todas as tentativas, relança a última exceção
    raise last_exc


def _download_drive_file_bytes(drive_service, file_id: str, max_retries: int = 3) -> bytes:
    """Baixa arquivo do Drive em chunks com retries para reduzir falhas de conexão."""
    buf = io.BytesIO()
    request = drive_service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(buf, request, chunksize=1024 * 1024)
    done = False
    retries = 0
    while not done:
        try:
            status, done = downloader.next_chunk()
        except Exception as e:
            retries += 1
            if retries >= max_retries:
                raise e
            time.sleep(min(5.0, 1.5 ** retries))
            continue
    buf.seek(0)
    return buf.read()

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
        'data': {
            'data', 'date', 'dt',
            'data_venda', 'data_da_venda', 'data_pedido', 'data_do_pedido',
            'data_emissao', 'emissao', 'emissao_nf', 'data_nf', 'data_nota',
            'data_de_venda', 'data_de_emissao', 'dt_venda', 'dt_emissao'
        },
        'quantidade': {'quantidade', 'qtd', 'quant', 'qte'},
        'preco_unitario': {'preco_unitario', 'preco', 'preco_unit', 'valor_unitario', 'preco_unitário', 'preco_venda'},
        'receita_total': {'receita_total', 'receita', 'faturamento', 'valor_total', 'total'},
        'produto': {'produto', 'item', 'sku', 'descricao', 'descricao_produto'},
        'regiao': {'regiao', 'regiao_venda', 'regiao_geografica', 'regiao_', 'regioes', 'regional', 'regiao_cliente'},
        'categoria': {'categoria', 'category', 'grupo', 'segmento', 'classe'}
    }
    current = set(df.columns)
    for canon, alts in alias_map.items():
        found = [c for c in current if c in alts]
        if found and canon not in df.columns:
            df = df.rename(columns={found[0]: canon})
    return df


def _coerce_date_series(s: pd.Series) -> pd.Series:
    """Converte uma série para datetime de forma robusta:
    - Strings com dayfirst=True
    - Números no formato serial do Excel (origin '1899-12-30')
    - Retorna NaT quando não possível
    """
    if s is None or len(s) == 0:
        return pd.to_datetime(pd.Series([], dtype='datetime64[ns]'))
    try:
        # Primeiro tenta converter strings convencionais
        out = pd.to_datetime(s, dayfirst=True, errors='coerce')
        # Se taxa de NaT for alta, tenta serial do Excel onde fizer sentido
        nat_ratio = out.isna().mean()
        # Identifica valores que parecem números (inclui strings numéricas)
        numeric_mask = pd.to_numeric(s, errors='coerce').notna()
        if nat_ratio > 0.5 and numeric_mask.any():
            excel_nums = pd.to_numeric(s.where(numeric_mask), errors='coerce')
            # Heurística de faixa comum de seriais do Excel (datas recentes)
            # 25569 ~ 1970-01-01; 60000 ~ 2064
            plausible = excel_nums.between(20000, 80000)
            if plausible.any():
                alt = pd.to_datetime(excel_nums.where(plausible), unit='D', origin='1899-12-30', errors='coerce')
                out = out.combine_first(alt)
        return out
    except Exception:
        # fallback bruto
        return pd.to_datetime(s, errors='coerce')


def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que exista uma coluna 'data'. Se não houver, tenta detectar a melhor candidata e cria 'data'."""
    if df is None or df.empty:
        return df
    if 'data' in df.columns:
        df['data'] = _coerce_date_series(df['data'])
        return df
    # Tenta detectar coluna de data por taxa de parse
    best_col = None
    best_ratio = 0.0
    for c in df.columns:
        try:
            parsed = _coerce_date_series(df[c])
            ratio = parsed.notna().mean()
            if ratio > best_ratio:
                best_ratio = ratio
                best_col = c
        except Exception:
            continue
    if best_col and best_ratio >= 0.6:
        df['data'] = _coerce_date_series(df[best_col])
    return df

def _clean_numeric_series(s: pd.Series) -> pd.Series:
    """Normaliza números de forma elemento a elemento para evitar inflar valores.
    Regras:
    - Se já for dtype numérico, retorna como está.
    - Remove moeda/símbolos (ex.: R$, %), NBSP e espaços.
    - Se a string tiver vírgula, trata como BR (',' decimal): remove pontos de milhar e troca vírgula por ponto.
    - Caso contrário, mantém '.' como decimal.
    """
    try:
        from pandas.api.types import is_numeric_dtype
    except Exception:
        is_numeric_dtype = lambda x: False  # fallback

    if is_numeric_dtype(s):
        return s
    def _parse(x: object) -> float:
        if x is None:
            return float('nan')
        sx = str(x).strip()
        # remove moeda/símbolos, mantendo apenas dígitos, sinais e separadores
        sx = re.sub(r"[^0-9,\.-]", "", sx)
        sx = sx.replace('\u00A0', '').replace(' ', '')
        if sx == '' or sx in {'-', '.', ','}:
            return float('nan')
        # Se contém vírgula, tratamos como BR
        if ',' in sx:
            sx = sx.replace('.', '')  # remove milhar
            sx = sx.replace(',', '.')
        # Caso contrário, assume '.' como decimal
        try:
            return float(sx)
        except Exception:
            return float('nan')

    return s.map(_parse)

def _drop_total_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas de totais agregados baseadas em texto 'total' nas colunas de texto."""
    if df is None or df.empty:
        return df
    str_cols = [c for c in df.columns if df[c].dtype == 'object']
    if not str_cols:
        return df
    pat = re.compile(r"^\s*totais?$|^\s*total\b", re.IGNORECASE)
    mask = pd.Series(False, index=df.index)
    for c in str_cols:
        try:
            mask = mask | df[c].astype(str).str.match(pat)
        except Exception:
            continue
    return df[~mask]

def _deduplicate_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Remove duplicatas com base em chaves preferenciais; retorna (df, removidos)."""
    if df is None or df.empty:
        return df, 0
    before = len(df)
    id_candidates = [
        'id', 'pedido_id', 'order_id', 'nota_id', 'invoice_id', 'id_pedido', 'id_nota', 'id_venda'
    ]
    key_cols = [c for c in id_candidates if c in df.columns]
    if not key_cols:
        key_cols = [c for c in ['data', 'produto', 'quantidade', 'preco_unitario', 'receita_total'] if c in df.columns]
    subset = key_cols if key_cols else df.columns.tolist()
    deduped = df.drop_duplicates(subset=subset, keep='first', ignore_index=True)
    removed = before - len(deduped)
    return deduped, removed

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
    Retorna: (df_consolidado, lista_arquivos, stats, drive_info)
    lista_arquivos: List[Dict[name,id,mimeType,linhas]]
    stats: {file_count, row_count, load_seconds}
    drive_info: {folder_id, counts_by_mime: dict, unsupported: list[str]}
    """
    sheets_service, drive_service = get_google_apis_services()
    if not sheets_service or not drive_service:
        return pd.DataFrame(), [], {"file_count": 0, "row_count": 0, "load_seconds": 0.0}, {"folder_id": _drive_folder_id, "counts_by_mime": {}, "unsupported": []}

    start_ts = time.time()
    all_data = []
    loaded_files: List[Dict[str, str]] = []
    unsupported_files: List[str] = []
    aggregated_tabs_skipped = 0
    
    with st.spinner("Buscando planilhas na sua pasta do Google Drive..."):
        try:
            query = (
                f"'{_drive_folder_id}' in parents and ("
                "mimeType='application/vnd.google-apps.spreadsheet' or "
                "mimeType='text/csv' or "
                "mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')"
            )
            items: List[Dict] = []
            page_token = None
            while True:
                req = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                )
                results = _execute_request_with_retries(req, max_retries=3)
                items.extend(results.get('files', []))
                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            if not items:
                st.warning("Nenhum arquivo suportado encontrado na pasta do Drive (Sheets/CSV/XLSX). Verifique o ID da pasta e os tipos de arquivo.")
                elapsed = time.time() - start_ts
                counts = {}
                drive_info = {"folder_id": _drive_folder_id, "counts_by_mime": counts, "unsupported": []}
                return pd.DataFrame(), [], {"file_count": 0, "row_count": 0, "load_seconds": elapsed}, drive_info

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
                        meta_req = sheets_service.spreadsheets().get(spreadsheetId=file_id, fields='sheets(properties(title))')
                        meta = _execute_request_with_retries(meta_req, max_retries=3)
                        sheet_titles = [s['properties']['title'] for s in meta.get('sheets', [])]
                        # ignora abas agregadas por padrão
                        skip_pat = re.compile(r"^(resumo|dashboard|consolidado|grafico|gr[aá]fico|summary|pivot|totais?)$", re.IGNORECASE)
                        orig_count = len(sheet_titles)
                        sheet_titles = [t for t in sheet_titles if not re.match(skip_pat, str(t).strip())]
                        aggregated_tabs_skipped += max(0, orig_count - len(sheet_titles))
                        sub_frames = []
                        for title in sheet_titles:
                            try:
                                rng = f"{title}!A1:ZZZ"  # evita truncar colunas
                                vreq = sheets_service.spreadsheets().values().get(spreadsheetId=file_id, range=rng)
                                result = _execute_request_with_retries(vreq, max_retries=3)
                                values = result.get('values', [])
                                if not values or len(values) < 2:
                                    continue
                                headers = values[0]
                                tmp = pd.DataFrame(values[1:], columns=headers)
                                tmp = _standardize_dataframe(tmp)
                                tmp['source_sheet'] = title
                                sub_frames.append(tmp)
                            except Exception:
                                continue
                        if sub_frames:
                            df = pd.concat(sub_frames, ignore_index=True)
                        else:
                            st.info(f"Arquivo '{file_name}' sem dados utilizáveis. Pulado.")

                    elif mime_type == 'text/csv':
                        # --- INÍCIO DA LÓGICA FLEXÍVEL DE LEITURA ---
                        csv_content_bytes = _download_drive_file_bytes(drive_service, file_id)

                        detected_delimiter = ','  # Padrão
                        detected_decimal = '.'    # Padrão

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

                    elif mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                        # XLSX (Excel) - somente se openpyxl estiver instalado
                        if not _HAS_OPENPYXL:
                            st.error("Arquivo XLSX detectado, mas o pacote 'openpyxl' não está instalado. Adicione 'openpyxl' ao requirements.txt e reinstale.")
                            unsupported_files.append(file_name)
                            df = None
                        else:
                            xlsx_bytes = _download_drive_file_bytes(drive_service, file_id)
                            xlsbio = io.BytesIO(xlsx_bytes)
                            # Lê todas as abas
                            try:
                                xls = pd.ExcelFile(xlsbio, engine='openpyxl')
                                sub_frames = []
                                skip_pat = re.compile(r"^(resumo|dashboard|consolidado|grafico|gr[aá]fico|summary|pivot|totais?)$", re.IGNORECASE)
                                orig_count = len(xls.sheet_names)
                                for sheet in xls.sheet_names:
                                    if re.match(skip_pat, str(sheet).strip()):
                                        continue
                                    tmp = pd.read_excel(xls, sheet_name=sheet, engine='openpyxl')
                                    tmp = _standardize_dataframe(tmp)
                                    tmp['source_sheet'] = sheet
                                    sub_frames.append(tmp)
                                aggregated_tabs_skipped += max(0, orig_count - len(sub_frames))
                                df = pd.concat(sub_frames, ignore_index=True) if sub_frames else None
                            except Exception as e:
                                st.error(f"Erro ao ler XLSX '{file_name}': {e}")
                                df = None

                    if df is not None:
                        df = _standardize_dataframe(df)
                        # Remover linhas de totais
                        df = _drop_total_rows(df)
                        # Garantir/Tratar coluna de data
                        df = _ensure_date_column(df)
                        for col in ['quantidade', 'preco_unitario', 'receita_total']:
                            if col in df.columns:
                                df[col] = _clean_numeric_series(df[col])
                        # Marcar origem
                        df['source_file'] = file_name
                        all_data.append(df)
                        loaded_files.append({"name": file_name, "id": file_id, "mimeType": mime_type, "rows": len(df)})

                except Exception as file_error:
                    st.error(f"Erro ao processar o arquivo {file_name}: {file_error}. Pulando...")

            
            progress_bar.empty()

            if not all_data:
                st.error("Nenhum dado válido foi carregado. Todas as planilhas estão vazias, inacessíveis, em formato não suportado ou com cabeçalhos incompatíveis.")
                elapsed = time.time() - start_ts
                counts = Counter([it.get('mimeType') for it in items])
                drive_info = {"folder_id": _drive_folder_id, "counts_by_mime": dict(counts), "unsupported": unsupported_files}
                return pd.DataFrame(), loaded_files, {"file_count": len(items), "row_count": 0, "load_seconds": elapsed}, drive_info

            consolidated_df = pd.concat(all_data, ignore_index=True)
            # Garante colunas em padrão canônico
            consolidated_df = _standardize_dataframe(consolidated_df)
            # Garantir/Tratar coluna de data consolidada
            consolidated_df = _ensure_date_column(consolidated_df)
            for col in ['quantidade', 'preco_unitario', 'receita_total']:
                if col in consolidated_df.columns:
                    consolidated_df[col] = _clean_numeric_series(consolidated_df[col])
            # Calcula receita_total se ausente e possível
            if 'receita_total' not in consolidated_df.columns and {'quantidade','preco_unitario'}.issubset(consolidated_df.columns):
                consolidated_df['receita_total'] = consolidated_df['quantidade'] * consolidated_df['preco_unitario']

            # Remover totais e deduplicar
            consolidated_df = _drop_total_rows(consolidated_df)
            rows_before_dedup = len(consolidated_df)
            consolidated_df, dedup_removed = _deduplicate_dataframe(consolidated_df)

            elapsed = time.time() - start_ts
            stats = {
                "file_count": len(items),
                "row_count": len(consolidated_df),
                "load_seconds": elapsed,
                "rows_before_dedup": rows_before_dedup,
                "dedup_removed": dedup_removed,
                "aggregated_tabs_skipped": aggregated_tabs_skipped,
            }
            counts = Counter([it.get('mimeType') for it in items])
            drive_info = {"folder_id": _drive_folder_id, "counts_by_mime": dict(counts), "unsupported": unsupported_files}
            return consolidated_df, loaded_files, stats, drive_info
        
        except Exception as e:
            st.error(f"Ocorreu um erro crítico ao ler os arquivos do Google Drive: {e}")
            return pd.DataFrame(), [], {"file_count": 0, "row_count": 0, "load_seconds": 0.0}, {"folder_id": _drive_folder_id, "counts_by_mime": {}, "unsupported": []}


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


# ============== Planner → Executor para perguntas complexas ==============
def _build_data_catalog(df: pd.DataFrame) -> Dict[str, Any]:
    """Gera um catálogo simples de dados: colunas, tipos, métricas/dimensões candidatas e intervalos."""
    catalog: Dict[str, Any] = {
        "columns": [],
        "metrics": [],
        "dimensions": [],
    }
    if df is None or df.empty:
        return catalog
    for c in df.columns:
        dtype = str(df[c].dtype)
        col_info = {"name": c, "dtype": dtype}
        if c == 'data':
            try:
                col_info["min"] = str(pd.to_datetime(df[c], errors='coerce').min())
                col_info["max"] = str(pd.to_datetime(df[c], errors='coerce').max())
            except Exception:
                pass
        elif pd.api.types.is_numeric_dtype(df[c]):
            try:
                col_info["min"] = float(pd.to_numeric(df[c], errors='coerce').min())
                col_info["max"] = float(pd.to_numeric(df[c], errors='coerce').max())
                col_info["sum"] = float(pd.to_numeric(df[c], errors='coerce').sum())
            except Exception:
                pass
        catalog["columns"].append(col_info)
        # Heurística de métricas e dimensões
        if pd.api.types.is_numeric_dtype(df[c]) or c in {"quantidade", "preco_unitario", "receita_total"}:
            catalog["metrics"].append(c)
        else:
            catalog["dimensions"].append(c)
    # Marcação de chaves/identificadores comuns
    catalog["identifiers"] = [c for c in df.columns if c in [
        'id','pedido_id','order_id','nota_id','invoice_id','id_pedido','id_nota','id_venda']]
    return catalog


def _plan_with_llm(user_query: str, catalog: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Solicita ao LLM um plano em JSON para executar sobre pandas. Retorna dicionário já parseado."""
    system = (
        "Você é um planejador de consultas tabulares. Produza SOMENTE um JSON válido que descreva um plano de análise sobre um DataFrame pandas. "
        "Não inclua comentários, markdown ou texto fora do JSON. Se não houver dados suficientes, retorne {\"error\": \"mensagem\"}."
    )
    schema_hint = {
        "filters": {"date_range": ["YYYY-MM-DD","YYYY-MM-DD"], "equals": {"coluna": ["valor1","valor2"]}},
        "groupby": ["coluna1","coluna2"],
        "metrics": [{"name": "receita_total", "agg": "sum"}],
        "sort": {"by": "receita_total", "ascending": False},
        "limit": 50
    }
    prompt = f"""
    CATÁLOGO DE DADOS (JSON):
    {json.dumps(catalog, ensure_ascii=False)}

    Esquematize um plano JSON para responder: {user_query}
    Use o seguinte formato de plano:
    {json.dumps(schema_hint, ensure_ascii=False)}
    Apenas colunas existentes no catálogo. Priorize métricas ['receita_total','quantidade','preco_unitario'] quando fizer sentido.
    """
    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content([system, prompt])
        text = resp.text or "{}"
        # Tente extrair JSON puro
        text_stripped = text.strip()
        if text_stripped.startswith("```) ") and text_stripped.endswith("```"):
            # fallback tosco caso venha em bloco, removendo crases
            text_stripped = text_stripped.strip('`')
        # Encontrar primeira/última chave
        first = text_stripped.find('{')
        last = text_stripped.rfind('}')
        if first >= 0 and last >= 0:
            text_stripped = text_stripped[first:last+1]
        plan = json.loads(text_stripped)
        if not isinstance(plan, dict):
            return {"error": "Plano não é um objeto JSON."}
        return plan
    except Exception as e:
        return {"error": f"Falha ao planejar com LLM: {e}"}


def _execute_plan(df: pd.DataFrame, plan: Dict[str, Any]) -> Dict[str, Any]:
    """Executa um plano simples sobre um DataFrame usando pandas. Retorna dict com 'table' e 'summary'."""
    result: Dict[str, Any] = {"table": pd.DataFrame(), "summary": ""}
    if df is None or df.empty:
        result["summary"] = "Sem dados para executar o plano."
        return result
    work = df.copy()
    # filtros por intervalo de data
    try:
        filters = plan.get("filters", {}) if isinstance(plan, dict) else {}
        if 'date_range' in filters and 'data' in work.columns:
            ini, fim = filters['date_range']
            ini_dt = pd.to_datetime(ini, errors='coerce')
            fim_dt = pd.to_datetime(fim, errors='coerce')
            if pd.notna(ini_dt) and pd.notna(fim_dt):
                work = work[(work['data'] >= ini_dt) & (work['data'] <= fim_dt)]
        # equals
        equals = filters.get('equals', {}) if isinstance(filters, dict) else {}
        for col, vals in equals.items():
            if col in work.columns:
                work = work[work[col].astype(str).isin([str(v) for v in vals])]
    except Exception:
        pass
    # derivar receita_total se preciso
    if 'receita_total' not in work.columns and {'quantidade','preco_unitario'}.issubset(work.columns):
        work['receita_total'] = work['quantidade'] * work['preco_unitario']
    # groupby + metrics
    groupby = plan.get('groupby', []) if isinstance(plan, dict) else []
    metrics = plan.get('metrics', []) if isinstance(plan, dict) else []
    agg_spec: Dict[str, str] = {}
    for m in metrics:
        if isinstance(m, dict) and m.get('name') in work.columns:
            agg_spec[m['name']] = m.get('agg','sum')
        elif isinstance(m, str) and m in work.columns:
            agg_spec[m] = 'sum'
    table = pd.DataFrame()
    try:
        if groupby and agg_spec:
            table = work.groupby(groupby).agg(agg_spec).reset_index()
        elif agg_spec:
            table = work.agg(agg_spec).to_frame().T
        else:
            table = work.head(50)
    except Exception:
        table = work.head(50)
    # sort/limit
    try:
        sort = plan.get('sort', {}) if isinstance(plan, dict) else {}
        if sort and sort.get('by') in table.columns:
            table = table.sort_values(by=sort['by'], ascending=bool(sort.get('ascending', False)))
        limit = int(plan.get('limit', 50))
        table = table.head(limit)
    except Exception:
        pass
    # resumo rápido
    try:
        lines = [f"Linhas retornadas: {len(table)}"]
        if 'receita_total' in work.columns:
            lines.append(f"Receita total no filtro: {_fmt_brl(float(work['receita_total'].sum()))}")
        if 'quantidade' in work.columns:
            lines.append(f"Quantidade total no filtro: {int(pd.to_numeric(work['quantidade'], errors='coerce').sum())}")
        result['summary'] = " | ".join(lines)
    except Exception:
        result['summary'] = f"Linhas retornadas: {len(table)}"
    result['table'] = table
    return result


def _narrate_results_with_llm(user_query: str, plan: Dict[str, Any], exec_res: Dict[str, Any], model_name: str) -> str:
    """Gera uma resposta em linguagem natural usando o LLM baseada no resultado do Planner→Executor."""
    try:
        table: pd.DataFrame = exec_res.get('table', pd.DataFrame())
        summary: str = exec_res.get('summary', '')
        sample_csv = table.head(100).to_csv(index=False) if isinstance(table, pd.DataFrame) and not table.empty else ''
        plan_json = json.dumps(plan, ensure_ascii=False)
        prompt = f"""
        Você é o AlphaBot, analista de vendas. Responda de forma direta, em português, com base SOMENTE nos dados fornecidos abaixo. 
        Formate valores monetários como R$ X.XXX,XX e inclua comparações, variações percentuais e insights executivos quando aplicável.

        PERGUNTA DO USUÁRIO:
        {user_query}

        CONTEXTO E RESULTADOS DISPONÍVEIS:
        - Plano de execução (JSON): {plan_json}
        - Resumo do resultado: {summary}
        - Tabela resultante (amostra até 100 linhas, CSV):
        {sample_csv}

        Gere uma resposta clara e objetiva, usando apenas o que está acima. Se algo não estiver nas colunas/linhas, diga que não está disponível.
        """
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text or summary or "Não há informações suficientes para responder."
    except Exception as e:
        # Fallback para pelo menos devolver o resumo
        return f"(Não foi possível gerar a narrativa do LLM: {e})\n{exec_res.get('summary', '')}"

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

sales_data_df, loaded_files, load_stats, drive_info = load_sales_data(GOOGLE_DRIVE_FOLDER_ID)

# Descoberta automática de modelos (com cache e fallback)
@st.cache_data(ttl=10800)
def get_available_models() -> List[str]:
    try:
        models = []
        for m in genai.list_models():
            if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        # ordenar para lista estável
        models = sorted(set(models))
        # sugeridos primeiro
        preferred = [
            'models/gemini-2.5-pro',
            'models/gemini-2.5-flash',
            'models/gemini-pro-latest',
            'models/gemini-flash-latest',
        ]
        # garantimos que preferidos venham no topo
        head = [m for m in preferred if m in models]
        tail = [m for m in models if m not in preferred]
        return head + tail
    except Exception:
        # Fallback simples
        return [
            'models/gemini-2.5-pro',
            'models/gemini-2.5-flash',
            'models/gemini-pro-latest',
            'models/gemini-flash-latest',
        ]

with st.sidebar:
    # 1) Configurações
    st.subheader("Configurações")
    model_options = get_available_models()
    selected_model = st.selectbox(
        "Modelo do Gemini",
        options=model_options,
        index=model_options.index('models/gemini-2.5-pro') if 'models/gemini-2.5-pro' in model_options else 0,
        key="model_name",
        help="Escolha o modelo para responder às suas perguntas. Recomendado: gemini-2.5-pro."
    )
    if st.button("Recarregar dados", use_container_width=True, help="Limpa o cache e recarrega os arquivos do Drive"):
        st.cache_data.clear()
        st.rerun()

    # 2) Filtros (removido filtro por data; mantemos produtos e regiões)
    st.divider()
    st.subheader("Filtros")
    filter_info = {}
    if not sales_data_df.empty:
        df_for_filters = sales_data_df
        # Produtos (vazio por padrão)
        if 'produto' in df_for_filters.columns:
            prods = sorted([p for p in df_for_filters['produto'].dropna().astype(str).unique()][:5000])
            sel_prods = st.multiselect("Produtos", options=prods, default=[], key='f_produtos')
            filter_info['produtos'] = sel_prods
        # Regiões (vazio por padrão)
        if 'regiao' in df_for_filters.columns:
            regs = sorted([r for r in df_for_filters['regiao'].dropna().astype(str).unique()][:5000])
            sel_regs = st.multiselect("Regiões", options=regs, default=[], key='f_regioes')
            filter_info['regioes'] = sel_regs

    # 3) Arquivos carregados
    st.divider()
    st.header("Arquivos carregados")
    selected_file_names: List[str] = []
    if loaded_files:
        st.caption("Selecione os arquivos que deseja incluir na análise")
        cols_sel = st.columns(2)
        with cols_sel[0]:
            if st.button("Selecionar todos", use_container_width=True):
                for f in loaded_files:
                    st.session_state[f"file_{f['id']}"] = True
        with cols_sel[1]:
            if st.button("Limpar seleção", use_container_width=True):
                for f in loaded_files:
                    st.session_state[f"file_{f['id']}"] = False
        for f in loaded_files:
            icon = "📄" if f.get("mimeType") == 'text/csv' else "🧮"
            key = f"file_{f['id']}"
            default_checked = st.session_state.get(key, True)
            checked = st.checkbox(f"{icon} {f['name']} ({f.get('rows', 0)} linhas)", value=default_checked, key=key)
            if checked:
                selected_file_names.append(f['name'])
    else:
        st.info("Nenhum arquivo listado ainda.")

    # 4) Resumo da carga (sem diagnóstico)
    st.divider()
    st.subheader("Resumo da carga")
    st.write(f"Arquivos encontrados: {load_stats.get('file_count', 0)}")
    st.write(f"Linhas consolidadas: {load_stats.get('row_count', 0)}")
    st.write(f"Tempo de carga: {load_stats.get('load_seconds', 0):.2f}s")
    # métricas extras
    if 'rows_before_dedup' in load_stats and 'dedup_removed' in load_stats:
        st.caption(f"Antes da dedup: {load_stats.get('rows_before_dedup', 0)} | Removidas: {load_stats.get('dedup_removed', 0)}")
    if 'aggregated_tabs_skipped' in load_stats:
        st.caption(f"Abas agregadas ignoradas: {load_stats.get('aggregated_tabs_skipped', 0)}")

def _apply_filters(df: pd.DataFrame, selected_files: List[str], filter_info: Dict) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df
    if selected_files and 'source_file' in out.columns:
        out = out[out['source_file'].isin(selected_files)]
    if filter_info:
        # produto
        if 'produtos' in filter_info and 'produto' in out.columns and filter_info['produtos']:
            out = out[out['produto'].astype(str).isin(filter_info['produtos'])]
        # regiao
        if 'regioes' in filter_info and 'regiao' in out.columns and filter_info['regioes']:
            out = out[out['regiao'].astype(str).isin(filter_info['regioes'])]
    return out


def _fmt_brl(v: float) -> str:
    try:
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "R$ 0,00"


if not sales_data_df.empty:
    st.success(f"Dados de {len(sales_data_df)} transações carregados com sucesso!")
    # Aplica filtros da sidebar
    filtered_df = _apply_filters(sales_data_df, selected_file_names if 'selected_file_names' in locals() else [], filter_info if 'filter_info' in locals() else {})

    # KPIs
    receita_col = 'receita_total' if 'receita_total' in filtered_df.columns else None
    if not receita_col and {'quantidade','preco_unitario'}.issubset(filtered_df.columns):
        receita_col = 'receita_total_temp'
        filtered_df[receita_col] = filtered_df['quantidade'] * filtered_df['preco_unitario']
    total_receita = float(filtered_df[receita_col].sum()) if receita_col else 0.0
    total_transacoes = int(len(filtered_df))
    ticket_medio = (total_receita / total_transacoes) if total_transacoes > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Receita total (estimada)", _fmt_brl(total_receita))
    c2.metric("Transações (linhas)", f"{total_transacoes:,}".replace(',', '.'))
    c3.metric("Ticket médio (por venda)", _fmt_brl(ticket_medio))

    # Período e Top produto (texto)
    if 'data' in filtered_df.columns:
        try:
            min_dt = filtered_df['data'].min(); max_dt = filtered_df['data'].max()
            st.caption(f"Período nos dados: {min_dt.date() if pd.notna(min_dt) else '?'} a {max_dt.date() if pd.notna(max_dt) else '?'}")
        except Exception:
            pass
    # Aviso sobre linhas sem data
    if 'data' in filtered_df.columns:
        try:
            invalid_dates = int(filtered_df['data'].isna().sum())
            if invalid_dates > 0:
                st.caption(f"Aviso: {invalid_dates} linhas sem data válida estão incluídas.")
        except Exception:
            pass
    if 'produto' in filtered_df.columns:
        try:
            top_prod = (
                filtered_df.groupby('produto')[receita_col].sum().sort_values(ascending=False).head(1)
                if receita_col else filtered_df.groupby('produto')['quantidade'].sum().sort_values(ascending=False).head(1)
            )
            if not top_prod.empty:
                st.caption(f"Top produto: {top_prod.index[0]}")
        except Exception:
            pass
    with st.expander("Prévia dos dados (25 linhas)"):
        st.dataframe(filtered_df.head(25), use_container_width=True)
    st.download_button(
        label="Baixar CSV consolidado",
        data=filtered_df.to_csv(index=False),
        file_name="vendas_consolidado.csv",
        mime="text/csv"
    )

    # Diagnóstico de datas
    with st.expander("Diagnóstico de datas e período"):
        total_lin = len(sales_data_df)
        valid_dates = sales_data_df['data'].notna().sum() if 'data' in sales_data_df.columns else 0
        st.write(f"Linhas totais: {total_lin}")
        st.write(f"Linhas com data válida: {valid_dates}")
        # Receita por mês (antes e depois do filtro)
        try:
            if 'data' in sales_data_df.columns:
                base = sales_data_df.dropna(subset=['data']).assign(mes=lambda x: x['data'].dt.to_period('M').astype(str))
                rcol = 'receita_total' if 'receita_total' in base.columns else None
                if not rcol and {'quantidade','preco_unitario'}.issubset(base.columns):
                    base['receita_total'] = base['quantidade'] * base['preco_unitario']
                    rcol = 'receita_total'
                if rcol:
                    st.write("Receita por mês (todas as linhas com data válida):")
                    st.dataframe(base.groupby('mes')[rcol].sum().reset_index().sort_values('mes'), use_container_width=True)
        except Exception:
            pass
    
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
                # 1) Tenta Planner→Executor
                catalog = _build_data_catalog(filtered_df)
                plan = _plan_with_llm(user_query, catalog, model_name=st.session_state.get("model_name", 'models/gemini-2.5-pro'))
                used_planner = False
                final_text = ""
                if isinstance(plan, dict) and not plan.get('error'):
                    used_planner = True
                    exec_res = _execute_plan(filtered_df, plan)
                    # Não exibimos a tabela; apenas geramos a narrativa baseada no resultado interno
                    final_text = _narrate_results_with_llm(
                        user_query=user_query,
                        plan=plan,
                        exec_res=exec_res,
                        model_name=st.session_state.get("model_name", 'models/gemini-2.5-pro')
                    )
                # 2) Fallback: resumo + amostra para o LLM
                if not used_planner:
                    resumo, csv_amostra = _prepare_analysis_payload(filtered_df, max_rows=1000)
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
                    final_text = get_gemini_analysis(compact_query, filtered_df, model_name=st.session_state.get("model_name", 'models/gemini-2.5-pro'))
                st.markdown(final_text)
            st.session_state.messages.append({"role": "assistant", "content": final_text})
else:
    st.error("Não foi possível carregar os dados de vendas. Verifique as configurações e a estrutura das planilhas.")       