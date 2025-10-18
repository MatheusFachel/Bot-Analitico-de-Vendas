import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import io
import csv

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

@st.cache_data(ttl=3600) # Cache de dados por 1 hora
def load_sales_data(_drive_folder_id):
    """Carrega e consolida dados de vendas de múltiplas planilhas do Google Drive."""
    sheets_service, drive_service = get_google_apis_services()
    if not sheets_service or not drive_service:
        return pd.DataFrame()

    all_data = []
    
    with st.spinner("Buscando planilhas na sua pasta do Google Drive..."):
        try:
            query = f"'{_drive_folder_id}' in parents and (mimeType='application/vnd.google-apps.spreadsheet' or mimeType='text/csv')"
            results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
            items = results.get('files', [])

            if not items:
                st.warning(f"Nenhuma planilha ou arquivo CSV encontrado na pasta do Drive. Verifique o ID da pasta em config.py.")
                return pd.DataFrame()

            progress_bar = st.progress(0, text="Iniciando o carregamento dos dados...")
            
            for i, item in enumerate(items):
                file_name = item['name']
                file_id = item['id']
                mime_type = item['mimeType']
                
                progress_bar.progress((i + 1) / len(items), text=f"Lendo arquivo: {file_name}")
                
                try:
                    df = None
                    if mime_type == 'application/vnd.google-apps.spreadsheet':
                        # Se for um Google Sheet nativo, lê os valores
                        result = sheets_service.spreadsheets().values().get(spreadsheetId=file_id, range='A1:Z').execute()
                        values = result.get('values', [])
                        
                        if not values or len(values) < 2: 
                            st.info(f"Arquivo '{file_name}' está vazio ou sem dados e foi pulado.")
                            continue
                        
                        headers = values[0]
                        if 'Data' not in headers:
                            st.warning(f"O arquivo '{file_name}' foi pulado. Cabeçalho 'Data' não encontrado.")
                            continue
                            
                        df = pd.DataFrame(values[1:], columns=headers)
                            
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

                        # Rebobina o stream e lê com o pandas usando os parâmetros detectados
                        csv_content = io.BytesIO(csv_content_bytes)
                        df = pd.read_csv(
                            csv_content, 
                            delimiter=detected_delimiter, 
                            decimal=detected_decimal
                        )
                        # --- FIM DA LÓGICA FLEXÍVEL ---
                        
                        if 'Data' not in df.columns:
                            st.warning(f"O arquivo CSV '{file_name}' foi pulado. A coluna 'Data' não foi encontrada.")
                            continue
                    
                    if df is not None:
                        all_data.append(df)
                
                except Exception as file_error:
                    st.error(f"Erro ao processar o arquivo {file_name}: {file_error}. Pulando...")

            
            progress_bar.empty()

            if not all_data:
                st.error("Nenhum dado válido foi carregado. Todas as planilhas estão vazias ou com formato incorreto.")
                return pd.DataFrame()

            consolidated_df = pd.concat(all_data, ignore_index=True)
            
            # --- A LIMPEZA DE DADOS ROBUSTA (JÁ FUNCIONA BEM) ---
            # Converte 'Data' para datetime
            consolidated_df['Data'] = pd.to_datetime(consolidated_df['Data'], errors='coerce')
            
            numeric_cols = ['Quantidade', 'Preco_Unitario', 'Receita_Total']
            
            for col in numeric_cols:
                if col in consolidated_df.columns:
                    # Esta lógica padroniza tudo para o formato correto
                    consolidated_df[col] = pd.to_numeric(
                        consolidated_df[col].astype(str).str.replace(',', '.'), 
                        errors='coerce'
                    )
                else:
                    st.warning(f"Coluna esperada '{col}' não encontrada em todos os arquivos.")

            return consolidated_df
        
        except Exception as e:
            st.error(f"Ocorreu um erro crítico ao ler os arquivos do Google Drive: {e}")
            return pd.DataFrame()


def get_gemini_analysis(user_query, sales_df):
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
        model = genai.GenerativeModel('models/gemini-flash-latest')
        response = model.generate_content(prompt_master)
        return response.text
    except Exception as e:
        return f"Desculpe, ocorreu um erro ao contatar o serviço de IA: {e}"

# --- Interface do Usuário com Streamlit ---
st.set_page_config(page_title="AlphaBot - Analista de Vendas", layout="centered", initial_sidebar_state="collapsed")

# CSS personalizado para aumentar o tamanho da barra de chat
st.markdown("""
<style>
.stChatInputContainer {
    padding-bottom: 5px;
    padding-top: 5px;
    width: 100%;
    max-width: 800px;  /* Aumenta a largura máxima da barra */
    margin: 0 auto;
}

.stChatInputContainer > input {
    height: 50px !important;  /* Aumenta a altura da barra */
    font-size: 16px !important;  /* Aumenta o tamanho da fonte */
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 AlphaBot | Analista de Vendas")

sales_data_df = load_sales_data(GOOGLE_DRIVE_FOLDER_ID)

if not sales_data_df.empty:
    st.success(f"Dados de {len(sales_data_df)} transações carregados com sucesso!")
    
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
                response = get_gemini_analysis(user_query, sales_data_df)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
else:
    st.error("Não foi possível carregar os dados de vendas. Verifique as configurações e a estrutura das planilhas.")       