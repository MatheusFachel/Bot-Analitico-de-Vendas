"""
Módulo de estilos CSS para a aplicação AlphaBot - Analista de Vendas

Este módulo contém todas as definições de estilo CSS para a interface
do Streamlit, organizadas de forma modular e reutilizável.
"""

def get_main_styles():
    """
    Retorna o CSS principal da aplicação.
    
    Returns:
        str: String contendo todo o CSS da aplicação
    """
    return """
    <style>
    /* ===== LOGO MINIMALISTA COM SUBLINHADO ANIMADO ===== */
    
    h1 {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        text-align: center !important;
        color: #F3F4F6 !important;
        margin: 2rem 0 !important;
        position: relative !important;
        letter-spacing: 2px !important;
    }

    h1::before {
        content: '';
        position: absolute;
        bottom: -15px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 4px;
        background: linear-gradient(90deg, #00C851, #0066FF);
        border-radius: 2px;
        animation: underline-grow 2s ease-out forwards;
    }

    @keyframes underline-grow {
        to { width: 300px; }
    }
    
    /* ===== MÉTRICAS PREMIUM COM CARDS E GRADIENTES - FORÇADO ===== */
    
    /* Seletores ultra-específicos para métricas */
    section[data-testid="stMain"] div[data-testid="metric-container"],
    .main div[data-testid="metric-container"],
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1A1D23 0%, #2A2F38 100%) !important;
        border: 1px solid #404854 !important;
        border-left: 4px solid #00C851 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin: 0.5rem 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        transition: all 0.3s ease !important;
    }

    section[data-testid="stMain"] div[data-testid="metric-container"]:hover,
    .main div[data-testid="metric-container"]:hover,
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.4) !important;
        border-left-color: #0066FF !important;
    }

    /* Valores das métricas - ultra-específico */
    section[data-testid="stMain"] div[data-testid="metric-container"] [data-testid="metric-value"],
    .main div[data-testid="metric-container"] [data-testid="metric-value"],
    div[data-testid="metric-container"] [data-testid="metric-value"],
    div[data-testid="metric-container"] > div > div {
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        color: #00C851 !important;
        text-shadow: 0 0 15px rgba(0, 200, 81, 0.5) !important;
    }

    /* Labels das métricas - ultra-específico */
    section[data-testid="stMain"] div[data-testid="metric-container"] [data-testid="metric-label"],
    .main div[data-testid="metric-container"] [data-testid="metric-label"],
    div[data-testid="metric-container"] [data-testid="metric-label"],
    div[data-testid="metric-container"] > div:first-child {
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #D1D5DB !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Força estilo em qualquer métrica do Streamlit */
    .metric-container,
    [class*="metric"],
    .stMetric {
        background: linear-gradient(135deg, #1A1D23 0%, #2A2F38 100%) !important;
        border: 1px solid #404854 !important;
        border-left: 4px solid #00C851 !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        margin: 0.5rem 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    
    /* ===== ESTILOS PRINCIPAIS DO CHAT ===== */
    
    /* Destaque MUITO visível na barra de conversa */
    .stChatFloatingInputContainer, .stChatInputContainer { 
        border: 3px solid #00C851 !important; 
        border-radius: 15px !important;
        box-shadow: 
            0 0 15px rgba(0,200,81,0.6) !important,
            0 0 30px rgba(0,200,81,0.4) !important,
            0 0 60px rgba(0,200,81,0.2) !important,
            inset 0 0 15px rgba(0,200,81,0.1) !important;
        background: linear-gradient(145deg, #1a1a1a, #2d2d2d) !important;
        animation: pulse-glow 2s ease-in-out infinite alternate !important;
        max-width: 75% !important;
        width: 75% !important;
        margin: 0 auto !important;
    }
    
    /* Força redução da largura do container do chat */
    div[data-testid="stChatInputContainer"] {
        max-width: 75% !important;
        width: 75% !important;
        margin: 0 auto !important;
    }
    
    /* Container principal do chat input */
    .stChatInput {
        max-width: 75% !important;
        width: 75% !important;
        margin: 0 auto !important;
    }
    
    /* Força container geral da área de chat a ser menor */
    section[data-testid="stMain"] > div > div > div:last-child {
        max-width: 75% !important;
        margin: 0 auto !important;
    }
    
    /* Alvo muito específico para o input do chat */
    div[data-baseweb="input"] {
        max-width: 100% !important;
    }
    
    /* ===== ANIMAÇÕES ===== */
    
    @keyframes pulse-glow {
        0% { box-shadow: 0 0 15px rgba(0,200,81,0.6), 0 0 30px rgba(0,200,81,0.4), 0 0 60px rgba(0,200,81,0.2); }
        100% { box-shadow: 0 0 25px rgba(0,200,81,0.8), 0 0 40px rgba(0,200,81,0.6), 0 0 80px rgba(0,200,81,0.3); }
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    
    /* ===== ESTILOS DO CHAT ===== */
    
    .stChatInput > div > div textarea {
        font-size: 1.2rem !important;
        background: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }
    
    .stChatInput > div > div textarea::placeholder {
        color: #FFFFFF !important;
        opacity: 0.9 !important;
        font-weight: 400 !important;
    }
    
    /* Área do chat com mais destaque */
    .stChatMessage {
        border-radius: 10px !important;
        margin: 0.8rem 0 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    /* Botão de envio com neon */
    button[data-testid="chatSubmitButton"] {
        background: linear-gradient(145deg, #00C851, #00A136) !important;
        border: none !important;
        border-radius: 50% !important;
        box-shadow: 0 0 15px rgba(0,200,81,0.5) !important;
    }
    
    /* CSS específico apenas para elementos internos do chat input */
    .stChatInputContainer > div, 
    .stChatInput > div,
    div[data-testid="stChatInputContainer"] > div {
        background: linear-gradient(145deg, #1a1a1a, #2d2d2d) !important;
        border-color: #00C851 !important;
    }
    
    /* ===== ESTILOS BÁSICOS DA SIDEBAR ===== */
    
    /* Sidebar estilizada para lista de arquivos */
    section[data-testid="stSidebar"] .stMarkdown ul {
        list-style: none; 
        padding-left: 0;
    }
    
    section[data-testid="stSidebar"] li { 
        margin: .25rem 0; 
        padding: .35rem .5rem; 
        background: #1f2023; 
        border-radius: .35rem;
    }
    
    section[data-testid="stSidebar"] li small { 
        color: #bbb; 
    }
    </style>
    """

