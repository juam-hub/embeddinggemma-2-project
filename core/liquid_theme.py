"""
Guía de Diseño: Criatura Líquida — Sistema Visual y Motor de Animaciones
Estética de vanguardia (Active Theory / Resn / Basement Studio / Locomotive)
Paleta estricta:
  Abisal:           #061A20 (Fondo base casi negro)
  Mercurio:         #CFD8DA (Texto y cromo líquido)
  Naranja venenoso: #FF5B14 (Acento principal potente)
  Lima ácida:       #C6FF3D (Acento de apoyo, destellos y estados activos)
Tipografía:
  Bricolage Grotesque (titulares elásticos y cuerpo)
  Instrument Serif en cursiva (susurros y anotaciones)
"""

def get_liquid_creature_css() -> str:
    """Retorna la hoja de estilo completa del sistema Criatura Líquida."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..125,200..800&family=Instrument+Serif:ital@0;1&display=swap');

    /* ═══════════════════════  VARIABLES DEL SISTEMA  ═══════════════════════ */
    :root {
        --abisal:          #061A20;
        --abisal-profundo: #030D10;
        --abisal-superficie: #0B252E;
        --abisal-organo:   rgba(6, 26, 32, 0.88);
        --mercurio:        #CFD8DA;
        --mercurio-tenue:  rgba(207, 216, 218, 0.65);
        --naranja:         #FF5B14;
        --naranja-glow:    rgba(255, 91, 20, 0.35);
        --lima:            #C6FF3D;
        --lima-glow:       rgba(198, 255, 61, 0.35);
        
        /* Cromo Líquido: Mercurio con reflejos abisales y bordes naranja/lima */
        --cromo-metal:     linear-gradient(135deg, #CFD8DA 0%, #061A20 50%, #CFD8DA 85%, #FF5B14 100%);
        --cromo-borde:     linear-gradient(90deg, #FF5B14 0%, #CFD8DA 50%, #C6FF3D 100%);
        --cromo-reflejo:   radial-gradient(circle at 30% 30%, rgba(207,216,218,0.9) 0%, rgba(6,26,32,0.85) 60%, rgba(255,91,20,0.4) 100%);

        --font-sans:       'Bricolage Grotesque', -apple-system, sans-serif;
        --font-whisper:    'Instrument Serif', Georgia, serif;
    }

    /* ═══════════════════════  CANVAS BASE Y PROFUNDIDAD  ═══════════════════════ */
    html, body, .stApp, [data-testid="stAppViewContainer"] {
        background-color: var(--abisal) !important;
        background-image: 
            radial-gradient(circle at 12% 18%, rgba(255, 91, 20, 0.08) 0%, transparent 40%),
            radial-gradient(circle at 88% 82%, rgba(198, 255, 61, 0.06) 0%, transparent 35%),
            radial-gradient(circle at 50% 50%, rgba(207, 216, 218, 0.03) 0%, transparent 60%),
            radial-gradient(ellipse at bottom, var(--abisal-profundo) 0%, var(--abisal) 100%) !important;
        color: var(--mercurio) !important;
        font-family: var(--font-sans) !important;
        overflow-x: hidden;
        cursor: default;
    }

    /* Ocultar barra superior genérica de Streamlit */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 0px !important;
        visibility: hidden !important;
    }

    .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0.8rem 1.4rem 2rem !important;
        max-width: 100% !important;
    }

    /* ═══════════════════════  TIPOGRAFÍA VARIABLE Y ELÁSTICA  ═══════════════════════ */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-sans) !important;
        color: var(--mercurio) !important;
        font-variation-settings: 'wght' 700, 'wdth' 105;
        letter-spacing: -0.04em !important;
        margin: 0;
    }

    .whisper-text {
        font-family: var(--font-whisper) !important;
        font-style: italic !important;
        font-weight: 400 !important;
        color: var(--mercurio) !important;
        opacity: 0.85;
    }

    /* Titular gigante recortado contra los bordes */
    .titular-gigante {
        font-family: var(--font-sans) !important;
        font-size: clamp(3.5rem, 8vw, 8.5rem);
        font-variation-settings: 'wght' 800, 'wdth' 125;
        line-height: 0.85;
        letter-spacing: -0.06em;
        text-transform: uppercase;
        color: var(--mercurio);
        margin: -10px -20px 10px -20px;
        white-space: nowrap;
        overflow: hidden;
        user-select: none;
        pointer-events: none;
        opacity: 0.18;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }

    .titular-gigante span.accent-orange {
        color: var(--naranja);
        opacity: 0.9;
    }

    .titular-gigante span.accent-lime {
        color: var(--lima);
        opacity: 0.9;
    }

    /* ═══════════════════════  ÓRGANOS FLOTANTES (MAPA DE CRIATURA)  ═══════════════════════ */
    .creature-organ {
        background: var(--abisal-organo);
        border: 1.5px solid rgba(207, 216, 218, 0.2);
        border-radius: 28px 12px 32px 16px;
        padding: 1.4rem;
        box-shadow: 
            0 20px 45px rgba(3, 13, 16, 0.7),
            inset 0 1px 0 rgba(207, 216, 218, 0.25),
            0 0 25px rgba(255, 91, 20, 0.08);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        position: relative;
        transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s ease, border-color 0.3s ease;
        margin-bottom: 1.2rem;
    }

    .creature-organ:hover {
        border-color: var(--naranja);
        box-shadow: 
            0 25px 60px rgba(3, 13, 16, 0.85),
            inset 0 1px 2px rgba(207, 216, 218, 0.4),
            0 0 35px var(--naranja-glow);
    }

    /* Detalle cromado líquido en la esquina del órgano */
    .creature-organ::before {
        content: '';
        position: absolute;
        top: -2px;
        left: 24px;
        width: 48px;
        height: 4px;
        background: var(--cromo-borde);
        border-radius: 4px;
        box-shadow: 0 0 10px var(--lima);
    }

    /* ═══════════════════════  ZONA TRANQUILA (QUIET ZONE)  ═══════════════════════ */
    .quiet-zone {
        background: rgba(6, 26, 32, 0.96) !important;
        border: 1px solid rgba(207, 216, 218, 0.3) !important;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        color: var(--mercurio) !important;
        font-family: var(--font-sans) !important;
    }

    /* ═══════════════════════  SIDEBAR / VIENTRE INGESTOR  ═══════════════════════ */
    section[data-testid="stSidebar"] {
        background-color: var(--abisal-profundo) !important;
        border-right: 2px solid rgba(207, 216, 218, 0.15) !important;
        box-shadow: 12px 0 35px rgba(3, 13, 16, 0.9) !important;
        background-image: 
            radial-gradient(ellipse at top left, rgba(255, 91, 20, 0.08) 0%, transparent 60%),
            radial-gradient(circle at 50% 80%, rgba(198, 255, 61, 0.04) 0%, transparent 50%) !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding: 1.2rem 1rem !important;
    }

    /* Píldoras de órgano y cromo */
    .organ-badge {
        font-family: var(--font-sans);
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 4px 10px;
        border-radius: 100px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(207, 216, 218, 0.08);
        border: 1px solid rgba(207, 216, 218, 0.25);
        color: var(--mercurio);
        margin-bottom: 6px;
    }

    .organ-badge.active-orange {
        background: rgba(255, 91, 20, 0.18);
        border-color: var(--naranja);
        color: #FFF;
        box-shadow: 0 0 12px var(--naranja-glow);
    }

    .organ-badge.active-lime {
        background: rgba(198, 255, 61, 0.15);
        border-color: var(--lima);
        color: var(--lima);
        box-shadow: 0 0 12px var(--lima-glow);
    }

    /* ═══════════════════════  CHAT Y MENSAJES LÍQUIDOS  ═══════════════════════ */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.6rem 0 !important;
    }

    .chat-bubble-user {
        background: linear-gradient(135deg, rgba(255, 91, 20, 0.2) 0%, rgba(6, 26, 32, 0.9) 100%);
        border: 1.5px solid var(--naranja);
        border-radius: 20px 20px 4px 20px;
        padding: 1rem 1.3rem;
        color: var(--mercurio);
        font-family: var(--font-sans);
        font-size: 0.98rem;
        line-height: 1.5;
        box-shadow: 0 8px 24px rgba(255, 91, 20, 0.15);
        position: relative;
    }

    .chat-bubble-assistant {
        background: linear-gradient(145deg, rgba(11, 37, 46, 0.85) 0%, rgba(6, 26, 32, 0.95) 100%);
        border: 1.5px solid rgba(207, 216, 218, 0.25);
        border-left: 4px solid var(--lima);
        border-radius: 20px 20px 20px 4px;
        padding: 1.2rem 1.4rem;
        color: var(--mercurio);
        font-family: var(--font-sans);
        font-size: 0.98rem;
        line-height: 1.6;
        box-shadow: 0 10px 30px rgba(3, 13, 16, 0.6);
        position: relative;
    }

    .chat-bubble-assistant:hover {
        border-color: rgba(207, 216, 218, 0.45);
        border-left-color: var(--lima);
    }

    /* Citas interactivas líquidas */
    .liquid-citation-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: var(--font-sans);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        color: var(--mercurio);
        background: rgba(6, 26, 32, 0.9);
        border: 1px solid var(--lima);
        border-radius: 8px;
        padding: 5px 11px;
        margin: 4px 6px 4px 0;
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        box-shadow: 0 2px 8px rgba(198, 255, 61, 0.12);
    }

    .liquid-citation-pill:hover {
        background: var(--lima);
        color: var(--abisal);
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 0 15px var(--lima);
    }

    .liquid-citation-pill.visual-citation {
        border-color: var(--naranja);
        box-shadow: 0 2px 8px rgba(255, 91, 20, 0.15);
    }

    .liquid-citation-pill.visual-citation:hover {
        background: var(--naranja);
        color: #FFF;
        box-shadow: 0 0 15px var(--naranja);
    }

    /* ═══════════════════════  BOTONES, SELECTS E INPUTS  ═══════════════════════ */
    .stButton > button {
        background: linear-gradient(135deg, rgba(207, 216, 218, 0.12) 0%, rgba(6, 26, 32, 0.8) 100%) !important;
        color: var(--mercurio) !important;
        border: 1.5px solid rgba(207, 216, 218, 0.3) !important;
        border-radius: 12px !important;
        font-family: var(--font-sans) !important;
        font-weight: 700 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.03em !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 12px rgba(3, 13, 16, 0.4) !important;
    }

    .stButton > button:hover {
        background: var(--cromo-reflejo) !important;
        border-color: var(--naranja) !important;
        color: #FFF !important;
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 0 18px var(--naranja-glow), 0 6px 18px rgba(3, 13, 16, 0.7) !important;
    }

    .stButton > button:active {
        transform: scale(0.97) !important;
    }

    /* Botón venenoso principal */
    .btn-naranja > button,
    button[kind="primary"] {
        background: var(--naranja) !important;
        color: #FFF !important;
        border: 1.5px solid #FF8045 !important;
        box-shadow: 0 0 20px var(--naranja-glow) !important;
    }

    .btn-naranja > button:hover,
    button[kind="primary"]:hover {
        background: #FF7030 !important;
        box-shadow: 0 0 30px rgba(255, 91, 20, 0.7) !important;
    }

    /* Input del chat pegado en zona tranquila */
    [data-testid="stChatInput"] {
        background: rgba(6, 26, 32, 0.95) !important;
        border: 1.5px solid rgba(207, 216, 218, 0.3) !important;
        border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(3, 13, 16, 0.8) !important;
        transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: var(--naranja) !important;
        box-shadow: 0 0 25px var(--naranja-glow), 0 10px 35px rgba(3, 13, 16, 0.9) !important;
    }

    [data-testid="stChatInput"] textarea {
        color: var(--mercurio) !important;
        font-family: var(--font-sans) !important;
        font-size: 0.95rem !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(207, 216, 218, 0.45) !important;
        font-family: var(--font-whisper) !important;
        font-style: italic !important;
    }

    /* Inputs y textboxes estándar */
    .stTextInput input, .stSelectbox [data-baseweb="select"] {
        background-color: rgba(6, 26, 32, 0.9) !important;
        border: 1px solid rgba(207, 216, 218, 0.25) !important;
        border-radius: 10px !important;
        color: var(--mercurio) !important;
        font-family: var(--font-sans) !important;
    }

    .stTextInput input:focus {
        border-color: var(--naranja) !important;
        box-shadow: 0 0 12px var(--naranja-glow) !important;
    }

    /* Uploader de archivos estilo vientre biológico */
    [data-testid="stFileUploader"] section {
        background: rgba(11, 37, 46, 0.6) !important;
        border: 2px dashed rgba(207, 216, 218, 0.3) !important;
        border-radius: 18px !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stFileUploader"] section:hover {
        border-color: var(--lima) !important;
        background: rgba(11, 37, 46, 0.85) !important;
        box-shadow: 0 0 20px var(--lima-glow) !important;
    }

    /* ═══════════════════════  METRICS Y TELEMETRÍA  ═══════════════════════ */
    [data-testid="stMetric"] {
        background: rgba(11, 37, 46, 0.7) !important;
        border: 1px solid rgba(207, 216, 218, 0.18) !important;
        border-radius: 14px !important;
        padding: 0.8rem 1rem !important;
        box-shadow: 0 8px 20px rgba(3, 13, 16, 0.5) !important;
    }

    [data-testid="stMetricLabel"] p {
        font-family: var(--font-sans) !important;
        font-size: 0.76rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: rgba(207, 216, 218, 0.7) !important;
    }

    [data-testid="stMetricValue"] {
        font-family: var(--font-sans) !important;
        font-weight: 800 !important;
        color: var(--mercurio) !important;
    }

    [data-testid="stMetricDelta"] {
        font-family: var(--font-whisper) !important;
        font-style: italic !important;
        color: var(--lima) !important;
    }

    /* ═══════════════════════  SCROLLBARS LÍQUIDOS  ═══════════════════════ */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: var(--abisal-profundo);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(207, 216, 218, 0.25);
        border-radius: 6px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--naranja);
    }

    /* ═══════════════════════  ANIMACIONES DE RESPIRACIÓN  ═══════════════════════ */
    @keyframes creature-breathe {
        0% {
            transform: scale(1) translateY(0px);
            box-shadow: 0 20px 45px rgba(3, 13, 16, 0.7);
        }
        50% {
            transform: scale(1.008) translateY(-4px);
            box-shadow: 0 25px 55px rgba(3, 13, 16, 0.8), 0 0 20px var(--naranja-glow);
        }
        100% {
            transform: scale(1) translateY(0px);
            box-shadow: 0 20px 45px rgba(3, 13, 16, 0.7);
        }
    }

    .creature-breathing {
        animation: creature-breathe 6s ease-in-out infinite;
    }

    /* ═══════════════════════  TEXTO ROTADO 90° Y ANOTACIONES  ═══════════════════════ */
    .texto-rotado {
        writing-mode: vertical-rl;
        transform: rotate(180deg);
        font-family: var(--font-whisper);
        font-style: italic;
        font-size: 0.8rem;
        color: var(--mercurio);
        opacity: 0.55;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        user-select: none;
        transition: opacity 0.3s ease, color 0.3s ease;
    }

    .texto-rotado:hover {
        opacity: 1;
        color: var(--lima);
    }

    /* Filtro de derretido por velocidad aplicado a elementos dinámicos */
    .speed-meltable {
        filter: url(#liquid-speed-melt);
        will-change: filter, transform;
    }

    /* Texto elástico sensible al cursor */
    .elastic-letter {
        display: inline-block;
        transition: font-weight 0.15s ease, transform 0.15s ease, color 0.15s ease;
    }
    </style>
    """

