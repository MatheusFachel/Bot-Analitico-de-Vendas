# AlphaBot – Projeto Educacional de Análise de Vendas com IA (Open Source)

Este repositório é um projeto didático para estudar e praticar:

- Ingestão de dados de planilhas (Google Drive/Sheets, CSV, XLSX)
- Limpeza e padronização de dados (datas, números, aliases de colunas, deduplicação)
- Criação de uma interface conversacional com Streamlit
- Uso de um modelo de linguagem (Gemini) de forma responsável: planejamento → execução → narrativa

O objetivo é ensinar e servir de base para evoluções. Sinta-se à vontade para forkar, abrir issues e enviar PRs. O foco aqui é ser legível, extensível e reproduzível.

---

## O que este projeto faz

- Consolida dados de vendas a partir de uma pasta do Google Drive
- Ignora abas agregadas (ex.: “resumo”, “dashboard”) e remove linhas de “Total”
- Normaliza colunas (acentos, símbolos) e unifica aliases (ex.: `data_venda` → `data`)
- Trata datas (inclui BR day-first e seriais do Excel) e números (R$, vírgulas/pontos)
- Deduplica registros com base em chaves conhecidas ou em um conjunto canônico
- Responde perguntas em linguagem natural com um fluxo Planner→Executor→Narrativa
  - Planner (LLM): cria um plano JSON (filtros, groupby, métricas)
  - Executor (pandas): executa o plano com DataFrame
  - Narrativa (LLM): gera o texto final usando apenas os resultados calculados

---

## Galeria (adicione suas imagens)

> Coloque prints reais quando tiver: isso ajuda quem está chegando agora a entender o fluxo.

![Overview – KPIs](docs/images/kpi_overview.png)

![Chat – Pergunta e resposta](docs/images/chat_answer.png)

![Sidebar – Configurações](docs/images/sidebar_config.png)

---

## Como funciona (visão de aprendizado)

1) Coleta
	- Lista arquivos de uma pasta no Google Drive (Sheets/CSV/XLSX) com paginação e suporte a Shared Drives.
	- Lê várias abas e formatos; usa `openpyxl` para Excel.

2) Saneamento
	- Normaliza cabeçalhos, mapeia aliases e trata números/datas de forma robusta.
	- Remove linhas de “Total” e ignora abas agregadas (para não contar dashboards/relatórios).
	- Deduplica registros por ID (quando existe) ou por um conjunto de colunas.

3) Planejamento e Execução
	- O LLM recebe um catálogo de dados (colunas, tipos, métricas/dimensões) e devolve um plano JSON.
	- O app executa o plano em pandas e gera um resultado tabular.

4) Narrativa
	- O LLM recebe a amostra do resultado e um resumo e escreve a resposta em português.
	- Na conversa, somente o texto é exibido (a tabela fica nos bastidores por padrão).

---

## Arquitetura (alto nível)

- UI: Streamlit (chat, KPIs, seleção de arquivos)
- Ingestão: Google Drive/Sheets + pandas
- Core de dados: normalização, datas, números, dedup, estatísticas
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
│  └─ images/                   # Coloque aqui suas imagens para o README
├─ README.md                    # Este arquivo
└─ __pycache__/                 # Gerado automaticamente
```

---

## Tecnologias

- Python 3.10+
- Streamlit
- pandas, openpyxl
- google-api-python-client (Drive/Sheets)
- google-generativeai (Gemini)
- python-dotenv (opcional)

---

## Instalação e execução (Windows PowerShell)

1) Pré-requisitos
	- Python 3.10+ no PATH
	- Conta de serviço com Drive/Sheets API ativas
	- `credentials/service_account.json` baixado
	- API Key do Gemini

2) Abra a pasta do projeto

```
PS> cd "C:\Users\SeuUsuario\Desktop\Bot-Analitico-de-Vendas"
```

3) Ambiente virtual

```
PS> python -m venv .venv
PS> .\.venv\Scripts\Activate.ps1
```

Se necessário:

```
PS> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
PS> .\.venv\Scripts\Activate.ps1
```

4) Dependências

```
PS> pip install -r requirements.txt
```

5) Configuração (uma das opções abaixo)

Opção A) `.streamlit/secrets.toml`

```
[general]
GEMINI_API_KEY = "sua_api_key"
GOOGLE_DRIVE_FOLDER_ID = "id_da_pasta_no_drive"
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"
```

Opção B) Variáveis de ambiente (PowerShell)

```
PS> $env:GEMINI_API_KEY = "sua_api_key"; $env:GOOGLE_DRIVE_FOLDER_ID = "id_da_pasta"; $env:GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH = "credentials/service_account.json"
```

Opção C) `.env` (copie de `.env.example`)

```
GEMINI_API_KEY=sua_api_key
GOOGLE_DRIVE_FOLDER_ID=id_da_pasta_no_drive
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_PATH=credentials/service_account.json
```

6) Rodar

```
PS> streamlit run main.py
```

Porta alternativa:

```
PS> streamlit run main.py --server.port 8502
```

7) Uso básico
	- Selecione o modelo Gemini na sidebar e clique em “Recarregar dados”.
	- Selecione os arquivos. O app saneia e deduplica automaticamente.
	- Faça perguntas no chat. A resposta é textual; a tabela fica oculta.

8) Solução de problemas
	- WinError 10053: rede instável/antivírus. O app faz retries e usa download em chunks; tente novamente.
	- Menos linhas que o “bruto”: foi deduplicado ou removido “Total”/abas agregadas.
	- Datas estranhas: já tratamos BR e seriais do Excel; pode ajustar aliases em `main.py`.

---

## Decisões de projeto (educacional)

- “Planner→Executor” para separar raciocínio (LLM) de execução (pandas)
- Nunca enviar planilhas inteiras ao LLM: usamos resumo e amostra segura
- Saneamento automático (abas agregadas, “Total”, dedup) para evitar números inflados
- UI minimalista: no chat, responder só com texto

Limitações atuais
- O executor cobre operações agregadas comuns (sum, groupby, sort, limit). Casos avançados (janelas, MoM/YoY) podem exigir extensão.
- A qualidade da narrativa depende do modelo escolhido e do contexto fornecido.

---

## Contribuindo

Contribuições são bem-vindas! Sugestões de melhoria, correções e novas integrações:

1. Abra uma issue descrevendo o objetivo e contexto
2. Crie um fork e uma branch temática
3. Abra um PR com descrição clara, prints e checklist de testes locais

Padrões sugeridos
- Código Python com tipagem leve e funções pequenas
- Comentários explicando decisões e trade-offs
- Manter README e exemplos atualizados

---

## Roadmap

- Métrica “Linhas brutas lidas” na sidebar
- Suporte a janelas temporais e comparativos automáticos (MoM/YoY)
- Exportação opcional do resultado calculado (CSV)
- Conector de arquivos locais (além de Drive/Sheets)

---

## Licença

Este projeto é open source e fornecido “como está”, para fins educacionais. Avalie e adapte para o seu contexto antes de uso em produção.
