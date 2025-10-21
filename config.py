"""
Configuração segura com fallback em ordem:
1) st.secrets (quando rodando no Streamlit com .streamlit/secrets.toml)
2) Variáveis de ambiente do sistema
3) Arquivo .env (se presente) via python-dotenv

Para o Service Account do Google, suporta dois métodos:
- GOOGLE_SERVICE_ACCOUNT_CREDENTIALS: JSON completo (para Streamlit Cloud)
- GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH: caminho do arquivo (para dev local)

Se ainda assim faltar, lançamos um erro amigável com instruções de configuração.
"""

import os
import json
from typing import Optional, Dict, Any

# Carrega variáveis de um arquivo .env se existir (em dev)
try:
	from dotenv import load_dotenv
	load_dotenv()  # não falha se o arquivo não existir
except Exception:
	pass

# Acesso ao st.secrets somente se Streamlit estiver disponível
try:
	import streamlit as st  # type: ignore
except Exception:  # fora do Streamlit
	st = None  # type: ignore


def _get_secret(name: str) -> Optional[str]:
	"""Tenta obter um segredo do st.secrets de forma resiliente."""
	if st is None:
		return None
	try:
		# st.secrets lança erro se o arquivo não existir; tratamos aqui
		value = st.secrets.get(name)
		if value is None:
			return None
		return str(value)
	except Exception:
		return None


def _get(name: str, *, required: bool = True, default: Optional[str] = None) -> Optional[str]:
	"""Ordem de resolução: st.secrets -> env vars -> default.
	Se required e nada encontrado, levanta RuntimeError com instruções.
	"""
	# 1) st.secrets
	value = _get_secret(name)
	# 2) env vars
	if not value:
		value = os.getenv(name)
	# 3) default
	if not value and default is not None:
		value = default

	if required and not value:
		raise RuntimeError(
			f"Configuração obrigatória ausente: {name}.\n"
			f"Defina a chave em .streamlit/secrets.toml (st.secrets) OU como variável de ambiente.\n\n"
			f"Exemplos:\n"
			f"  - .streamlit/secrets.toml:\n"
			f"      {name} = \"valor_aqui\"\n"
			f"  - PowerShell (sessão atual):\n"
			f"      $env:{name} = \"valor_aqui\"\n"
			f"  - .env (para dev local):\n"
			f"      {name}=valor_aqui\n"
		)
	return value


def get_google_service_account_credentials() -> Dict[str, Any]:
	"""
	Retorna as credenciais do Google Service Account como dict.
	
	Suporta dois métodos (em ordem de prioridade):
	1. GOOGLE_SERVICE_ACCOUNT_CREDENTIALS: JSON completo (para Streamlit Cloud)
	2. GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH: caminho do arquivo (para dev local)
	
	Returns:
		Dict com as credenciais no formato esperado pelo Google APIs
		
	Raises:
		RuntimeError: Se nenhum método de credencial estiver disponível
	"""
	# Método 1: JSON completo (preferido para Cloud)
	creds_json = _get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS", required=False)
	
	if creds_json:
		try:
			return json.loads(creds_json)
		except json.JSONDecodeError as e:
			raise RuntimeError(
				f"Erro ao fazer parse do JSON em GOOGLE_SERVICE_ACCOUNT_CREDENTIALS.\n"
				f"Verifique se o JSON está bem formatado. Detalhes: {e}"
			)
	
	# Método 2: Arquivo local (fallback para dev)
	creds_path = _get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH", required=False)
	
	if creds_path:
		if not os.path.isfile(creds_path):
			raise RuntimeError(
				f"Arquivo de credenciais não encontrado: {creds_path}\n"
				f"Verifique o caminho absoluto, por exemplo:\n"
				f"C:/Users/SEU_USER/Desktop/Bot-Analitico-de-Vendas/credentials/service_account.json"
			)
		
		try:
			with open(creds_path, 'r', encoding='utf-8') as f:
				return json.load(f)
		except json.JSONDecodeError as e:
			raise RuntimeError(
				f"Erro ao ler JSON do arquivo: {creds_path}\n"
				f"Verifique se o arquivo contém JSON válido. Detalhes: {e}"
			)
		except Exception as e:
			raise RuntimeError(
				f"Erro ao ler arquivo de credenciais: {creds_path}\n"
				f"Detalhes: {e}"
			)
	
	# Nenhum método disponível
	raise RuntimeError(
		"Credenciais do Google Service Account não configuradas.\n\n"
		"Configure usando um dos métodos:\n\n"
		"1. Para Streamlit Cloud (recomendado):\n"
		"   Adicione em .streamlit/secrets.toml:\n"
		'   GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = """\n'
		"   {\n"
		'     "type": "service_account",\n'
		'     "project_id": "seu-projeto",\n'
		"     ...\n"
		"   }\n"
		'   """\n\n'
		"2. Para desenvolvimento local:\n"
		"   Adicione em .streamlit/secrets.toml ou .env:\n"
		'   GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"\n'
	)


# Variáveis de configuração obrigatórias
GOOGLE_DRIVE_FOLDER_ID = _get("GOOGLE_DRIVE_FOLDER_ID")
GEMINI_API_KEY = _get("GEMINI_API_KEY")

# Credenciais do Google (validação ocorre na função acima quando chamada)
# Mantemos compatibilidade com código legado que usa a variável PATH
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = _get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH", required=False)