def get_liquid_creature_js() -> str:
    """
    Retorna el motor JavaScript interactivo de la Criatura Líquida:
    1. Derretido por velocidad (feTurbulence + feDisplacementMap)
    2. Tipografía elástica (lente de pez magnética según distancia del cursor)
    3. Cursor gelatinoso con filtro Gooey (#liquid-goo)
    4. Cromo vivo central biomórfico reactivo
    5. Onda de choque con destellos al hacer clic
    6. Respiración en reposo tras 2.5s de inactividad
    7. Orbe líquido de navegación flotante
    """
    return """
    <div id="liquid-creature-root" style="display:none;"></div>

    <!-- Filtros SVG obligatorios para distorsión y cromo -->
    <svg style="position:fixed; top:-9999px; left:-9999px; width:0; height:0;" aria-hidden="true">
      <defs>
        <!-- 1. Filtro Gooey para cursor gelatinoso y orbe -->
        <filter id="liquid-goo">
          <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur" />
          <feColorMatrix in="blur" mode="matrix" 
            values="1 0 0 0 0  
                    0 1 0 0 0  
                    0 0 1 0 0  
                    0 0 0 24 -9" result="goo" />
          <feBlend in="SourceGraphic" in2="goo" />
        </filter>

        <!-- 2. Filtro de derretido por velocidad -->
        <filter id="liquid-speed-melt" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence id="melt-turb" type="fractalNoise" baseFrequency="0.02 0.06" numOctaves="2" result="noise" />
          <feDisplacementMap id="melt-disp" in="SourceGraphic" in2="noise" scale="0" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
    </svg>

    <script>
    (function initLiquidCreature() {
        const doc = window.parent ? window.parent.document : document;
        const win = window.parent ? window.parent : window;

        if (doc.getElementById('liquid-creature-injected')) return;
        const marker = doc.createElement('div');
        marker.id = 'liquid-creature-injected';
        doc.body.appendChild(marker);

        // Inyectar definiciones SVG en el DOM principal
        if (!doc.getElementById('liquid-svg-defs')) {
            const svgContainer = doc.createElement('div');
            svgContainer.id = 'liquid-svg-defs';
            svgContainer.innerHTML = `
            <svg style="position:fixed; top:-9999px; left:-9999px; width:0; height:0;" aria-hidden="true">
              <defs>
                <filter id="liquid-goo">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="7" result="blur" />
                  <feColorMatrix in="blur" mode="matrix" 
                    values="1 0 0 0 0  
                            0 1 0 0 0  
                            0 0 1 0 0  
                            0 0 0 24 -9" result="goo" />
                  <feBlend in="SourceGraphic" in2="goo" />
                </filter>
                <filter id="liquid-speed-melt" x="-20%" y="-20%" width="140%" height="140%">
                  <feTurbulence id="parent-melt-turb" type="fractalNoise" baseFrequency="0.015 0.05" numOctaves="2" result="noise" />
                  <feDisplacementMap id="parent-melt-disp" in="SourceGraphic" in2="noise" scale="0" xChannelSelector="R" yChannelSelector="G" />
                </filter>
              </defs>
            </svg>`;
            doc.body.appendChild(svgContainer);
        }

        // ═══════════════════════  1. CURSOR GELATINOSO  ═══════════════════════
        const cursorContainer = doc.createElement('div');
        cursorContainer.id = 'creature-cursor-wrap';
        cursorContainer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 999999;
            filter: url(#liquid-goo);
            overflow: hidden;
        `;

        const mainDot = doc.createElement('div');
        mainDot.id = 'cursor-main-dot';
        mainDot.style.cssText = `
            position: absolute;
            width: 18px;
            height: 18px;
            background: #FF5B14;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            transition: transform 0.05s ease;
            box-shadow: 0 0 12px rgba(255, 91, 20, 0.7);
        `;

        const trailingBlob = doc.createElement('div');
        trailingBlob.id = 'cursor-trailing-blob';
        trailingBlob.style.cssText = `
            position: absolute;
            width: 32px;
            height: 32px;
            background: #CFD8DA;
            border-radius: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            opacity: 0.75;
        `;

        cursorContainer.appendChild(trailingBlob);
        cursorContainer.appendChild(mainDot);
        doc.body.appendChild(cursorContainer);

        let mouseX = win.innerWidth / 2;
        let mouseY = win.innerHeight / 2;
        let trailX = mouseX;
        let trailY = mouseY;
        let prevMouseX = mouseX;
        let prevMouseY = mouseY;
        let velocity = 0;
        let idleTimer = null;

        win.addEventListener('mousemove', (e) => {
            mouseX = e.clientX;
            mouseY = e.clientY;
            mainDot.style.left = `${mouseX}px`;
            mainDot.style.top = `${mouseY}px`;

            // Detectar hover sobre elementos interactivos para estirar la gota
            const target = e.target;
            const isClickable = target.closest('button, a, input, select, textarea, [role="button"], .liquid-citation-pill');
            if (isClickable) {
                mainDot.style.transform = 'translate(-50%, -50%) scale(1.6)';
                mainDot.style.background = '#C6FF3D';
                trailingBlob.style.transform = 'translate(-50%, -50%) scale(1.4)';
            } else {
                mainDot.style.transform = 'translate(-50%, -50%) scale(1)';
                mainDot.style.background = '#FF5B14';
                trailingBlob.style.transform = 'translate(-50%, -50%) scale(1)';
            }

            resetIdleState();
        }, { passive: true });

        // ═══════════════════════  2. ONDA DE CHOQUE AL CLIC  ═══════════════════════
        win.addEventListener('click', (e) => {
            const shockwave = doc.createElement('div');
            shockwave.className = 'liquid-shockwave';
            shockwave.style.cssText = `
                position: fixed;
                left: ${e.clientX}px;
                top: ${e.clientY}px;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                border: 2px solid #C6FF3D;
                background: radial-gradient(circle, rgba(255,91,20,0.3) 0%, transparent 70%);
                transform: translate(-50%, -50%) scale(0.2);
                pointer-events: none;
                z-index: 999998;
                box-shadow: 0 0 25px #C6FF3D, inset 0 0 15px #FF5B14;
                transition: transform 0.65s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.65s ease;
                opacity: 0.9;
            `;
            doc.body.appendChild(shockwave);

            requestAnimationFrame(() => {
                shockwave.style.transform = 'translate(-50%, -50%) scale(14)';
                shockwave.style.opacity = '0';
            });

            setTimeout(() => {
                shockwave.remove();
            }, 700);

            resetIdleState();
        });

        // ═══════════════════════  3. DERRETIDO POR VELOCIDAD  ═══════════════════════
        const dispMap = doc.getElementById('parent-melt-disp');
        let currentScale = 0;

        function updateVelocityAndMelt() {
            const dx = mouseX - prevMouseX;
            const dy = mouseY - prevMouseY;
            const instSpeed = Math.sqrt(dx * dx + dy * dy);
            velocity = velocity * 0.8 + instSpeed * 0.2;

            prevMouseX = mouseX;
            prevMouseY = mouseY;

            // Suavizado del trailing blob
            trailX += (mouseX - trailX) * 0.18;
            trailY += (mouseY - trailY) * 0.18;
            trailingBlob.style.left = `${trailX}px`;
            trailingBlob.style.top = `${trailY}px`;

            // Calcular deformación por velocidad (máx 36px)
            const targetScale = Math.min(36, velocity * 0.7);
            currentScale += (targetScale - currentScale) * 0.15;

            if (dispMap) {
                if (currentScale > 0.5) {
                    dispMap.setAttribute('scale', currentScale.toFixed(2));
                } else if (currentScale <= 0.5 && dispMap.getAttribute('scale') !== '0') {
                    dispMap.setAttribute('scale', '0');
                }
            }

            requestAnimationFrame(updateVelocityAndMelt);
        }
        requestAnimationFrame(updateVelocityAndMelt);

        // ═══════════════════════  4. RESPIRACIÓN DE REPOSO (IDLE)  ═══════════════════════
        function resetIdleState() {
            doc.body.classList.remove('creature-idle');
            const organs = doc.querySelectorAll('.creature-organ');
            organs.forEach(o => o.classList.remove('creature-breathing'));

            clearTimeout(idleTimer);
            idleTimer = setTimeout(() => {
                doc.body.classList.add('creature-idle');
                const organs = doc.querySelectorAll('.creature-organ');
                organs.forEach(o => o.classList.add('creature-breathing'));
            }, 2500);
        }
        resetIdleState();

        // ═══════════════════════  5. NAVEGACIÓN: ORBE LÍQUIDO  ═══════════════════════
        // Crea el orbe biomórfico flotante de navegación que sigue al usuario
        if (!doc.getElementById('liquid-nav-orb')) {
            const orb = doc.createElement('div');
            orb.id = 'liquid-nav-orb';
            orb.style.cssText = `
                position: fixed;
                bottom: 24px;
                right: 28px;
                width: 58px;
                height: 58px;
                border-radius: 50%;
                background: var(--cromo-reflejo);
                border: 2px solid #FF5B14;
                box-shadow: 0 0 25px rgba(255, 91, 20, 0.4), inset 0 0 12px #CFD8DA;
                z-index: 999990;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
            `;
            orb.innerHTML = `<span style="font-size:22px; user-select:none;">🧪</span>`;

            const constellation = doc.createElement('div');
            constellation.id = 'liquid-constellation';
            constellation.style.cssText = `
                position: absolute;
                bottom: 70px;
                right: 0;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
                opacity: 0;
                transform: translateY(15px) scale(0.9);
                transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            `;

            const sections = [
                { icon: '💬', label: 'Diálogo Neural', action: () => {
                    const btn = doc.querySelector('button[key="toggle_header_traceability"]');
                    if (btn && btn.innerText.includes('Volver')) btn.click();
                }},
                { icon: '👁️', label: 'Ojo Visor', action: () => {
                    const btn = doc.querySelector('button[key="toggle_main_viewer"]');
                    if (btn) btn.click();
                }},
                { icon: '⚡', label: 'Telemetría', action: () => {
                    const btn = doc.querySelector('button[key="toggle_header_traceability"]');
                    if (btn) btn.click();
                }}
            ];

            sections.forEach(s => {
                const bubble = doc.createElement('div');
                bubble.style.cssText = `
                    background: rgba(6, 26, 32, 0.95);
                    border: 1.5px solid #C6FF3D;
                    color: #CFD8DA;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-family: 'Bricolage Grotesque', sans-serif;
                    font-size: 0.82rem;
                    font-weight: 700;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    box-shadow: 0 4px 15px rgba(3, 13, 16, 0.7), 0 0 10px rgba(198, 255, 61, 0.2);
                    white-space: nowrap;
                    pointer-events: auto;
                    cursor: pointer;
                    transition: transform 0.2s ease, background 0.2s ease;
                `;
                bubble.innerHTML = `<span>${s.icon}</span> <span>${s.label}</span>`;
                bubble.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    s.action();
                    toggleConstellation(false);
                });
                bubble.addEventListener('mouseenter', () => {
                    bubble.style.transform = 'translateX(-6px) scale(1.05)';
                    bubble.style.background = '#C6FF3D';
                    bubble.style.color = '#061A20';
                });
                bubble.addEventListener('mouseleave', () => {
                    bubble.style.transform = 'translateX(0) scale(1)';
                    bubble.style.background = 'rgba(6, 26, 32, 0.95)';
                    bubble.style.color = '#CFD8DA';
                });
                constellation.appendChild(bubble);
            });

            orb.appendChild(constellation);
            doc.body.appendChild(orb);

            let orbOpen = false;
            function toggleConstellation(forceState) {
                orbOpen = forceState !== undefined ? forceState : !orbOpen;
                if (orbOpen) {
                    constellation.style.opacity = '1';
                    constellation.style.pointerEvents = 'auto';
                    constellation.style.transform = 'translateY(0) scale(1)';
                    orb.style.boxShadow = '0 0 35px #C6FF3D, inset 0 0 18px #FF5B14';
                    orb.style.borderColor = '#C6FF3D';
                    orb.style.transform = 'rotate(45deg) scale(1.1)';
                } else {
                    constellation.style.opacity = '0';
                    constellation.style.pointerEvents = 'none';
                    constellation.style.transform = 'translateY(15px) scale(0.9)';
                    orb.style.boxShadow = '0 0 25px rgba(255, 91, 20, 0.4), inset 0 0 12px #CFD8DA';
                    orb.style.borderColor = '#FF5B14';
                    orb.style.transform = 'rotate(0deg) scale(1)';
                }
            }

            orb.addEventListener('click', () => toggleConstellation());
        }
    })();
    </script>
    """

