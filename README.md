# AlphaBot – Projeto Educacional de Análise de Vendas com IA (Open Source)

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Educational-green)
![Status](https://img.shields.io/badge/status-Active-success)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4)

> 📊 **Transforme planilhas em insights conversacionais**  
> Faça perguntas em linguagem natural sobre seus dados de vendas e receba análises instantâneas.

![Demo](docs/images/demo.gif)
_Demo: Pergunta → Análise → Resposta em segundos_

---

## 🎯 Sobre o Projeto

Um projeto didático para aprender:

- 📥 Ingestão de dados de planilhas (Google Drive/Sheets, CSV, XLSX)
- 🧹 Limpeza e padronização (datas, números, aliases, deduplicação)
- 💬 Interface conversacional com Streamlit
- 🤖 Uso responsável de LLM (Gemini) com fluxo Planner → Executor → Narrativa

O foco é ser **legível, extensível e reproduzível**. Forks, issues e PRs são bem-vindos!

---

## Sumário

- [🎯 Sobre o Projeto](#-sobre-o-projeto)
- [O que este projeto faz](#o-que-este-projeto-faz)
- [⚡ Quick Start](#-quick-start)
- [Como funciona](#como-funciona-visão-de-aprendizado)
- [Arquitetura (alto nível)](#arquitetura-alto-nível)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Requisitos de sistema](#requisitos-de-sistema)
- [🔐 Credenciais do Google (como obter)](#-credenciais-do-google-como-obter)
- [💡 Exemplos de perguntas](#-exemplos-de-perguntas)
- [📦 Instalação e execução](#-instalação-e-execução)
  - [Windows PowerShell](#windows-powershell)
  - [Linux/macOS (bash/zsh)](#linuxmacos-bashzsh)
- [⚙️ Configuração detalhada](#️-configuração-detalhada)
- [Saída esperada ao iniciar](#saída-esperada-ao-iniciar)
- [📊 Performance e Limitações](#-performance-e-limitações)
- [Formato do plano (Planner JSON)](#formato-do-plano-planner-json)
- [🔍 Casos de Uso Reais](#-casos-de-uso-reais)
- [🆚 Comparação com Alternativas](#-comparação-com-alternativas)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [🔒 Segurança](#-segurança)
- [🚀 Deploy (Streamlit Cloud)](#-deploy-streamlit-cloud)
- [🧩 Exemplos de extensão](#-exemplos-de-extensão)
- [❓ FAQs](#-faqs)
- [🤝 Contribuindo](#-contribuindo)
- [🗺️ Roadmap](#️-roadmap)
- [👥 Comunidade](#-comunidade)
- [✨ Autores/Créditos](#-autorescréditos)
- [📄 Licença](#-licença)

---

## ⚡ Quick Start

```bash
# 1. Clone e entre na pasta
git clone https://github.com/MatheusFachel/Bot-Analitico-de-Vendas.git
cd Bot-Analitico-de-Vendas

# 2. Configure credenciais (veja seção "Credenciais do Google")
cp .env.example .env
# Edite .env com suas chaves

# 3. Instale e rode
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
streamlit run main.py
```

**Primeira vez?** Vá direto para [🔐 Credenciais do Google](#-credenciais-do-google-como-obter).

---

## O que este projeto faz

- Consolida dados de vendas de uma pasta do Google Drive.
- Ignora abas agregadas (ex.: “resumo”, “dashboard”) e remove linhas de “Total”.
- Normaliza colunas (acentos, símbolos) e unifica aliases (ex.: `data_venda` → `data`).
- Trata datas (BR day-first e seriais do Excel) e números (`R$`, vírgula/ponto).
- Deduplica registros por chaves conhecidas ou conjunto canônico.
- Responde perguntas via Planner→Executor→Narrativa (LLM só escreve o texto final).

---

## Como funciona (visão de aprendizado)

1) Coleta
	 - Lista arquivos no Drive (suporte a Shared Drives e paginação), lê Sheets/CSV/XLSX.
	 - Usa `openpyxl` para Excel e leitura multi-aba.

2) Saneamento
	 - Normaliza cabeçalhos, mapeia aliases, trata números/datas.
	 - Remove “Total” e ignora abas agregadas para evitar duplicidade/contagem indevida.
	 - Deduplica por ID ou por colunas canônicas.

3) Planejamento e Execução
	 - O LLM recebe um catálogo das colunas/tipos e retorna um plano JSON.
	 - O app traduz esse plano em operações pandas (groupby/aggs/filtros/sort/limit).

4) Narrativa
	 - O LLM recebe um resumo e uma amostra do resultado calculado e redige a resposta.
	 - No chat, exibimos somente o texto (a tabela fica oculta por padrão).

> Diagrama (Mermaid)

```mermaid
flowchart LR
	A[Planilhas no Drive] -->|Sheets/CSV/XLSX| B(Ingestão + Saneamento)
	B --> C[Catálogo de Dados]
	U[Pergunta do Usuário] --> D(Planner - LLM)
	C --> D
	D -->|Plano JSON| E[Executor - pandas]
	E -->|Resultado tabular| F[Narrativa - LLM]
	F -->|Resposta em texto| U
```

---

## Arquitetura (alto nível)

- UI: Streamlit (chat, KPIs, seleção de arquivos)
- Ingestão: Google Drive/Sheets + pandas
- Core: normalização, datas, números, dedup
- IA: Gemini (google-generativeai)
- Orquestração: Planner (LLM) → Executor (pandas) → Narrativa (LLM)

---

## Estrutura do repositório

```
Bot-Analitico-de-Vendas/
├─ main.py                      # App Streamlit: UI, ingestão, Planner→Executor, narrativa
├─ config.py                    # Config segura (via st.secrets/env/.env)
├─ requirements.txt             # Dependências Python
├─ test_models.py               # Utilitário: lista modelos Gemini disponíveis
├─ credentials/
│  └─ service_account.json      # Credenciais Google (não versionar)
├─ .streamlit/
│  ├─ config.toml               # Tema do Streamlit
│  ├─ secrets.toml              # (opcional/local) Segredos do Streamlit
│  └─ secrets.toml.example      # Exemplo de segredos
├─ .env.example                 # Exemplo de variáveis de ambiente
├─ docs/
│  └─ images/                   # (opcional) adicione prints para a documentação
├─ README.md                    # Este arquivo
└─ __pycache__/                 # Gerado automaticamente
```

---

## Requisitos de sistema

- Python 3.10+
- Acesso à internet para APIs do Google e Gemini
- Ambiente com permissão para executar scripts (no Windows PowerShell)
- Recursos: depende do volume de dados; para bases pequenas/médias, máquina comum atende. Se possível, mantenha ~2 GB de RAM livre para conforto.

---

## 🔐 Credenciais do Google (como obter)

### Passo 1: Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative as APIs necessárias:
   - [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
   - [Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)

### Passo 2: Criar Conta de Serviço

1. Navegue para "IAM & Admin" → "Service Accounts"
2. Clique em "Create Service Account"
3. Dê um nome (ex.: `alphabot-reader`)
4. Clique em "Create and Continue"
5. Na tela de permissões, pule (não precisa de roles IAM do projeto)
6. Clique em "Done"

### Passo 3: Baixar credenciais JSON

1. Clique na conta de serviço criada
2. Vá para aba "Keys"
3. Click "Add Key" → "Create new key" → "JSON"
4. O arquivo será baixado automaticamente
5. Renomeie para `service_account.json` e mova para `credentials/`

### Passo 4: Compartilhar pasta do Drive

1. Abra a pasta do Google Drive que contém suas planilhas
2. Copie o ID da pasta da URL:
   ```
   https://drive.google.com/drive/folders/1a2B3c4D5e6F7g8H9i0J
                                          ^^^^^^^^^^^^^^^^^^^
                                          Este é o ID da pasta
   ```
3. Clique em "Compartilhar" (botão superior direito)
4. Cole o **e-mail da conta de serviço** (algo como `alphabot-reader@seu-projeto.iam.gserviceaccount.com`)
5. Dê permissão de **"Leitor"**
6. Clique em "Enviar"

### Passo 5: Obter API Key do Gemini

1. Acesse [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Clique em "Create API Key"
3. Copie a chave gerada

---

## 💡 Exemplos de perguntas

- "Receita por categoria no 1º trimestre de 2024"
- "Top 5 produtos por receita no Sudeste"
- "Variação percentual de receita entre Mar–Mai e Jun–Ago"
- "Ticket médio por região e categoria"
- "Participação de cada categoria na receita total"
- "Produtos com maior crescimento mês a mês"

---

## 📦 Instalação e execução

### Windows PowerShell

1) Abrir a pasta do projeto:
```
PS> cd "C:\Users\SeuUsuario\Desktop\Bot-Analitico-de-Vendas"
```
2) Ambiente virtual:
```
PS> python -m venv .venv
PS> .\.venv\Scripts\Activate.ps1
```
Se necessário:
```
PS> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
PS> .\.venv\Scripts\Activate.ps1
```
3) Dependências:
```
PS> pip install -r requirements.txt
```
4) Configuração (uma das opções): `.streamlit/secrets.toml`, variáveis de ambiente, ou `.env` (ver seção abaixo).
5) Executar:
```
PS> streamlit run main.py
```
Porta alternativa:
```
PS> streamlit run main.py --server.port 8502
```

### Linux/macOS (bash/zsh)

1) Abrir a pasta do projeto:
```
$ cd ~/Desktop/Bot-Analitico-de-Vendas
```
2) Ambiente virtual:
```
$ python3 -m venv .venv
$ source .venv/bin/activate
```
3) Dependências:
```
(.venv) $ pip install -r requirements.txt
```
4) Variáveis (exemplos):
```
(.venv) $ export GEMINI_API_KEY="sua_api_key"
(.venv) $ export GOOGLE_DRIVE_FOLDER_ID="id_da_pasta"
(.venv) $ export GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH="credentials/service_account.json"
```
5) Executar:
```
(.venv) $ streamlit run main.py
```

---

## ⚙️ Configuração detalhada

### Credenciais do Google Service Account

O bot suporta **dois métodos** para fornecer as credenciais:

#### Método 1: JSON completo (recomendado para Streamlit Cloud)

Use a variável `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` com o JSON completo:

**`.streamlit/secrets.toml`:**
```toml
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = """
{
  "type": "service_account",
  "project_id": "seu-projeto-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "alphabot@seu-projeto.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
"""
```

**Arquivo `.env`:**
```env
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS='{"type":"service_account","project_id":"seu-projeto",...}'
```

#### Método 2: Caminho do arquivo (recomendado para desenvolvimento local)

Use a variável `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH` com o caminho do arquivo:

**`.streamlit/secrets.toml`:**
```toml
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"
```

**Arquivo `.env`:**
```env
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH=credentials/service_account.json
```

**Windows PowerShell:**
```powershell
$env:GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "C:\Users\SEU_USER\Desktop\Bot-Analitico-de-Vendas\credentials\service_account.json"
```

**Linux/macOS:**
```bash
export GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH="/home/seu_user/Bot-Analitico-de-Vendas/credentials/service_account.json"
```

---

### Opção A: Streamlit Secrets (recomendado para desenvolvimento local)

Crie o arquivo `.streamlit/secrets.toml`:

```toml
# API do Gemini
GEMINI_API_KEY = "AIzaSyD..."

# ID da pasta do Google Drive
GOOGLE_DRIVE_FOLDER_ID = "1a2B3c4D5e6F7g8H9i0J"

# Credenciais (escolha UM dos dois métodos acima)
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"
```

**Vantagens:** Não aparece em variáveis de ambiente do sistema; fácil de alternar entre projetos.

### Opção B: Variáveis de Ambiente

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY = "AIzaSyD..."
$env:GOOGLE_DRIVE_FOLDER_ID = "1a2B3c4D5e6F7g8H9i0J"
$env:GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"
streamlit run main.py
```

**Linux/macOS:**
```bash
export GEMINI_API_KEY="AIzaSyD..."
export GOOGLE_DRIVE_FOLDER_ID="1a2B3c4D5e6F7g8H9i0J"
export GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH="credentials/service_account.json"
streamlit run main.py
```

**Vantagens:** Funciona para qualquer aplicação; bom para CI/CD.

### Opção C: Arquivo .env

Copie `.env.example` para `.env` e preencha:

```env
GEMINI_API_KEY=AIzaSyD...
GOOGLE_DRIVE_FOLDER_ID=1a2B3c4D5e6F7g8H9i0J
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH=credentials/service_account.json
```

O app carrega automaticamente com `python-dotenv`.

**Vantagens:** Gitignore por padrão; convenção amplamente usada.

### Quick Start

1) Configure `credentials/service_account.json` e as variáveis de ambiente.
2) `pip install -r requirements.txt`
3) `streamlit run main.py`
4) Na sidebar, selecione o modelo Gemini → "Recarregar dados" → faça sua pergunta.

---

## Saída esperada ao iniciar

No terminal, algo como:

```
	You can now view your Streamlit app in your browser.

	Local URL: http://localhost:8501
	Network URL: http://192.168.x.y:8501
```

No navegador, você verá a UI do AlphaBot com KPIs e o campo de chat.

---

## 📊 Performance e Limitações

### Capacidade testada

| Métrica | Limite confortável | Limite máximo testado |
|---------|-------------------|---------------------|
| Arquivos no Drive | ~50 arquivos | ~100 arquivos |
| Linhas totais | ~10.000 linhas | ~50.000 linhas |
| Tempo de carga | 5-15 segundos | 30-60 segundos |
| Tempo de resposta | 2-5 segundos | 10-15 segundos |

### Limitações conhecidas

- **Executor básico:** Suporta `sum`, `groupby`, `sort`, `limit`. Janelas temporais (MoM/YoY) e agregações complexas requerem extensão.
- **Sem persistência:** Dados são carregados a cada sessão (usa cache do Streamlit, mas reiniciar limpa).
- **Dependente de conexão:** Requer internet para Drive API e Gemini API.
- **Formato rígido:** Espera colunas com nomes reconhecíveis (`data`, `produto`, `receita_total`, etc.). Planilhas muito customizadas podem precisar de aliases manuais.
- **Contexto do LLM:** O Planner pode falhar em perguntas muito abstratas ou fora do escopo dos dados.

### Quando NÃO usar este projeto

- Dados > 100k linhas (considere banco de dados + BI dedicado)
- Necessidade de dashboards interativos complexos (use Power BI/Tableau)
- Dados sensíveis sem controle de acesso granular (implemente autenticação robusta)
- Requisitos de auditoria/compliance rigorosos (adicione logs e trilhas)

---

## Formato do plano (Planner JSON)

Exemplo de plano produzido pelo LLM:

```json
{
	"filters": {
		"equals": { "regiao": ["Sudeste", "Sul"] }
	},
	"groupby": ["categoria", "mes"],
	"metrics": [
		{ "name": "receita_total", "agg": "sum" },
		{ "name": "quantidade", "agg": "sum" }
	],
	"sort": { "by": "receita_total", "ascending": false },
	"limit": 50
}
```

Regras suportadas (base):
- filters.equals: filtro de igualdade por coluna (lista de valores)
- groupby: colunas para agregação
- metrics: colunas e a agregação (ex.: sum)
- sort: ordenação do resultado
- limit: recorte final de linhas

> Observação: o Executor atual cobre agregações comuns. Extensões são bem-vindas.

---

## 🔍 Casos de Uso Reais

### Caso 1: Análise de sazonalidade

**Pergunta:** "Compare a receita de eletrônicos entre Q1 e Q2 de 2024"

**Plano gerado:**
```json
{
  "filters": {
    "equals": { "categoria": ["Eletrônicos"] }
  },
  "groupby": ["mes"],
  "metrics": [{ "name": "receita_total", "agg": "sum" }],
  "sort": { "by": "mes", "ascending": true },
  "limit": 6
}
```

**Resultado calculado:**
| mes | receita_total |
|-----|--------------|
| 2024-01 | 125.430,50 |
| 2024-02 | 98.720,30 |
| 2024-03 | 142.890,75 |
| 2024-04 | 156.220,40 |
| 2024-05 | 178.540,90 |
| 2024-06 | 189.760,20 |

**Resposta do bot:**
> "A receita de eletrônicos apresentou crescimento de 51% entre Q1 (R$ 367.041,55) e Q2 (R$ 524.521,50). O mês de junho foi o pico com R$ 189.760,20. Essa tendência sugere aumento da demanda no segundo trimestre, possivelmente por promoções ou lançamentos de produtos."

---

### Caso 2: Identificação de top performers

**Pergunta:** "Top 3 produtos por receita no Sudeste em 2024"

**Plano gerado:**
```json
{
  "filters": {
    "equals": { "regiao": ["Sudeste"] }
  },
  "groupby": ["produto"],
  "metrics": [{ "name": "receita_total", "agg": "sum" }],
  "sort": { "by": "receita_total", "ascending": false },
  "limit": 3
}
```

**Resultado calculado:**
| produto | receita_total |
|---------|--------------|
| Smartphone ProMax | 234.567,80 |
| Laptop X1 | 187.432,50 |
| Monitor 4K | 98.765,40 |

**Resposta do bot:**
> "Os 3 produtos mais vendidos no Sudeste foram: 1) Smartphone ProMax (R$ 234.567,80), 2) Laptop X1 (R$ 187.432,50) e 3) Monitor 4K (R$ 98.765,40). Juntos representam R$ 520.765,70 em receita."

---

### Caso 3: Análise de ticket médio

**Pergunta:** "Ticket médio por categoria"

**Plano gerado:**
```json
{
  "groupby": ["categoria"],
  "metrics": [
    { "name": "receita_total", "agg": "sum" },
    { "name": "quantidade", "agg": "sum" }
  ],
  "sort": { "by": "receita_total", "ascending": false }
}
```

**Resultado calculado:**
| categoria | receita_total | quantidade |
|-----------|--------------|-----------|
| Eletrônicos | 1.245.678,90 | 3.456 |
| Periféricos | 432.109,50 | 8.901 |
| Acessórios | 156.789,30 | 12.345 |

**Resposta do bot:**
> "O ticket médio varia por categoria: Eletrônicos (R$ 360,48), Periféricos (R$ 48,55) e Acessórios (R$ 12,70). Eletrônicos tem o maior valor por venda, indicando produtos de maior valor agregado."

---

## 🆚 Comparação com Alternativas

| Aspecto | AlphaBot | Excel/Planilhas | Power BI | Python Puro |
|---------|----------|-----------------|----------|-------------|
| **Curva de aprendizado** | Baixa (perguntas em PT) | Baixa | Média-Alta | Alta |
| **Automação** | Alta (IA) | Baixa (manual) | Média | Alta |
| **Escalabilidade** | ~50k linhas | ~1M linhas | Milhões | Ilimitada |
| **Custo** | Grátis | Grátis/Licença | Licença | Grátis |
| **Tempo setup** | 15 min | Imediato | 1-2 horas | 30 min-1h |
| **Dashboards** | Não | Limitado | Sim (avançado) | Sim (com libs) |
| **Conversacional** | ✅ | ❌ | ❌ | ❌ |
| **Offline** | ❌ | ✅ | ✅ (desktop) | ✅ |

**Use AlphaBot quando:**
- Quer respostas rápidas sem criar dashboards
- Dados estão em Google Drive/Sheets
- Perguntas variam muito (exploração ad-hoc)
- Equipe prefere linguagem natural

**NÃO use quando:**
- Precisa de dashboards permanentes/interativos
- Dados > 100k linhas
- Requer auditoria/compliance rigoroso
- Necessita de offline

---

## 🛠️ Troubleshooting

- 401/403 nas APIs do Google: confira credenciais, escopos e se a pasta foi compartilhada com a conta de serviço.
- WinError 10053 (conexão abortada): rede/antivírus podem interromper downloads grandes; o app usa retries e download em chunks — tente novamente.
- "Arquivo não encontrado" no Drive: verifique o `GOOGLE_DRIVE_FOLDER_ID` e as permissões.
- `openpyxl` ausente para XLSX: instale (já listado no `requirements.txt`).
- Datas não reconhecidas: o app tenta BR e seriais do Excel; ajuste aliases em `main.py` se necessário.

---

## 🔒 Segurança

### Boas práticas

1. **Nunca versione credenciais**
   - Adicione `credentials/`, `.env`, `.streamlit/secrets.toml` ao `.gitignore`
   - Use `.example` para documentar estrutura

2. **Rotação de credenciais**
   - Gemini API Key: regenere periodicamente no AI Studio
   - Service Account: crie nova conta e delete a antiga no GCP
   - Drive: remova acesso da conta antiga

3. **Princípio do menor privilégio**
   - Conta de serviço: apenas leitura (`Leitor`)
   - Compartilhe somente as pastas necessárias

4. **Logs e auditoria**
   - Ative logging do Streamlit para debug
   - Monitore uso da Gemini API (quotas)

### Checklist de segurança

- [ ] `credentials/service_account.json` está no `.gitignore`
- [ ] `.env` e `.streamlit/secrets.toml` estão no `.gitignore`
- [ ] Conta de serviço tem permissão mínima (Leitor)
- [ ] API Keys não estão hardcoded no código
- [ ] Revisei o histórico do git antes de tornar público

---

## 🚀 Deploy (Streamlit Cloud)

### Passo 1: Preparar repositório

1. Certifique-se que `.gitignore` inclui:
   ```
   credentials/
   .env
   .streamlit/secrets.toml
   __pycache__/
   .venv/
   ```

2. Commit e push para GitHub

### Passo 2: Streamlit Cloud

1. Acesse [share.streamlit.io](https://share.streamlit.io/)
2. Clique em "New app"
3. Selecione seu repositório e branch
4. Main file path: `main.py`

### Passo 3: Configurar Secrets

No Streamlit Cloud, credenciais são configuradas via interface web (não arquivos).

1. Na dashboard do app, vá em **Settings** → **Secrets**
2. Cole o conteúdo abaixo, substituindo pelos seus valores reais:

```toml
# --- API KEY DO GEMINI ---
GEMINI_API_KEY = "AIza..."

# --- ID DA PASTA DO GOOGLE DRIVE ---
GOOGLE_DRIVE_FOLDER_ID = "1AbC2dEf3GhI..."

# --- CREDENCIAIS DO GOOGLE SERVICE ACCOUNT (JSON completo) ---
# Abra seu arquivo service_account.json, copie TODO o conteúdo e cole entre as aspas triplas abaixo
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS = """
{
  "type": "service_account",
  "project_id": "seu-projeto-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nSUA_CHAVE_PRIVADA_COMPLETA\n-----END PRIVATE KEY-----\n",
  "client_email": "alphabot@seu-projeto.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
"""
```

**⚠️ Importante:**
- **NÃO** use `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH` no Cloud (caminhos de arquivo não funcionam)
- Copie o JSON **completo** do seu arquivo `service_account.json`
- Mantenha a formatação JSON intacta (chaves, vírgulas, quebras de linha)
- As aspas triplas (`"""`) são obrigatórias para textos multilinha no TOML

### Passo 4: Deploy

Clique em "Deploy" e aguarde. A URL pública será gerada automaticamente.

### Limitações no Cloud

- Memória limitada (1 GB free tier)
- Timeout de requisições (pode afetar cargas grandes)
- Considere caching agressivo para reduzir chamadas de API

---

## 🧩 Exemplos de extensão

1) Adicionar um alias de coluna em `main.py` (função `_standardize_dataframe`):

```python
alias_map = {
		# ...
		'data': {'data', 'date', 'dt', 'data_venda', 'emissao', 'data_nf', 'dt_emissao'},
		# acrescente aqui um novo nome que apareça na sua planilha
}
```

2) Suportar nova agregação no Executor (ex.: média) em `_execute_plan`:

```python
agg_spec = {}
for m in metrics:
		if isinstance(m, dict) and m.get('name') in work.columns:
				agg = m.get('agg', 'sum')
				if agg not in {'sum', 'mean', 'max', 'min'}:
						agg = 'sum'
				agg_spec[m['name']] = agg
```

3) Expor variável de ambiente opcional no README/`.env.example` (ex.: porta do Streamlit):

```
STREAMLIT_SERVER_PORT=8502
```

---

## ❓ FAQs

### Posso usar com outras fontes além do Google Drive?

Sim! Você pode adaptar a função `load_sales_data` em `main.py` para ler de:
- Arquivos locais (`pd.read_csv`, `pd.read_excel`)
- Bancos de dados (PostgreSQL, MySQL via SQLAlchemy)
- APIs REST (requests + pandas)

A estrutura Planner→Executor funciona independentemente da fonte.

### Funciona offline?

Não completamente. Você precisa de internet para:
- Drive/Sheets API (ingestão)
- Gemini API (planner e narrativa)

Alternativa offline: carregue dados localmente e use um LLM local (Ollama, LLaMA.cpp) em vez do Gemini.

### Como adicionar novos tipos de visualização?

O projeto foca em respostas textuais. Para gráficos, você pode:
1. Usar `st.line_chart`, `st.bar_chart` do Streamlit após `_execute_plan`
2. Integrar Plotly/Altair no executor
3. Criar um modo "visual" que exibe tabela + gráfico ao lado da narrativa

### Posso usar com dados que não sejam de vendas?

Sim! O projeto é agnóstico ao domínio. Ajuste:
- Aliases de colunas em `_standardize_dataframe`
- Prompt do Planner para refletir o novo contexto
- KPIs na UI

Funciona para: RH (funcionários), Logística (entregas), Marketing (campanhas), etc.

### O LLM vê meus dados?

Sim, mas de forma limitada:
- O Planner recebe um **catálogo** (nomes de colunas, tipos, ranges)
- A Narrativa recebe uma **amostra** (até 100 linhas) e resumos

O app **não envia** a planilha completa. Ainda assim, se os dados forem sensíveis, considere:
- LLM local (Ollama)
- Anonimizar dados antes do envio

### Por que o bot não responde algumas perguntas?

Possíveis causas:
1. **Planner falhou:** pergunta muito complexa/abstrata
2. **Dados ausentes:** colunas necessárias não existem
3. **Executor limitado:** operação não suportada (ex.: percentis, window functions)

Solução: reformule a pergunta ou estenda o executor.

### Quantos usuários simultâneos suporta?

Depende do deploy:
- **Local:** 1 usuário (você)
- **Streamlit Cloud (free):** ~10-50 usuários (com caching)
- **Server dedicado:** escala horizontalmente

Cada sessão carrega dados independentemente. Use cache global (`@st.cache_resource`) para compartilhar.

---

## 🤝 Contribuindo

1. Abra uma issue descrevendo o objetivo e o contexto
2. Faça fork e crie uma branch temática
3. Abra um PR com descrição clara, prints e checklist de testes locais

Padrões sugeridos:
- Código Python com tipagem leve e funções pequenas
- Comentários explicando decisões e trade-offs
- README e exemplos atualizados

---

## 🗺️ Roadmap

### v1.1 (próxima release)
- [ ] Métrica "Linhas brutas lidas" na sidebar
- [ ] Suporte a filtros por data no Executor
- [ ] Exportação CSV do resultado calculado

### v1.2
- [ ] Janelas temporais (MoM/YoY) no Executor
- [ ] Gráficos opcionais (Plotly) para respostas visuais
- [ ] Conector de arquivos locais

### v2.0 (futuro)
- [ ] Autenticação multi-usuário
- [ ] Histórico de perguntas/respostas
- [ ] LLM local (Ollama) como alternativa ao Gemini
- [ ] Suporte a bancos de dados (PostgreSQL, MySQL)

Veja issues e vote em features: [GitHub Issues](https://github.com/MatheusFachel/Bot-Analitico-de-Vendas/issues)

---

## 👥 Comunidade

- Issues: https://github.com/MatheusFachel/Bot-Analitico-de-Vendas/issues
- Discussões: https://github.com/MatheusFachel/Bot-Analitico-de-Vendas/discussions
- Código de Conduta: baseado em https://www.contributor-covenant.org/

**Precisa de ajuda?** Abra uma issue com a tag `question`.

---

## ✨ Autores/Créditos

- Matheus Fachel ([@MatheusFachel](https://github.com/MatheusFachel)) – Criador e mantenedor
- Contribuidores – Obrigado pelos PRs/issues! 🙏

**Tecnologias usadas:**
- [Streamlit](https://streamlit.io/) - Framework web
- [Google Gemini](https://deepmind.google/technologies/gemini/) - Modelo de linguagem
- [pandas](https://pandas.pydata.org/) - Manipulação de dados
- [Google APIs](https://developers.google.com/) - Drive e Sheets

---

## 📄 Licença

Este projeto é open source e fornecido “como está”, para fins educacionais. Avalie e adapte ao seu contexto antes de uso em produção.
