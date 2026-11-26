import os
import time
import sqlite3
import threading
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from functools import wraps
from deep_translator import GoogleTranslator
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for

app = Flask(__name__)

# --- CONFIGURAÇÕES DE SEGURANÇA ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "faroglobal-secret-key-2026")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@2026!")
CRON_SECRET_KEY = os.environ.get("CRON_SECRET_KEY", "radar2026")
DB_PATH = "faroglobal_v4.db"

# --- PROTEÇÃO ANTI-FORÇA BRUTA ---
FAILED_LOGINS = {}
MAX_ATTEMPTS = 5
BLOCK_MINUTES = 30

def is_ip_blocked(ip):
    record = FAILED_LOGINS.get(ip)
    if not record:
        return False
    attempts, blocked_until = record
    if blocked_until and datetime.now() < blocked_until:
        return True
    if blocked_until and datetime.now() >= blocked_until:
        del FAILED_LOGINS[ip]
    return False

def register_failed_login(ip):
    attempts, _ = FAILED_LOGINS.get(ip, (0, None))
    attempts += 1
    blocked_until = datetime.now() + timedelta(minutes=BLOCK_MINUTES) if attempts >= MAX_ATTEMPTS else None
    FAILED_LOGINS[ip] = (attempts, blocked_until)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# --- BANCO DE DADOS COM DOSSIÊ DETALHADO E TRILHA DE CAMINHOS ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_origin TEXT UNIQUE,
            term_br TEXT,
            continent TEXT,
            region TEXT,
            format_type TEXT,
            description TEXT,
            why_trending TEXT,
            target_audience TEXT,
            channel_metric TEXT,
            br_listings INTEGER,
            gap_score INTEGER,
            trend_source_url TEXT,
            br_market_url TEXT,
            supplier_url TEXT,
            affiliate_url TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()

    c.execute("SELECT COUNT(*) FROM opportunities")
    if c.fetchone()[0] == 0:
        seed_items = [
            (
                "Creatina Monohidratada Pura 300g",
                "Creatina Monohidratada Pura (Campeã de Buscas)",
                "Brasil", "Brasil 🇧🇷", "Produtos Validados",
                "Suplemento nº 1 em pedidos recorrentes e buscas diárias nos marketplaces brasileiros.",
                "Alta taxa de recompra mensal (ciclo de 30 dias) e forte procura orgânica no Google e Mercado Livre.",
                "Praticantes de musculação, corredores, crossfit e público fitness (18 a 55 anos).",
                "Mercado Livre & Amazon • +450 mil buscas/mês", 12, 97,
                "https://trends.google.com.br/trends/explore?geo=BR&q=Creatina%20Monohidratada",
                "https://lista.mercadolivre.com.br/creatina-monohidratada-pura",
                "https://www.amazon.com.br/s?k=creatina+monohidratada+pura",
                "https://www.amazon.com.br/s?k=creatina+monohidratada+pura",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ),
            (
                "Air Fryer Digital & Acessórios",
                "Kit Formas de Silicone & Acessórios para Air Fryer",
                "Brasil", "Brasil 🇧🇷", "Produtos Validados",
                "Um dos itens mais pesquisados e vendidos na Shopee e Mercado Livre com altíssima conversão.",
                "Compra por impulso de ticket baixo (R$ 25 a R$ 59) com altíssimo volume de pedidos diários.",
                "Donos de fritadeira elétrica, famílias e compradores de utilidades domésticas.",
                "Shopee & Mercado Livre • +380 mil buscas/mês", 18, 95,
                "https://trends.google.com.br/trends/explore?geo=BR&q=Forma%20Silicone%20Air%20Fryer",
                "https://lista.mercadolivre.com.br/forma-silicone-air-fryer",
                "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer",
                "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ),
            (
                "AI Workflow Automation Course",
                "Curso Completo de Automação com IA (Sem Código)",
                "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA",
                "Treinamento prático americano para automatizar atendimento e vendas usando agentes de IA.",
                "Explosão de buscas nos EUA por fluxos no n8n, Make e OpenAI com pouquíssimos cursos práticos em português.",
                "Empreendedores digitais, gestores de tráfego, agências e profissionais liberais.",
                "Alta demanda EUA • +180 mil buscas/mês", 2, 96,
                "https://trends.google.com/trends/explore?geo=US&q=AI%20Workflow%20Automation",
                "https://lista.mercadolivre.com.br/curso-automacao-ia",
                "https://hotmart.com/pt-br/marketplace/produtos?q=automacao+ia",
                "https://kiwify.com.br",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ),
            (
                "Notion Second Brain 2026 System",
                "Sistema Segundo Cérebro no Notion (Produtividade)",
                "Europa", "Europa (Reino Unido) 🇬🇧", "Templates & Planilhas",
                "Template completo de gestão de projetos, finanças e metas pessoais com alta demanda na Europa.",
                "Custo zero de estoque e entrega imediata via link duplicável do Notion; grande tração no Reino Unido.",
                "Estudantes universitários, freelancers, criadores de conteúdo e gestores.",
                "Top Produtividade UK • Baixa oferta BR", 4, 91,
                "https://trends.google.com/trends/explore?geo=GB&q=Notion%20Second%20Brain",
                "https://lista.mercadolivre.com.br/template-notion",
                "https://www.notion.so/templates/search?query=second+brain",
                "https://hotmart.com",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ),
            (
                "Sistema Gestión Clínicas & Turnos AR",
                "Sistema Inteligente de Agendamento & Gestão de Clínicas",
                "América do Sul", "Argentina 🇦🇷", "Templates & Planilhas",
                "Plataforma/planilha argentina de controle de pacientes, agendas e faturamento recorrente.",
                "Forte adoção por clínicas pequenas e consultórios na Argentina buscando reduzir faltas e organizar caixa.",
                "Fisioterapeutas, dentistas, psicólogos, nutricionistas e clínicas de estética.",
                "Tendência LATAM • Baixa concorrência BR", 3, 92,
                "https://trends.google.com/trends/explore?geo=AR&q=gestion%20turnos%20clinicas",
                "https://lista.mercadolivre.com.br/planilha-gestao-clinica",
                "https://hotmart.com/pt-br/marketplace/produtos?q=gestao+clinica",
                "https://kiwify.com.br",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            ),
            (
                "Portable Espresso Maker Travel",
                "Cafeteira Portátil de Pressão para Viagem e Escritório",
                "Europa", "Europa (Alemanha) 🇩🇪", "Produtos Validados",
                "Gadget compacto que prepara café expresso sem eletricidade, viral em lojas europeias.",
                "Vídeos de demonstração com alto engajamento na Alemanha e Itália; margem alta para revenda ou afiliação.",
                "Viajantes frequentes, motoristas, campistas e entusiastas de café especial.",
                "Viral Europa • Poucos anúncios no BR", 3, 93,
                "https://trends.google.com/trends/explore?geo=DE&q=Portable%20Espresso%20Maker",
                "https://lista.mercadolivre.com.br/cafeteira-portatil-expresso",
                "https://pt.aliexpress.com/wholesale?SearchText=portable+espresso+maker",
                "https://www.amazon.com.br/s?k=cafeteira+portatil+expresso",
                datetime.now().strftime("%d/%m/%Y %H:%M")
            )
        ]
        c.executemany('''
            INSERT OR IGNORE INTO opportunities (
                term_origin, term_br, continent, region, format_type, description,
                why_trending, target_audience, channel_metric, br_listings, gap_score,
                trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_items)
        conn.commit()
    conn.close()

init_db()

# --- MOTOR DE VARREDURA COM TRILHA EXATA DE LINKS ---
COMMERCIAL_KEYWORDS = [
    "ai", "ia", "curso", "course", "template", "planilha", "notion", "app",
    "software", "tool", "ferramenta", "kit", "pro", "smart", "mini", "portable",
    "portatil", "guia", "guide", "ebook", "system", "sistema", "tracker",
    "automacao", "automation", "marketing", "vendas", "fitness", "saude", "creatina"
]

def is_commercial_opportunity(term, nicho="geral"):
    t = term.lower()
    if nicho == "ia":
        return any(w in t for w in ["ai", "ia", "gpt", "curso", "course", "automacao", "automation", "software"])
    if nicho == "planilhas":
        return any(w in t for w in ["template", "planilha", "notion", "sheet", "excel", "tracker", "sistema", "system"])
    return any(w in t for w in COMMERCIAL_KEYWORDS)

def check_br_saturation(term_br):
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={requests.utils.quote(term_br)}&limit=1"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("paging", {}).get("total", 9999)
    except Exception:
        pass
    return 9999

def classify_format(term):
    t = term.lower()
    if any(k in t for k in ["course", "curso", "class", "training", "ai", "ia", "gpt", "academy", "guide", "ebook"]):
        return "Cursos & IA"
    if any(k in t for k in ["template", "plantilla", "planilha", "notion", "sheet", "excel", "plan", "dashboard", "tracker"]):
        return "Templates & Planilhas"
    return "Produtos Validados"

def build_supplier_url(fmt, term_origin, term_br):
    if fmt == "Cursos & IA":
        return f"https://hotmart.com/pt-br/marketplace/produtos?q={requests.utils.quote(term_br)}"
    if fmt == "Templates & Planilhas":
        return f"https://www.notion.so/templates/search?query={requests.utils.quote(term_origin)}"
    return f"https://pt.aliexpress.com/wholesale?SearchText={requests.utils.quote(term_origin)}"

def fetch_google_trends_rss(geo_code):
    terms = []
    try:
        url = f"https://trends.google.com/trending/rss?geo={geo_code}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item/title"):
                if item.text:
                    terms.append(item.text.strip())
    except Exception:
        pass
    return terms

def run_radar_cycle(nicho="geral"):
    all_markets = [
        ("BR", "Brasil", "Brasil 🇧🇷"),
        ("AR", "América do Sul", "Argentina 🇦🇷"),
        ("CL", "América do Sul", "Chile 🇨🇱"),
        ("CO", "América do Sul", "Colômbia 🇨🇴"),
        ("US", "Estados Unidos", "Estados Unidos 🇺🇸"),
        ("GB", "Europa", "Europa (Reino Unido) 🇬🇧"),
        ("DE", "Europa", "Europa (Alemanha) 🇩🇪")
    ]
    markets = [m for m in all_markets if m[0] == "BR"] if nicho == "brasil" else all_markets
    translator = GoogleTranslator(source='auto', target='pt')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for geo, continent, region_label in markets:
        for term in fetch_google_trends_rss(geo):
            if not is_commercial_opportunity(term, nicho):
                continue
            term_br = term if geo == "BR" else translator.translate(term)
            br_count = check_br_saturation(term_br)
            gap_score = 94 if geo == "BR" else (96 if br_count <= 5 else (89 if br_count <= 30 else 80))
            fmt = classify_format(term_br)
            metric = "Google Trends BR • Alta Procura" if geo == "BR" else f"Radar {region_label} • {br_count} anúncios no BR"
            desc = f"Oportunidade comercial detectada em tempo real no Google Trends ({region_label})."
            why = f"Pico de buscas orgânicas registrado em {region_label} com baixa saturação competitiva no Brasil ({br_count} anúncios)."
            audience = "Compradores online ativos interessados em produtividade, soluções digitais ou produtos virais."
            trend_url = f"https://trends.google.com/trends/explore?geo={geo}&q={requests.utils.quote(term)}"
            br_url = f"https://lista.mercadolivre.com.br/{requests.utils.quote(term_br)}"
            supp_url = build_supplier_url(fmt, term, term_br)

            try:
                c.execute('''
                    INSERT INTO opportunities (
                        term_origin, term_br, continent, region, format_type, description,
                        why_trending, target_audience, channel_metric, br_listings, gap_score,
                        trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (term, term_br, continent, region_label, fmt, desc, why, audience, metric, br_count, gap_score, trend_url, br_url, supp_url, br_url, datetime.now().strftime("%d/%m/%Y %H:%M")))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
            time.sleep(0.5)
    conn.close()

# --- LOGO VETORIAL OFICIAL FARO GLOBAL ---
LOGO_SVG = """
<svg width="58" height="58" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="mx-auto">
    <defs>
        <linearGradient id="fgGrad" x1="15" y1="85" x2="85" y2="15" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#0088FF"/>
            <stop offset="100%" stop-color="#10B981"/>
        </linearGradient>
    </defs>
    <circle cx="50" cy="50" r="30" stroke="url(#fgGrad)" stroke-width="4.5"/>
    <ellipse cx="50" cy="50" rx="14" ry="30" stroke="url(#fgGrad)" stroke-width="3"/>
    <line x1="20" y1="50" x2="80" y2="50" stroke="url(#fgGrad)" stroke-width="3"/>
    <polygon points="50,12 54,46 88,50 54,54 50,88 46,54 12,50 46,46" fill="url(#fgGrad)" opacity="0.25"/>
    <polygon points="73,27 54,54 27,73 46,46" fill="url(#fgGrad)"/>
    <circle cx="50" cy="50" r="4.5" fill="#FFFFFF"/>
    <path d="M68 18 A18 18 0 0 1 82 32" stroke="#10B981" stroke-width="4" stroke-linecap="round"/>
    <path d="M72 10 A26 26 0 0 1 90 28" stroke="#0088FF" stroke-width="4" stroke-linecap="round"/>
</svg>
"""

# --- 1. VITRINE PÚBLICA ---
PUBLIC_HTML = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faro Global • Radar de Tendências & Mais Vendidos</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans antialiased">
    <nav class="pt-5 px-4 flex justify-center">
        <div class="bg-white/95 backdrop-blur border border-slate-200 shadow-sm rounded-full px-5 py-2 flex items-center gap-4 text-xs font-semibold">
            <span class="text-emerald-600 flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Radar Ativo 24/7</span>
            <span class="text-slate-300">|</span>
            <a href="#vitrine" class="text-slate-700 hover:text-emerald-600 transition">Vitrine Pública</a>
            <span class="text-slate-300">|</span>
            <a href="/admin" class="text-[#0A2540] hover:text-emerald-600 font-bold transition">Painel Administrativo</a>
        </div>
    </nav>

    <header class="max-w-5xl mx-auto px-4 pt-10 pb-8 text-center">
        {LOGO_SVG}
        <h1 class="mt-3 text-3xl md:text-5xl font-black tracking-tight">
            <span class="text-[#0A2540]">FARO</span> <span class="text-emerald-500">GLOBAL</span>
        </h1>
        <p class="text-[11px] font-bold tracking-[0.22em] text-[#0A2540] uppercase mt-1">Radar de Tendências & Mais Vendidos</p>
        <p class="mt-4 text-slate-600 text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
            Monitore os produtos e cursos mais vendidos no <strong>Brasil</strong> e descubra oportunidades validadas na <strong>América do Sul</strong>, <strong>Estados Unidos</strong> e <strong>Europa</strong>.
        </p>

        <div id="vitrine" class="mt-8 max-w-3xl mx-auto space-y-4">
            <input type="text" id="searchInput" onkeyup="filterCards()" placeholder="🔍 Buscar produto mais vendido, curso de IA, planilha ou termo pesquisado..." class="w-full bg-white border border-slate-300 rounded-2xl px-5 py-3.5 text-sm shadow-sm focus:outline-none focus:border-emerald-500">

            <div class="flex flex-wrap justify-center gap-2 text-xs font-bold">
                <button onclick="setContinent('ALL', this)" class="cont-btn bg-[#0A2540] text-white px-4 py-2 rounded-full transition">🌍 Todos os Mercados</button>
                <button onclick="setContinent('Brasil', this)" class="cont-btn bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100 px-4 py-2 rounded-full transition">🇧🇷 Brasil • Mais Vendidos & Buscados</button>
                <button onclick="setContinent('América do Sul', this)" class="cont-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-4 py-2 rounded-full transition">🌎 América do Sul</button>
                <button onclick="setContinent('Estados Unidos', this)" class="cont-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-4 py-2 rounded-full transition">🇺🇸 Estados Unidos</button>
                <button onclick="setContinent('Europa', this)" class="cont-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-4 py-2 rounded-full transition">🇪🇺 Europa</button>
            </div>

            <div class="flex flex-wrap justify-center gap-2 text-xs font-semibold">
                <button onclick="setCategory('ALL', this)" class="cat-btn bg-slate-800 text-white px-3.5 py-1.5 rounded-full transition">Todas as Categorias</button>
                <button onclick="setCategory('Produtos Validados', this)" class="cat-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-3.5 py-1.5 rounded-full transition">Produtos Validados</button>
                <button onclick="setCategory('Cursos & IA', this)" class="cat-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-3.5 py-1.5 rounded-full transition">Cursos & IA</button>
                <button onclick="setCategory('Templates & Planilhas', this)" class="cat-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-3.5 py-1.5 rounded-full transition">Templates & Planilhas</button>
            </div>
        </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 pb-16">
        <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in items %}}
            <div class="opp-card bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between text-center"
                 data-cont="{{{{ item[3] }}}}"
                 data-cat="{{{{ item[5] }}}}"
                 data-text="{{{{ item[2]|lower }}}} {{{{ item[1]|lower }}}} {{{{ item[6]|lower }}}} {{{{ item[4]|lower }}}}">
                <div>
                    <div class="flex flex-wrap justify-center items-center gap-1.5 text-[11px] font-bold mb-3">
                        <span class="{{{{ 'bg-emerald-100 text-emerald-800' if item[3] == 'Brasil' else 'bg-slate-100 text-slate-700' }}}} px-2.5 py-1 rounded-full">{{{{ item[4] }}}}</span>
                        <span class="bg-sky-50 text-sky-700 px-2.5 py-1 rounded-full">{{{{ item[5] }}}}</span>
                    </div>
                    <h3 class="text-lg font-extrabold text-[#0A2540] leading-snug">{{{{ item[2] }}}}</h3>
                    <p class="text-xs text-slate-600 mt-2 leading-relaxed">{{{{ item[6] }}}}</p>
                    <p class="text-[11px] font-semibold text-emerald-700 mt-3">{{{{ item[9] }}}}</p>
                </div>
                <div class="mt-5 pt-4 border-t border-slate-100">
                    <a href="{{{{ item[15] }}}}" target="_blank" class="block w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-sm transition shadow-sm">
                        Ver Oferta / Oportunidade →
                    </a>
                </div>
            </div>
            {{% endfor %}}
        </div>
    </main>

    <footer class="border-t border-slate-200 py-8 text-center text-xs text-slate-500">
        <p class="font-bold text-[#0A2540]">FARO GLOBAL • faroglobal.com.br</p>
        <p class="mt-1">Monitoramento Brasil, América do Sul, EUA & Europa 24/7</p>
    </footer>

    <script>
        let currentCont = 'ALL';
        let currentCat = 'ALL';
        function setContinent(cont, btn) {{
            currentCont = cont;
            document.querySelectorAll('.cont-btn').forEach(b => b.className = 'cont-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-4 py-2 rounded-full transition');
            btn.className = cont === 'Brasil' ? 'cont-btn bg-emerald-600 text-white px-4 py-2 rounded-full transition shadow-sm' : 'cont-btn bg-[#0A2540] text-white px-4 py-2 rounded-full transition shadow-sm';
            filterCards();
        }}
        function setCategory(cat, btn) {{
            currentCat = cat;
            document.querySelectorAll('.cat-btn').forEach(b => b.className = 'cat-btn bg-white text-slate-600 border border-slate-200 hover:border-slate-400 px-3.5 py-1.5 rounded-full transition');
            btn.className = 'cat-btn bg-slate-800 text-white px-3.5 py-1.5 rounded-full transition';
            filterCards();
        }}
        function filterCards() {{
            const q = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.opp-card').forEach(card => {{
                const matchCont = currentCont === 'ALL' || card.dataset.cont === currentCont;
                const matchCat = currentCat === 'ALL' || card.dataset.cat === currentCat;
                const matchText = card.dataset.text.includes(q);
                card.style.display = (matchCont && matchCat && matchText) ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""

# --- 2. LOGIN ADMINISTRATIVO ---
LOGIN_HTML = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acesso Restrito • Faro Global</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 flex items-center justify-center min-h-screen px-4">
    <form method="POST" class="bg-white border border-slate-200 p-8 rounded-2xl w-full max-w-sm shadow-xl text-center">
        {LOGO_SVG}
        <h1 class="text-xl font-black text-[#0A2540] mt-3">FARO <span class="text-emerald-500">GLOBAL</span></h1>
        <p class="text-xs text-slate-500 mb-6">Painel Administrativo Protegido</p>
        {{% if error %}}<div class="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-xl mb-4">{{{{ error }}}}</div>{{% endif %}}
        <input type="password" name="password" required class="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm text-center mb-4 focus:outline-none focus:border-emerald-500" placeholder="Digite sua senha mestra">
        <button type="submit" class="w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-sm transition">Desbloquear Painel</button>
        <a href="/" class="block text-xs text-slate-400 hover:text-slate-700 mt-4">← Voltar para a Vitrine</a>
    </form>
</body>
</html>
"""

# --- 3. PAINEL ADMINISTRATIVO COM DOSSIÊ DETALHADO E TRILHA DE CAMINHOS ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin • Dossiê & Caminhos Exatos • Faro Global</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans p-4 md:p-8">
    <div class="max-w-6xl mx-auto">
        <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-6 text-center shadow-sm">
            <h1 class="text-2xl font-black text-[#0A2540]">📡 Central de Inteligência & Auditoria • <span class="text-emerald-500">Faro Global</span></h1>
            <p class="text-xs text-slate-500 mt-1">Dossiê completo de cada produto, análise de saturação e trilha direta até a fonte oficial, fornecedor e checkout</p>
            <div class="flex flex-wrap justify-center gap-3 mt-5">
                <a href="/admin/run-now" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-xl text-xs transition shadow-sm">⚡ Forçar Varredura Global & Brasil Agora</a>
                <a href="/" target="_blank" class="bg-[#0A2540] hover:bg-slate-800 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition">Abrir Vitrine Pública</a>
                <a href="/admin/logout" class="bg-red-50 text-red-600 border border-red-200 font-semibold px-4 py-2.5 rounded-xl text-xs">Bloquear Painel</a>
            </div>
        </div>

        <!-- Formulário de Cadastro Completo -->
        <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-8 shadow-sm">
            <h2 class="text-sm font-extrabold text-[#0A2540] uppercase tracking-wider mb-4 text-center">+ Cadastrar Novo Produto / Curso com Dossiê e Caminhos Diretos</h2>
            <form method="POST" action="/admin/add-item" class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input type="text" name="term_br" required placeholder="Título na Vitrine (ex: Creatina Pura 300g)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="term_origin" required placeholder="Termo Original de Busca (ex: Creatine Monohydrate)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <select name="region_combo" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs font-semibold">
                    <option value="Brasil|Brasil 🇧🇷">🇧🇷 Brasil (Mais Vendidos & Buscados)</option>
                    <option value="América do Sul|Argentina 🇦🇷">🇦🇷 América do Sul (Argentina)</option>
                    <option value="América do Sul|Chile 🇨🇱">🇨🇱 América do Sul (Chile)</option>
                    <option value="América do Sul|Colômbia 🇨🇴">🇨🇴 América do Sul (Colômbia)</option>
                    <option value="América do Sul|Uruguai 🇺🇾">🇺🇾 América do Sul (Uruguai)</option>
                    <option value="Estados Unidos|Estados Unidos 🇺🇸">🇺🇸 Estados Unidos</option>
                    <option value="Europa|Europa (Reino Unido) 🇬🇧">🇬🇧 Europa (Reino Unido)</option>
                    <option value="Europa|Europa (Alemanha) 🇩🇪">🇩🇪 Europa (Alemanha)</option>
                </select>
                <select name="format_type" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs font-semibold">
                    <option value="Produtos Validados">Produtos Validados</option>
                    <option value="Cursos & IA">Cursos & IA</option>
                    <option value="Templates & Planilhas">Templates & Planilhas</option>
                </select>
                <input type="text" name="why_trending" required placeholder="Por que está em alta? (ex: Alta recompra mensal)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="target_audience" required placeholder="Público-alvo comprador (ex: Praticantes de academia)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="url" name="supplier_url" required placeholder="Link Fornecedor / Plataforma (AliExpress, Hotmart...)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="url" name="affiliate_url" required placeholder="Seu Link Final de Venda / Afiliado (Vitrine)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="description" required placeholder="Resumo comercial exibido no card público" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <button type="submit" class="md:col-span-3 bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-xs transition">Publicar Produto & Trilha na Vitrine</button>
            </form>
        </div>

        <!-- Dossiês Detalhados com Caminhos Exatos -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {% for item in items %}
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
                <div>
                    <!-- Cabeçalho do Card -->
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded-full">{{ item[4] }} • {{ item[5] }}</span>
                        <div class="flex items-center gap-2">
                            <span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-extrabold px-2.5 py-0.5 rounded-full">Gap Score: {{ item[11] }}/100</span>
                            <a href="/admin/delete/{{ item[0] }}" onclick="return confirm('Remover este item?')" class="text-xs text-red-500 hover:text-red-700 font-bold px-1.5">✕</a>
                        </div>
                    </div>

                    <h3 class="text-lg font-extrabold text-[#0A2540] mt-2">{{ item[2] }}</h3>
                    <p class="text-[11px] text-slate-400 mt-0.5">Termo exato rastreado: <strong class="text-slate-600">{{ item[1] }}</strong> • Captado em {{ item[16] }}</p>

                    <!-- Bloco de Inteligência & Detalhes do Produto -->
                    <div class="mt-4 bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2 text-xs">
                        <p class="text-slate-700"><strong class="text-[#0A2540]">📌 Resumo:</strong> {{ item[6] }}</p>
                        <p class="text-slate-700"><strong class="text-emerald-700">📈 Por que está em alta:</strong> {{ item[7] }}</p>
                        <p class="text-slate-700"><strong class="text-sky-700">🎯 Público comprador:</strong> {{ item[8] }}</p>
                        <p class="text-slate-700"><strong class="text-amber-700">📊 Saturação & Volume:</strong> {{ item[9] }} ({{ item[10] }} anúncios diretos no BR)</p>
                    </div>

                    <!-- Trilha de Caminhos Diretos até a Informação -->
                    <div class="mt-4">
                        <p class="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 mb-2">🧭 Trilha Direta até a Informação (Clique para abrir):</p>
                        <div class="grid grid-cols-3 gap-2 text-[11px] font-bold">
                            <a href="{{ item[12] }}" target="_blank" class="bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 py-2 px-2 rounded-lg text-center transition">
                                1. Fonte Trends ↗
                            </a>
                            <a href="{{ item[13] }}" target="_blank" class="bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 py-2 px-2 rounded-lg text-center transition">
                                2. Mercado BR ↗
                            </a>
                            <a href="{{ item[14] }}" target="_blank" class="bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 py-2 px-2 rounded-lg text-center transition">
                                3. Fornecedor/Plat. ↗
                            </a>
                        </div>
                    </div>
                </div>

                <!-- 4. Caminho Final do Cliente (Link de Monetização / Checkout) -->
                <div class="mt-4 pt-4 border-t border-slate-100">
                    <label class="block text-[11px] font-bold text-[#0A2540] mb-1">4. Destino Final do Botão da Vitrine (Link de Afiliado / Checkout):</label>
                    <form method="POST" action="/admin/update-link/{{ item[0] }}" class="flex gap-2">
                        <input type="url" name="affiliate_url" value="{{ item[15] }}" class="flex-1 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs">
                        <a href="{{ item[15] }}" target="_blank" class="bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold px-3 py-2 rounded-lg text-xs flex items-center">Testar</a>
                        <button type="submit" class="bg-[#0A2540] hover:bg-emerald-600 text-white font-bold px-3.5 py-2 rounded-lg text-xs transition">Salvar</button>
                    </form>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

# --- ROTAS ---
@app.route("/")
def public_home():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM opportunities ORDER BY id DESC LIMIT 100")
    items = c.fetchall()
    conn.close()
    return render_template_string(PUBLIC_HTML, items=items)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if is_ip_blocked(ip):
        return render_template_string(LOGIN_HTML, error="IP bloqueado por 30 minutos."), 429
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            FAILED_LOGINS.pop(ip, None)
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        register_failed_login(ip)
        return render_template_string(LOGIN_HTML, error="Senha incorreta."), 401
    return render_template_string(LOGIN_HTML, error=None)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("public_home"))

@app.route("/admin")
@login_required
def admin_dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM opportunities ORDER BY id DESC LIMIT 120")
    items = c.fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, items=items)

@app.route("/admin/add-item", methods=["POST"])
@login_required
def add_item():
    term_br = request.form.get("term_br", "").strip()
    term_origin = request.form.get("term_origin", "").strip()
    continent, region = request.form.get("region_combo", "Brasil|Brasil 🇧🇷").split("|")
    fmt = request.form.get("format_type", "Produtos Validados").strip()
    why = request.form.get("why_trending", "").strip()
    audience = request.form.get("target_audience", "").strip()
    supp_url = request.form.get("supplier_url", "").strip()
    aff_url = request.form.get("affiliate_url", "").strip()
    desc = request.form.get("description", "").strip()

    if term_br and term_origin and aff_url:
        geo = "BR" if continent == "Brasil" else ("US" if continent == "Estados Unidos" else "GB")
        trend_url = f"https://trends.google.com/trends/explore?geo={geo}&q={requests.utils.quote(term_origin)}"
        br_url = f"https://lista.mercadolivre.com.br/{requests.utils.quote(term_br)}"
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO opportunities (
                term_origin, term_br, continent, region, format_type, description,
                why_trending, target_audience, channel_metric, br_listings, gap_score,
                trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (term_origin, term_br, continent, region, fmt, desc, why, audience, f"Curadoria {region}", 5, 95, trend_url, br_url, supp_url, aff_url, datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/update-link/<int:item_id>", methods=["POST"])
@login_required
def update_link(item_id):
    new_url = request.form.get("affiliate_url", "").strip()
    if new_url:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE opportunities SET affiliate_url = ? WHERE id = ?", (new_url, item_id))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<int:item_id>")
@login_required
def delete_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM opportunities WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/run-now")
@login_required
def run_now():
    threading.Thread(target=run_radar_cycle, args=("geral",)).start()
    return redirect(url_for("admin_dashboard"))

@app.route("/scan")
def cron_scan():
    if request.args.get("key") != CRON_SECRET_KEY:
        return jsonify({"error": "unauthorized"}), 401
    nicho = request.args.get("nicho", "geral").strip()
    threading.Thread(target=run_radar_cycle, args=(nicho,)).start()
    return jsonify({"status": "ok", "pesquisa": nicho, "time": str(datetime.now())})

@app.route("/ping")
def ping():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