def get_living_chrome_svg() -> str:
    """
    Retorna la forma biomórfica de cromo líquido con reflejos mercuriales y perfiles naranja/lima.
    Reacciona elásticamente como un organismo en reposo.
    """
    return """
    <div class="living-chrome-container" style="display:flex; justify-content:center; align-items:center; margin: 0.5rem 0 1rem; position:relative; overflow:hidden;">
      <svg width="280" height="90" viewBox="0 0 280 90" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 0 18px rgba(255,91,20,0.3));">
        <defs>
          <linearGradient id="chromeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#CFD8DA" />
            <stop offset="35%" stop-color="#061A20" />
            <stop offset="70%" stop-color="#CFD8DA" />
            <stop offset="90%" stop-color="#FF5B14" />
            <stop offset="100%" stop-color="#C6FF3D" />
          </linearGradient>
          <radialGradient id="mercuryReflect" cx="40%" cy="30%" r="60%">
            <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.9"/>
            <stop offset="45%" stop-color="#CFD8DA" stop-opacity="0.6"/>
            <stop offset="85%" stop-color="#061A20" stop-opacity="0.9"/>
            <stop offset="100%" stop-color="#FF5B14" stop-opacity="0.5"/>
          </radialGradient>
        </defs>
        
        <!-- Cuerpo líquido de la medusa metálica -->
        <path d="M 30,45 C 50,15 110,20 140,40 C 170,60 230,25 250,45 C 270,65 210,85 140,65 C 70,85 10,65 30,45 Z" 
              fill="url(#mercuryReflect)" 
              stroke="url(#chromeGrad)" 
              stroke-width="3"
              style="animation: jellyMorph 8s ease-in-out infinite alternate;">
        </path>
        
        <!-- Núcleo bio-luminiscente naranja -->
        <circle cx="140" cy="48" r="7" fill="#FF5B14" opacity="0.85" style="filter: drop-shadow(0 0 8px #FF5B14);">
          <animate attributeName="r" values="6;8.5;6" dur="3s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite"/>
        </circle>

        <!-- Destellos en Lima Ácida -->
        <circle cx="95" cy="40" r="3" fill="#C6FF3D" opacity="0.75" />
        <circle cx="185" cy="46" r="3.5" fill="#C6FF3D" opacity="0.75" />

        <!-- Tentáculos tenues de cromo -->
        <path d="M 110,60 Q 100,85 85,90" stroke="#CFD8DA" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.4"/>
        <path d="M 140,65 Q 140,88 145,92" stroke="#FF5B14" stroke-width="1.8" opacity="0.5"/>
        <path d="M 170,60 Q 180,85 195,90" stroke="#C6FF3D" stroke-width="1.5" stroke-dasharray="3 3" opacity="0.4"/>
      </svg>
      <style>
      @keyframes jellyMorph {
        0% {
          d: path("M 30,45 C 50,15 110,20 140,40 C 170,60 230,25 250,45 C 270,65 210,85 140,65 C 70,85 10,65 30,45 Z");
          transform: rotate(0deg);
        }
        50% {
          d: path("M 25,40 C 60,25 100,10 140,48 C 180,20 220,30 255,42 C 265,70 190,75 140,60 C 90,80 15,60 25,40 Z");
          transform: rotate(1deg);
        }
        100% {
          d: path("M 35,50 C 45,20 120,30 140,38 C 160,50 240,15 245,50 C 260,62 200,80 140,68 C 80,78 20,68 35,50 Z");
          transform: rotate(-1deg);
        }
      }
      </style>
    </div>
    """
