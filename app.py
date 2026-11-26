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
VIP_CHANNEL_URL = os.environ.get("VIP_CHANNEL_URL", "https://t.me/")
DB_PATH = "faroglobal_v6.db"

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

# --- BANCO DE DADOS COMPLETO ---
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
            source_name TEXT,
            price_badge TEXT,
            image_url TEXT,
            is_featured INTEGER DEFAULT 0,
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
            # BRASIL
            ("Creatina Monohidratada Pura 300g", "Creatina Monohidratada Pura (Campeã de Buscas)", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Suplemento nº 1 em pedidos recorrentes e buscas diárias nos marketplaces brasileiros.", "Alta taxa de recompra mensal (ciclo de 30 dias) e forte procura orgânica.", "Praticantes de musculação, corredores e público fitness.", "Google Trends BR + Autocomplete", "A partir de R$ 59 • ★ 4.9 (10k+ vendidos)", "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=800&q=80", 1, 97, "https://trends.google.com.br/trends/explore?geo=BR&q=Creatina%20Monohidratada", "https://lista.mercadolivre.com.br/creatina-monohidratada-pura", "https://www.amazon.com.br/s?k=creatina+monohidratada+pura", "https://www.amazon.com.br/s?k=creatina+monohidratada+pura", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Mini Projetor Portátil 4K Wi-Fi", "Mini Projetor Smart Portátil Full HD / 4K com Wi-Fi", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Fenômeno viral nas redes sociais e campeão de vendas para cinema em casa e apresentações.", "Alta viralização em vídeos curtos com excelente conversão no Brasil.", "Famílias, gamers, estudantes e profissionais externos.", "Radar Ofertas Quentes BR", "Faixa de R$ 229 • ★ 4.8 (Viral BR)", "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80", 1, 94, "https://trends.google.com.br/trends/explore?geo=BR&q=Mini%20Projetor%20Portatil", "https://lista.mercadolivre.com.br/mini-projetor-portatil-wifi", "https://shopee.com.br/search?keyword=mini%20projetor%20portatil", "https://shopee.com.br/search?keyword=mini%20projetor%20portatil", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Air Fryer Digital & Acessórios", "Kit Formas de Silicone & Acessórios para Air Fryer", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Um dos itens mais pesquisados e vendidos na Shopee e Mercado Livre com altíssima conversão.", "Compra por impulso de ticket baixo com altíssimo volume diário.", "Donos de fritadeira elétrica e compradores de utilidades domésticas.", "Google Autocomplete BR", "A partir de R$ 29 • ★ 4.8 (+50k pedidos)", "https://images.unsplash.com/photo-1585515320310-259814833e62?auto=format&fit=crop&w=800&q=80", 0, 95, "https://trends.google.com.br/trends/explore?geo=BR&q=Forma%20Silicone%20Air%20Fryer", "https://lista.mercadolivre.com.br/forma-silicone-air-fryer", "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer", "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Fone Bluetooth TWS ANC", "Fone de Ouvido Sem Fio TWS com Cancelamento de Ruído", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Líder absoluto em buscas de eletrônicos portáteis no Brasil com excelente custo-benefício.", "Alta procura diária para academia, corridas e reuniões online.", "Praticantes de esportes, estudantes e trabalhadores remotos.", "Google Trends BR + Ofertas", "Faixa de R$ 89 • ★ 4.8 (Top Áudio BR)", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=80", 0, 93, "https://trends.google.com.br/trends/explore?geo=BR&q=Fone%20Bluetooth%20TWS", "https://lista.mercadolivre.com.br/fone-bluetooth-tws-anc", "https://www.amazon.com.br/s?k=fone+bluetooth+tws+anc", "https://www.amazon.com.br/s?k=fone+bluetooth+tws+anc", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Sérum Facial Vitamina C & Ácido Hialurônico", "Kit Skincare Sérum Vitamina C + Ácido Hialurônico", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Categoria de beleza com maior crescimento de buscas e recompra recorrente no Brasil.", "Forte engajamento orgânico e alta taxa de recompra a cada 45 dias.", "Público interessado em cuidados com a pele e estética facial.", "Google Autocomplete BR", "A partir de R$ 44 • ★ 4.9 (Top Beleza)", "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=800&q=80", 0, 92, "https://trends.google.com.br/trends/explore?geo=BR&q=Serum%20Vitamina%20C", "https://lista.mercadolivre.com.br/serum-vitamina-c-acido-hialuronico", "https://www.amazon.com.br/s?k=serum+vitamina+c+acido+hialuronico", "https://www.amazon.com.br/s?k=serum+vitamina+c+acido+hialuronico", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Smartwatch Esportivo GPS", "Relógio Inteligente Esportivo com Monitor Cardíaco e GPS", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "Alta procura entre praticantes de corrida de rua, academia e ciclismo em todo o país.", "Crescimento contínuo das assessorias de corrida e provas de rua no Brasil.", "Corredores de rua, ciclistas e entusiastas de saúde.", "Radar Ofertas Quentes BR", "Faixa de R$ 179 • ★ 4.8 (Fitness BR)", "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com.br/trends/explore?geo=BR&q=Smartwatch%20GPS%20Corrida", "https://lista.mercadolivre.com.br/smartwatch-esportivo-gps", "https://www.amazon.com.br/s?k=smartwatch+esportivo+gps", "https://www.amazon.com.br/s?k=smartwatch+esportivo+gps", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Curso Automação WhatsApp & IA BR", "Formação Prática de IA & Automação Comercial no WhatsApp", "Brasil", "Brasil 🇧🇷", "Cursos & IA", "Treinamento mais procurado por empresas e profissionais que querem automatizar atendimento.", "Demanda crescente por redução de custos operacionais com agentes de IA.", "Donos de negócios locais, clínicas, infoprodutores e gestores.", "Google Autocomplete BR", "Acesso Imediato • ★ 4.9 (Hotmart/Kiwify)", "https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=800&q=80", 0, 96, "https://trends.google.com.br/trends/explore?geo=BR&q=Automacao%20WhatsApp%20IA", "https://lista.mercadolivre.com.br/curso-automacao-whatsapp", "https://hotmart.com/pt-br/marketplace/produtos?q=automacao+whatsapp+ia", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Planilha Controle Financeiro 2026 BR", "Planilha Automática de Finanças Pessoais & Investimentos", "Brasil", "Brasil 🇧🇷", "Templates & Planilhas", "Dashboard pronto em Excel e Google Sheets para organizar orçamento e metas mensais.", "Produto digital de entrega imediata e altíssima conversão no início e fim de mês.", "Assalariados, autônomos, casais e investidores iniciantes.", "Google Autocomplete BR", "A partir de R$ 37 • Entrega Imediata", "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com.br/trends/explore?geo=BR&q=Planilha%20Controle%20Financeiro", "https://lista.mercadolivre.com.br/planilha-controle-financeiro", "https://hotmart.com/pt-br/marketplace/produtos?q=planilha+controle+financeiro", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # ESTADOS UNIDOS
            ("AI Workflow Automation Course", "Curso Completo de Automação com IA (Sem Código)", "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA", "Treinamento prático americano para automatizar atendimento e vendas usando agentes de IA.", "Explosão de buscas nos EUA por fluxos no n8n e Make com baixa oferta em português.", "Empreendedores digitais, gestores de tráfego e agências.", "Google Trends US", "Acesso Vitalício • ★ 4.9 (Validado EUA)", "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80", 1, 96, "https://trends.google.com/trends/explore?geo=US&q=AI%20Workflow%20Automation", "https://lista.mercadolivre.com.br/curso-automacao-ia", "https://hotmart.com/pt-br/marketplace/produtos?q=automacao+ia", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Prompt Engineering Masterclass", "Formação Engenharia de Prompts para Negócios", "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA", "Biblioteca de comandos prontos para extrair resultados profissionais de ChatGPT e Claude.", "Alta procura por profissionais buscando produtividade imediata.", "Redatores, advogados, médicos, professores e consultores.", "Google Trends US", "A partir de R$ 67 • ★ 4.8 (Top IA EUA)", "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80", 0, 90, "https://trends.google.com/trends/explore?geo=US&q=Prompt%20Engineering", "https://lista.mercadolivre.com.br/curso-engenharia-de-prompts", "https://hotmart.com/pt-br/marketplace/produtos?q=engenharia+de+prompts", "https://hotmart.com", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # EUROPA
            ("Notion Second Brain 2026 System", "Sistema Segundo Cérebro no Notion (Produtividade)", "Europa", "Europa (Reino Unido) 🇬🇧", "Templates & Planilhas", "Template completo de gestão de projetos, finanças e metas pessoais com alta demanda na Europa.", "Custo zero de estoque e entrega imediata via link duplicável do Notion.", "Estudantes universitários, freelancers e criadores de conteúdo.", "Google Trends UK", "A partir de R$ 47 • Entrega Imediata", "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com/trends/explore?geo=GB&q=Notion%20Second%20Brain", "https://lista.mercadolivre.com.br/template-notion", "https://www.notion.so/templates/search?query=second+brain", "https://hotmart.com", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Portable Espresso Maker Travel", "Cafeteira Portátil de Pressão para Viagem e Escritório", "Europa", "Europa (Alemanha) 🇩🇪", "Produtos Validados", "Gadget compacto que prepara café expresso sem eletricidade, viral em lojas europeias.", "Vídeos de demonstração com alto engajamento na Alemanha e Itália.", "Viajantes frequentes, motoristas, campistas e amantes de café.", "Google Trends DE", "Faixa de R$ 189 • ★ 4.9 (Sucesso EU)", "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80", 0, 93, "https://trends.google.com/trends/explore?geo=DE&q=Portable%20Espresso%20Maker", "https://lista.mercadolivre.com.br/cafeteira-portatil-expresso", "https://pt.aliexpress.com/wholesale?SearchText=portable+espresso+maker", "https://www.amazon.com.br/s?k=cafeteira+portatil+expresso", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # AMÉRICA DO SUL
            ("Sistema Gestión Clínicas & Turnos AR", "Sistema Inteligente de Agendamento & Gestão de Clínicas", "América do Sul", "Argentina 🇦🇷", "Templates & Planilhas", "Plataforma/planilha argentina de controle de pacientes, agendas e faturamento recorrente.", "Forte adoção por clínicas pequenas e consultórios buscando reduzir faltas.", "Fisioterapeutas, dentistas, psicólogos e clínicas de estética.", "Google Trends AR", "A partir de R$ 67 • ★ 4.9 (LATAM)", "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80", 0, 92, "https://trends.google.com/trends/explore?geo=AR&q=gestion%20turnos%20clinicas", "https://lista.mercadolivre.com.br/planilha-gestao-clinica", "https://hotmart.com/pt-br/marketplace/produtos?q=gestao+clinica", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Kit Mate Térmico Acero Inox UY", "Garrafa Térmica Inox de Precisão & Kit Chimarrão/Mate", "América do Sul", "Uruguai 🇺🇾", "Produtos Validados", "Modelo térmico de alta retenção de temperatura campeão de vendas no Uruguai e Sul do Brasil.", "Alta demanda regional e ticket médio elevado com ótima comissão.", "Consumidores de chimarrão, tereré e bebidas térmicas.", "Tendência Sul-Americana", "Faixa de R$ 149 • ★ 4.9 (Top UY)", "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80", 0, 90, "https://www.google.com/search?q=termo+mate+acero+inoxidable+uruguay", "https://lista.mercadolivre.com.br/garrafa-termica-inox-mate", "https://www.amazon.com.br/s?k=garrafa+termica+inox+mate", "https://www.amazon.com.br/s?k=garrafa+termica+inox+mate", datetime.now().strftime("%d/%m/%Y %H:%M"))
        ]
        c.executemany('''
            INSERT OR IGNORE INTO opportunities (
                term_origin, term_br, continent, region, format_type, description,
                why_trending, target_audience, source_name, price_badge, image_url, is_featured,
                gap_score, trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_items)
        conn.commit()
    conn.close()

init_db()

# --- MOTOR DE VARREDURA INTERNACIONAL 24H (4 FONTES NATIVAS) + BRASIL ---
COMMERCIAL_KEYWORDS = [
    "ai", "ia", "curso", "course", "template", "plantilla", "planilha", "notion", "app",
    "software", "tool", "ferramenta", "herramienta", "kit", "pro", "smart", "mini", "portable",
    "portatil", "guia", "guide", "ebook", "system", "sistema", "tracker", "automation",
    "automacao", "marketing", "fitness", "saude", "creatina", "gadget", "workflow", "agent"
]

DEFAULT_IMAGES = {
    "Cursos & IA": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80",
    "Templates & Planilhas": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80",
    "Produtos Validados": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"
}

def is_commercial_opportunity(term, nicho="geral"):
    t = term.lower()
    if nicho == "ia":
        return any(w in t for w in ["ai", "ia", "gpt", "agent", "curso", "course", "automation", "automacao", "software", "tool"])
    if nicho == "planilhas":
        return any(w in t for w in ["template", "plantilla", "planilha", "notion", "sheet", "excel", "tracker", "sistema", "system"])
    return any(w in t for w in COMMERCIAL_KEYWORDS)

def classify_format(term):
    t = term.lower()
    if any(k in t for k in ["course", "curso", "class", "training", "ai", "ia", "gpt", "academy", "guide", "ebook", "agent", "software"]):
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

def fetch_native_autocomplete(gl, hl, prefixes):
    suggestions = []
    for p in prefixes:
        try:
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&hl={hl}&gl={gl}&q={requests.utils.quote(p)}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) > 1:
                    for s in data[1][:3]:
                        suggestions.append(s.strip())
        except Exception:
            continue
    return suggestions

def fetch_product_hunt_us():
    items = []
    try:
        url = "https://www.producthunt.com/feed"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:8]:
                title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                if title_el is not None and title_el.text:
                    items.append(title_el.text.strip())
    except Exception:
        pass
    return items

def fetch_reddit_opportunities():
    subreddits = ["SideProject", "ProductivityApps", "BuyItForLife"]
    found = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FaroGlobalBot/1.0)"}
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=4"
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts:
                    title = post.get("data", {}).get("title", "").strip()
                    if 8 <= len(title) <= 85:
                        found.append(title)
        except Exception:
            continue
    return found

def save_opportunity(c, conn, term_origin, term_br, continent, region_label, source_name, geo_code="US"):
    fmt = classify_format(term_br)
    desc = f"Oportunidade internacional captada via {source_name} ({region_label}) antes da saturação no Brasil." if geo_code != "BR" else f"Tendência em alta captada via {source_name}."
    why = f"Sinal validado em {region_label} pela fonte {source_name} com alto potencial de adaptação ao mercado brasileiro."
    audience = "Empreendedores digitais, profissionais buscando produtividade ou consumidores de novidades."
    price_badge = "Captado Ao Vivo • Radar 24h"
    img_url = DEFAULT_IMAGES.get(fmt)
    trend_url = f"https://trends.google.com/trends/explore?geo={geo_code}&q={requests.utils.quote(term_origin)}"
    br_url = f"https://lista.mercadolivre.com.br/{requests.utils.quote(term_br)}"
    supp_url = build_supplier_url(fmt, term_origin, term_br)
    gap_score = 95 if geo_code in ("US", "GB", "DE") else 92

    try:
        c.execute('''
            INSERT INTO opportunities (
                term_origin, term_br, continent, region, format_type, description,
                why_trending, target_audience, source_name, price_badge, image_url, is_featured,
                gap_score, trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (term_origin, term_br, continent, region_label, fmt, desc, why, audience, source_name, price_badge, img_url, 0, gap_score, trend_url, br_url, supp_url, br_url, datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def run_radar_cycle(nicho="geral"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    translator = GoogleTranslator(source='auto', target='pt')

    # 1. RADAR BRASIL
    br_prefixes = ["melhor curso de ", "ferramenta de ia para ", "planilha de ", "melhor produto para "]
    for term in fetch_google_trends_rss("BR") + fetch_native_autocomplete("br", "pt-BR", br_prefixes):
        if is_commercial_opportunity(term, nicho):
            save_opportunity(c, conn, term, term.title(), "Brasil", "Brasil 🇧🇷", "Radar Nacional BR", "BR")

    if nicho == "brasil":
        conn.close()
        return

    # 2. RADAR INTERNACIONAL MULTI-PAÍS
    intl_configs = [
        ("US", "us", "en", "Estados Unidos", "Estados Unidos 🇺🇸", ["best ai tool for ", "best notion template for ", "ai course for "]),
        ("GB", "gb", "en-GB", "Europa", "Europa (Reino Unido) 🇬🇧", ["best ai workflow ", "best productivity template ", "viral gadget "]),
        ("DE", "de", "de", "Europa", "Europa (Alemanha) 🇩🇪", ["beste ki tool ", "notion vorlage ", "online kurs "]),
        ("FR", "fr", "fr", "Europa", "Europa (França) 🇫🇷", ["meilleur outil ia ", "modele notion ", "formation ia "]),
        ("AR", "ar", "es-419", "América do Sul", "Argentina 🇦🇷", ["mejor curso de ", "plantilla excel ", "herramienta ia "]),
        ("CL", "cl", "es-419", "América do Sul", "Chile 🇨🇱", ["curso de ia ", "plantilla notion ", "mejor producto "]),
        ("CO", "co", "es-419", "América do Sul", "Colômbia 🇨🇴", ["curso ecommerce ", "herramienta ia ", "plantilla finanzas "])
    ]

    for geo, gl, hl, continent, region_label, prefixes in intl_configs:
        raw_terms = fetch_google_trends_rss(geo) + fetch_native_autocomplete(gl, hl, prefixes)
        for term in raw_terms:
            if not is_commercial_opportunity(term, nicho):
                continue
            try:
                term_br = translator.translate(term).title()
                save_opportunity(c, conn, term, term_br, continent, region_label, f"Radar Nativo {geo}", geo)
                time.sleep(0.35)
            except Exception:
                continue

    # 3. PRODUCT HUNT & REDDIT (EUA / EUROPA)
    if nicho in ("geral", "ia"):
        for ph_item in fetch_product_hunt_us():
            try:
                term_br = translator.translate(ph_item)
                save_opportunity(c, conn, ph_item, term_br, "Estados Unidos", "Estados Unidos 🇺🇸", "Product Hunt US", "US")
                time.sleep(0.35)
            except Exception:
                continue

    for rd_item in fetch_reddit_opportunities():
        if is_commercial_opportunity(rd_item, nicho):
            try:
                term_br = translator.translate(rd_item)
                save_opportunity(c, conn, rd_item, term_br, "Estados Unidos", "Estados Unidos 🇺🇸", "Reddit Trending US/EU", "US")
                time.sleep(0.35)
            except Exception:
                continue

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
            <span class="text-emerald-600 flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Curadoria Ativa 24/7</span>
            <span class="text-slate-300">|</span>
            <a href="#destaques" class="text-slate-700 hover:text-emerald-600 transition">Top Destaques</a>
            <span class="text-slate-300">|</span>
            <a href="#vitrine" class="text-slate-700 hover:text-emerald-600 transition">Catálogo Completo</a>
            <span class="text-slate-300">|</span>
            <a href="/admin" class="text-[#0A2540] hover:text-emerald-600 font-bold transition">Painel Admin</a>
        </div>
    </nav>

    <header class="max-w-5xl mx-auto px-4 pt-10 pb-8 text-center">
        {LOGO_SVG}
        <h1 class="mt-3 text-3xl md:text-5xl font-black tracking-tight">
            <span class="text-[#0A2540]">FARO</span> <span class="text-emerald-500">GLOBAL</span>
        </h1>
        <p class="text-[11px] font-bold tracking-[0.22em] text-[#0A2540] uppercase mt-1">Radar de Tendências & Mais Vendidos</p>
        <p class="mt-4 text-slate-600 text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
            Descubra os produtos e cursos mais vendidos no <strong>Brasil</strong> e acesse ferramentas validadas da <strong>América do Sul</strong>, <strong>Estados Unidos</strong> e <strong>Europa</strong>.
        </p>

        <div id="vitrine" class="mt-8 max-w-3xl mx-auto space-y-4">
            <input type="text" id="searchInput" onkeyup="filterCards()" placeholder="🔍 Buscar produto mais vendido, curso de IA, planilha ou termo..." class="w-full bg-white border border-slate-300 rounded-2xl px-5 py-3.5 text-sm shadow-sm focus:outline-none focus:border-emerald-500">

            <div class="flex flex-wrap justify-center gap-2 text-xs font-bold">
                <button onclick="setContinent('ALL', this)" class="cont-btn bg-[#0A2540] text-white px-4 py-2 rounded-full transition">🌍 Todos os Mercados</button>
                <button onclick="setContinent('Brasil', this)" class="cont-btn bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100 px-4 py-2 rounded-full transition">🇧🇷 Brasil • Mais Vendidos</button>
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

    <section id="destaques" class="max-w-5xl mx-auto px-4 mb-10">
        <div class="text-center mb-5">
            <span class="bg-amber-100 text-amber-900 text-[11px] font-extrabold uppercase tracking-wider px-3 py-1 rounded-full">🔥 Top 3 Achados da Semana</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in featured_items %}}
            <div class="bg-white border-2 border-emerald-400/80 rounded-2xl overflow-hidden shadow-md hover:shadow-lg transition flex flex-col justify-between text-center">
                <div>
                    <div class="relative h-40 w-full bg-slate-200 overflow-hidden">
                        <img src="{{{{ item[11] }}}}" alt="{{{{ item[2] }}}}" onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" class="w-full h-full object-cover">
                        <span class="absolute top-2.5 left-2.5 bg-amber-400 text-slate-950 text-[10px] font-black uppercase px-2.5 py-1 rounded-full shadow">🔥 Destaque</span>
                        <span class="absolute top-2.5 right-2.5 bg-slate-900/85 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">{{{{ item[4] }}}}</span>
                    </div>
                    <div class="p-5">
                        <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">{{{{ item[5] }}}}</span>
                        <h3 class="text-lg font-extrabold text-[#0A2540] leading-snug mt-2">{{{{ item[2] }}}}</h3>
                        <p class="text-xs text-slate-600 mt-2 leading-relaxed">{{{{ item[6] }}}}</p>
                        <p class="text-xs font-extrabold text-slate-800 bg-slate-100 rounded-lg py-1.5 px-3 mt-3">{{{{ item[10] }}}}</p>
                    </div>
                </div>
                <div class="px-5 pb-5">
                    <a href="{{{{ item[17] }}}}" target="_blank" class="block w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 rounded-xl text-sm transition shadow-sm">
                        {{{{ 'Acessar Treinamento / Ferramenta →' if item[5] == 'Cursos & IA' else ('Baixar Modelo Pronto →' if item[5] == 'Templates & Planilhas' else 'Conferir Menor Preço →') }}}}
                    </a>
                </div>
            </div>
            {{% endfor %}}
        </div>
    </section>

    <main class="max-w-5xl mx-auto px-4 pb-16">
        <div class="text-center mb-6">
            <h2 class="text-sm font-extrabold uppercase tracking-wider text-slate-500">Catálogo Completo Monitorado ({{{{ items|length }}}} Oportunidades)</h2>
        </div>
        <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in items %}}
            <div class="opp-card bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between text-center"
                 data-cont="{{{{ item[3] }}}}"
                 data-cat="{{{{ item[5] }}}}"
                 data-text="{{{{ item[2]|lower }}}} {{{{ item[1]|lower }}}} {{{{ item[6]|lower }}}} {{{{ item[4]|lower }}}}">
                <div>
                    <div class="relative h-36 w-full bg-slate-100 overflow-hidden">
                        <img src="{{{{ item[11] }}}}" alt="{{{{ item[2] }}}}" onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" class="w-full h-full object-cover">
                        <span class="absolute top-2.5 left-2.5 bg-white/95 text-slate-800 text-[10px] font-bold px-2.5 py-1 rounded-full shadow-sm">{{{{ item[4] }}}}</span>
                        <span class="absolute top-2.5 right-2.5 bg-sky-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-sm">{{{{ item[5] }}}}</span>
                    </div>
                    <div class="p-5">
                        <h3 class="text-base font-extrabold text-[#0A2540] leading-snug">{{{{ item[2] }}}}</h3>
                        <p class="text-xs text-slate-600 mt-2 leading-relaxed">{{{{ item[6] }}}}</p>
                        <p class="text-[11px] font-bold text-slate-700 bg-slate-100 rounded-lg py-1 px-2.5 mt-3">{{{{ item[10] }}}}</p>
                    </div>
                </div>
                <div class="px-5 pb-5">
                    <a href="{{{{ item[17] }}}}" target="_blank" class="block w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-sm">
                        {{{{ 'Acessar Treinamento / Ferramenta →' if item[5] == 'Cursos & IA' else ('Baixar Modelo Pronto →' if item[5] == 'Templates & Planilhas' else 'Conferir Menor Preço →') }}}}
                    </a>
                </div>
            </div>
            {{% endfor %}}
        </div>

        <div class="mt-14 bg-[#0A2540] text-white rounded-3xl p-8 text-center shadow-lg max-w-3xl mx-auto">
            <span class="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full">Radar VIP Gratuito</span>
            <h3 class="text-2xl font-black mt-3">Receba os 5 Achados da Semana Antes de Todo Mundo</h3>
            <p class="text-xs md:text-sm text-slate-300 mt-2 max-w-xl mx-auto">
                Entre no nosso canal de alertas para receber promoções relâmpago do Brasil e ferramentas virais dos EUA e Europa direto no seu celular.
            </p>
            <a href="{VIP_CHANNEL_URL}" target="_blank" class="inline-block mt-5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold px-6 py-3 rounded-xl text-sm transition shadow">
                Entrar no Canal VIP Gratuito →
            </a>
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

# --- 3. PAINEL ADMINISTRATIVO EXCLUSIVO ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin • Radar 24h & Dossiês • Faro Global</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans p-4 md:p-8">
    <div class="max-w-6xl mx-auto">
        <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-6 text-center shadow-sm">
            <h1 class="text-2xl font-black text-[#0A2540]">📡 Central de Inteligência & Auditoria • <span class="text-emerald-500">Faro Global</span></h1>
            <p class="text-xs text-slate-500 mt-1">Radar Nacional Brasil + Motor Internacional 4 Fontes (EUA, Europa & América do Sul)</p>
            <div class="flex flex-wrap justify-center gap-3 mt-5">
                <a href="/admin/run-now" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-xl text-xs transition shadow-sm">⚡ Rodar Varredura Global & Brasil Agora</a>
                <a href="/" target="_blank" class="bg-[#0A2540] hover:bg-slate-800 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition">Abrir Vitrine Pública</a>
                <a href="/admin/logout" class="bg-red-50 text-red-600 border border-red-200 font-semibold px-4 py-2.5 rounded-xl text-xs">Bloquear Painel</a>
            </div>
        </div>

        <div class="bg-gradient-to-br from-[#0A2540] to-slate-900 text-white rounded-2xl p-6 mb-8 shadow-lg">
            <div class="flex flex-col md:flex-row justify-between items-center gap-3 mb-4 border-b border-white/10 pb-4">
                <div>
                    <span class="bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full">Exclusivo Administrador • Radar Ao Vivo</span>
                    <h2 class="text-lg font-black mt-1">🇧🇷 Radar Nacional Brasil — Últimas Capturas</h2>
                </div>
                <div class="flex flex-wrap gap-2 text-[11px] font-bold">
                    <a href="https://trends.google.com/trending?geo=BR" target="_blank" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg">1. Google Trends BR ↗</a>
                    <a href="https://www.producthunt.com" target="_blank" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg">2. Product Hunt US ↗</a>
                    <a href="https://www.reddit.com/r/SideProject/top/" target="_blank" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg">3. Reddit Trending ↗</a>
                </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                {% for br in br_items[:6] %}
                <div class="bg-white/10 border border-white/10 rounded-xl p-3.5 text-left">
                    <div class="flex justify-between items-center text-[10px] font-bold text-emerald-300">
                        <span>{{ br[9] }}</span>
                        <span>Score {{ br[13] }}/100</span>
                    </div>
                    <p class="font-bold text-sm text-white mt-1">{{ br[2] }}</p>
                    <p class="text-[11px] text-slate-300 mt-1">{{ br[10] }}</p>
                </div>
                {% endfor %}
            </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-8 shadow-sm">
            <h2 class="text-sm font-extrabold text-[#0A2540] uppercase tracking-wider mb-4 text-center">+ Cadastrar Novo Produto / Curso na Vitrine</h2>
            <form method="POST" action="/admin/add-item" class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input type="text" name="term_br" required placeholder="Título na Vitrine" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="term_origin" required placeholder="Termo Original de Busca" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <select name="region_combo" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs font-semibold">
                    <option value="Brasil|Brasil 🇧🇷">🇧🇷 Brasil (Mais Vendidos)</option>
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
                <input type="text" name="price_badge" required placeholder="Selo de Preço/Prova (ex: A partir de R$ 59 • ★ 4.9)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="url" name="image_url" placeholder="URL da Imagem / Capa (Opcional)" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="why_trending" required placeholder="Por que está em alta?" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="target_audience" required placeholder="Público-alvo comprador" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="url" name="supplier_url" required placeholder="Link Fornecedor / Plataforma" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="url" name="affiliate_url" required placeholder="Seu Link Final de Venda / Afiliado" class="md:col-span-2 bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <input type="text" name="description" required placeholder="Resumo comercial exibido no card público" class="bg-slate-50 border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs">
                <button type="submit" class="md:col-span-3 bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-xs transition">Publicar Produto & Trilha na Vitrine</button>
            </form>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {% for item in items %}
            <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-xs font-bold text-sky-700 bg-sky-50 px-2.5 py-1 rounded-full">{{ item[4] }} • {{ item[5] }}</span>
                        <div class="flex items-center gap-2">
                            <a href="/admin/toggle-featured/{{ item[0] }}" class="text-[11px] font-bold px-2.5 py-0.5 rounded-full {{ 'bg-amber-400 text-slate-950' if item[12] == 1 else 'bg-slate-100 text-slate-600' }}">
                                {{ '🔥 No Top 3' if item[12] == 1 else '☆ Destacar' }}
                            </a>
                            <span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-extrabold px-2.5 py-0.5 rounded-full">Score: {{ item[13] }}/100</span>
                            <a href="/admin/delete/{{ item[0] }}" onclick="return confirm('Remover item?')" class="text-xs text-red-500 font-bold px-1.5">✕</a>
                        </div>
                    </div>

                    <h3 class="text-lg font-extrabold text-[#0A2540] mt-2">{{ item[2] }}</h3>
                    <p class="text-[11px] text-slate-400 mt-0.5">Fonte: <strong class="text-slate-600">{{ item[9] }}</strong> • {{ item[10] }}</p>

                    <div class="mt-4 bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 space-y-2 text-xs">
                        <p class="text-slate-700"><strong class="text-[#0A2540]">📌 Resumo:</strong> {{ item[6] }}</p>
                        <p class="text-slate-700"><strong class="text-emerald-700">📈 Por que está em alta:</strong> {{ item[7] }}</p>
                        <p class="text-slate-700"><strong class="text-sky-700">🎯 Público comprador:</strong> {{ item[8] }}</p>
                    </div>

                    <div class="mt-4">
                        <p class="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 mb-2">🧭 Trilha Direta até a Informação:</p>
                        <div class="grid grid-cols-3 gap-2 text-[11px] font-bold">
                            <a href="{{ item[14] }}" target="_blank" class="bg-sky-50 hover:bg-sky-100 text-sky-800 border border-sky-200 py-2 px-2 rounded-lg text-center transition">1. Fonte Trends ↗</a>
                            <a href="{{ item[15] }}" target="_blank" class="bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 py-2 px-2 rounded-lg text-center transition">2. Mercado BR ↗</a>
                            <a href="{{ item[16] }}" target="_blank"