def get_sidebar_premium_styles():
    """
    Retorna os estilos premium da sidebar.
    
    Returns:
        str: String contendo o CSS premium da sidebar
    """
    return """
    <style>
    /* ============ SIDEBAR PREMIUM DESIGN ============ */
    
    /* Cores por seção */
    :root {
        --color-config: #0066FF;
        --color-filter: #F59E0B;
        --color-files: #10B981;
        --color-data: #6B46C1;
        --color-stats: #6B7280;
    }
    
    /* Container geral da sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0B0D 0%, #1A1D23 100%) !important;
        border-right: 1px solid #2A2F38 !important;
    }
    
    /* Cards para cada seção */
    .sidebar-card {
        background: linear-gradient(135deg, #1A1D23 0%, #2A2F38 100%);
        border: 1px solid #404854;
        border-radius: 12px;
        padding: 1rem;
        margin: 0.75rem 0;
        position: relative;
        transition: all 0.3s ease;
        border-left: 4px solid transparent;
    }
    
    .sidebar-card:hover {
        border-color: #6B7280;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        transform: translateX(2px);
    }
    
    /* Cards específicos por seção */
    .card-config {
        border-left-color: var(--color-config) !important;
    }
    
    .card-filter {
        border-left-color: var(--color-filter) !important;
    }
    
    .card-files {
        border-left-color: var(--color-files) !important;
    }
    
    .card-data {
        border-left-color: var(--color-data) !important;
    }
    
    .card-stats {
        border-left-color: var(--color-stats) !important;
    }
    
    /* Títulos das seções com ícones */
    .sidebar-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        color: #F3F4F6;
    }
    
    .title-config { color: var(--color-config); }
    .title-filter { color: var(--color-filter); }
    .title-files { color: var(--color-files); }
    .title-data { color: var(--color-data); }
    .title-stats { color: var(--color-stats); }
    
    /* ===== BOTÕES PREMIUM ===== */
    
    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(135deg, #0066FF 0%, #3385FF 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        color: white !important;
        font-weight: 500 !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
        box-shadow: 0 2px 4px rgba(0, 102, 255, 0.2) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s ease;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 102, 255, 0.4) !important;
        background: linear-gradient(135deg, #3385FF 0%, #0066FF 100%) !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover::before {
        left: 100%;
    }
    
    /* Botões secundários */
    .btn-secondary {
        background: transparent !important;
        border: 1px solid #6B7280 !important;
        color: #D1D5DB !important;
    }
    
    .btn-secondary:hover {
        border-color: #9CA3AF !important;
        background: rgba(156, 163, 175, 0.1) !important;
    }
    
    /* ===== FORMULÁRIOS ESTILIZADOS ===== */
    
    /* Selectbox e Multiselect estilizados */
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stMultiSelect > div > div {
        background: #2A2F38 !important;
        border: 1px solid #404854 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox > div > div:hover,
    section[data-testid="stSidebar"] .stMultiSelect > div > div:hover {
        border-color: #0066FF !important;
        box-shadow: 0 0 0 1px rgba(0, 102, 255, 0.3) !important;
    }
    
    /* Checkboxes customizados */
    section[data-testid="stSidebar"] .stCheckbox > label {
        background: rgba(42, 47, 56, 0.5) !important;
        border-radius: 6px !important;
        padding: 0.5rem !important;
        margin: 0.25rem 0 !important;
        transition: all 0.2s ease !important;
        border-left: 3px solid transparent !important;
    }
    
    section[data-testid="stSidebar"] .stCheckbox > label:hover {
        background: rgba(42, 47, 56, 0.8) !important;
        border-left-color: var(--color-files) !important;
    }
    
    /* ===== BADGES E INDICADORES ===== */
    
    /* Status badges */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10B981;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.875rem;
        font-weight: 500;
        color: #10B981;
        margin: 2px;
    }
    
    .status-badge-warning {
        background: rgba(245, 158, 11, 0.1);
        border-color: #F59E0B;
        color: #F59E0B;
    }
    
    .status-badge-info {
        background: rgba(0, 102, 255, 0.1);
        border-color: #0066FF;
        color: #3385FF;
    }
    
    /* Progress bar para seleção de arquivos */
    .file-progress {
        width: 100%;
        height: 4px;
        background: #404854;
        border-radius: 2px;
        overflow: hidden;
        margin: 8px 0;
    }
    
    .file-progress-bar {
        height: 100%;
        background: linear-gradient(90deg, var(--color-files), #34D399);
        border-radius: 2px;
        transition: width 0.3s ease;
    }
    
    /* ===== ELEMENTOS ESPECIAIS ===== */
    
    /* Expander personalizado */
    section[data-testid="stSidebar"] .streamlit-expander {
        border: 1px solid #404854 !important;
        border-radius: 8px !important;
        background: rgba(42, 47, 56, 0.3) !important;
    }
    
    section[data-testid="stSidebar"] .streamlit-expander > summary {
        background: rgba(42, 47, 56, 0.5) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        color: #D1D5DB !important;
    }
    
    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .tooltip::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        background: #1A1D23;
        color: #F3F4F6;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.875rem;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s ease;
        border: 1px solid #404854;
        z-index: 1000;
    }
    
    .tooltip:hover::after {
        opacity: 1;
    }
    
    /* Seções colapsáveis */
    .collapsible-section {
        margin: 1rem 0;
    }
    
    .collapsible-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.75rem;
        background: rgba(42, 47, 56, 0.5);
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
        border-left: 4px solid transparent;
    }
    
    .collapsible-header:hover {
        background: rgba(42, 47, 56, 0.8);
    }
    
    .collapsible-content {
        padding: 1rem;
        background: rgba(26, 29, 35, 0.5);
        border-radius: 0 0 8px 8px;
        border-top: 1px solid #404854;
    }
    
    /* ===== CLASSES DE ANIMAÇÃO ===== */
    
    .animate-slide-down {
        animation: slideDown 0.3s ease-out;
    }
    
    .animate-fade-in {
        animation: fadeIn 0.3s ease-out;
    }
    
    /* ===== RESPONSIVIDADE DA SIDEBAR ===== */
    
    @media (max-width: 768px) {
        .sidebar-card {
            margin: 0.5rem 0;
            padding: 0.75rem;
        }
        
        .sidebar-title {
            font-size: 1rem;
        }
    }
    
    /* ===== SCROLLBAR DA SIDEBAR ===== */
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar {
        width: 6px;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-track {
        background: #1A1D23;
    }
    
    section[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #0066FF, #3385FF);
        border-radius: 3px;
    }
    </style>
    """

def get_all_styles():
    """
    Retorna todos os estilos combinados da aplicação.
    
    Returns:
        str: String contendo todo o CSS da aplicação
    """
    return get_main_styles() + get_sidebar_premium_styles()

# Funções de conveniência para aplicar estilos
def apply_main_styles(st):
    """
    Aplica os estilos principais usando st.markdown.
    
    Args:
        st: Módulo streamlit
    """
    st.markdown(get_main_styles(), unsafe_allow_html=True)

def apply_sidebar_styles(st):
    """
    Aplica os estilos da sidebar usando st.markdown.
    
    Args:
        st: Módulo streamlit
    """
    st.markdown(get_sidebar_premium_styles(), unsafe_allow_html=True)

def apply_all_styles(st):
    """
    Aplica todos os estilos usando st.markdown.
    
    Args:
        st: Módulo streamlit
    """
    st.markdown(get_all_styles(), unsafe_allow_html=True)