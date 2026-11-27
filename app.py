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
DB_PATH = "faroglobal_v7.db"

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

# --- BANCO DE DADOS COMPLETO (21 PRODUTOS + PREÇO PADRONIZADO + FILTROS DE OFERTA) ---
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
            offer_tag TEXT,
            description TEXT,
            why_trending TEXT,
            target_audience TEXT,
            source_name TEXT,
            price_prefix TEXT,
            price_value TEXT,
            social_proof TEXT,
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
            # TOP 3 DESTAQUES DA SEMANA
            ("Creatina Monohidratada Pura 300g", "Creatina Monohidratada Pura (Campeã de Buscas)", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "ticket_baixo", "Suplemento nº 1 em pedidos recorrentes e buscas diárias nos marketplaces brasileiros.", "Alta taxa de recompra mensal (ciclo de 30 dias) e forte procura orgânica.", "Praticantes de musculação, corredores e público fitness.", "Google Trends BR + Autocomplete", "A partir de", "R$ 59", "★ 4.9 • +10k vendidos • Recompra mensal", "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=800&q=80", 1, 97, "https://trends.google.com.br/trends/explore?geo=BR&q=Creatina%20Monohidratada", "https://lista.mercadolivre.com.br/creatina-monohidratada-pura", "https://www.amazon.com.br/s?k=creatina+monohidratada+pura", "https://www.amazon.com.br/s?k=creatina+monohidratada+pura", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("AI Workflow Automation Course", "Curso Completo de Automação com IA (Sem Código)", "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA", "acesso_imediato", "Treinamento prático americano para automatizar atendimento e vendas usando agentes de IA.", "Explosão de buscas nos EUA por fluxos no n8n e Make com baixa oferta em português.", "Empreendedores digitais, gestores de tráfego e agências.", "Google Trends US", "Modalidade", "ACESSO VITALÍCIO", "★ 4.9 • Validado nos EUA • Sem mensalidade", "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=80", 1, 96, "https://trends.google.com/trends/explore?geo=US&q=AI%20Workflow%20Automation", "https://lista.mercadolivre.com.br/curso-automacao-ia", "https://hotmart.com/pt-br/marketplace/produtos?q=automacao+ia", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Mini Projetor Portátil 4K Wi-Fi", "Mini Projetor Smart Portátil Full HD / 4K com Wi-Fi", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "faixa_media", "Fenômeno viral nas redes sociais e campeão de vendas para cinema em casa e apresentações.", "Alta viralização em vídeos curtos com excelente conversão no Brasil.", "Famílias, gamers, estudantes e profissionais externos.", "Radar Ofertas Quentes BR", "Faixa de", "R$ 229", "★ 4.8 • Viral BR • Entrega rápida", "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?auto=format&fit=crop&w=800&q=80", 1, 94, "https://trends.google.com.br/trends/explore?geo=BR&q=Mini%20Projetor%20Portatil", "https://lista.mercadolivre.com.br/mini-projetor-portatil-wifi", "https://shopee.com.br/search?keyword=mini%20projetor%20portatil", "https://shopee.com.br/search?keyword=mini%20projetor%20portatil", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # BRASIL (CATÁLOGO)
            ("Air Fryer Digital & Acessórios", "Kit Formas de Silicone & Acessórios para Air Fryer", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "ticket_baixo", "Um dos itens mais pesquisados e vendidos na Shopee e Mercado Livre com altíssima conversão.", "Compra por impulso de ticket baixo com altíssimo volume diário.", "Donos de fritadeira elétrica e compradores de utilidades domésticas.", "Google Autocomplete BR", "A partir de", "R$ 29", "★ 4.8 • +50k pedidos • Ticket baixo", "https://images.unsplash.com/photo-1585515320310-259814833e62?auto=format&fit=crop&w=800&q=80", 0, 95, "https://trends.google.com.br/trends/explore?geo=BR&q=Forma%20Silicone%20Air%20Fryer", "https://lista.mercadolivre.com.br/forma-silicone-air-fryer", "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer", "https://shopee.com.br/search?keyword=forma%20silicone%20air%20fryer", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Fone Bluetooth TWS ANC", "Fone de Ouvido Sem Fio TWS com Cancelamento de Ruído", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "ticket_baixo", "Líder absoluto em buscas de eletrônicos portáteis no Brasil com excelente custo-benefício.", "Alta procura diária para academia, corridas e reuniões online.", "Praticantes de esportes, estudantes e trabalhadores remotos.", "Google Trends BR + Ofertas", "Faixa de", "R$ 89", "★ 4.8 • Top Áudio BR • Uso diário", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=80", 0, 93, "https://trends.google.com.br/trends/explore?geo=BR&q=Fone%20Bluetooth%20TWS", "https://lista.mercadolivre.com.br/fone-bluetooth-tws-anc", "https://www.amazon.com.br/s?k=fone+bluetooth+tws+anc", "https://www.amazon.com.br/s?k=fone+bluetooth+tws+anc", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Sérum Facial Vitamina C & Ácido Hialurônico", "Kit Skincare Sérum Vitamina C + Ácido Hialurônico", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "recorrencia", "Categoria de beleza com maior crescimento de buscas e recompra recorrente no Brasil.", "Forte engajamento orgânico e alta taxa de recompra a cada 45 dias.", "Público interessado em cuidados com a pele e estética facial.", "Google Autocomplete BR", "A partir de", "R$ 44", "★ 4.9 • Top Beleza • Recompra rápida", "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=800&q=80", 0, 92, "https://trends.google.com.br/trends/explore?geo=BR&q=Serum%20Vitamina%20C", "https://lista.mercadolivre.com.br/serum-vitamina-c-acido-hialuronico", "https://www.amazon.com.br/s?k=serum+vitamina+c+acido+hialuronico", "https://www.amazon.com.br/s?k=serum+vitamina+c+acido+hialuronico", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Smartwatch Esportivo GPS", "Relógio Inteligente Esportivo com Monitor Cardíaco e GPS", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "faixa_media", "Alta procura entre praticantes de corrida de rua, academia e ciclismo em todo o país.", "Crescimento contínuo das assessorias de corrida e provas de rua no Brasil.", "Corredores de rua, ciclistas e entusiastas de saúde.", "Radar Ofertas Quentes BR", "Faixa de", "R$ 179", "★ 4.8 • Fitness BR • Alta procura", "https://images.unsplash.com/photo-1579586337278-3befd40fd17a?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com.br/trends/explore?geo=BR&q=Smartwatch%20GPS%20Corrida", "https://lista.mercadolivre.com.br/smartwatch-esportivo-gps", "https://www.amazon.com.br/s?k=smartwatch+esportivo+gps", "https://www.amazon.com.br/s?k=smartwatch+esportivo+gps", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Pistola de Massagem Muscular", "Pistola Massageadora Profunda para Recuperação Muscular", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "faixa_media", "Sucesso entre atletas amadores, corredores e fisioterapeutas para alívio miofascial rápido.", "Excelente margem e alta percepção de valor como presente ou uso próprio.", "Corredores, praticantes de crossfit, academias e clínicas.", "Google Trends BR", "Faixa de", "R$ 119", "★ 4.8 • Recuperação • Bem avaliado", "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=800&q=80", 0, 90, "https://trends.google.com.br/trends/explore?geo=BR&q=Pistola%20Massageadora%20Muscular", "https://lista.mercadolivre.com.br/pistola-massageadora-muscular", "https://www.amazon.com.br/s?k=pistola+massageadora+muscular", "https://www.amazon.com.br/s?k=pistola+massageadora+muscular", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Garrafa Térmica Inox 1L", "Garrafa Térmica Inteligente em Aço Inox Parede Dupla", "Brasil", "Brasil 🇧🇷", "Produtos Validados", "recorrencia", "Item essencial no dia a dia de trabalho, academia e viagens com alta durabilidade.", "Produto perene com pico de buscas em épocas quentes.", "Estudantes, trabalhadores, atletas e viajantes.", "Google Autocomplete BR", "A partir de", "R$ 49", "★ 4.9 • +30k pedidos • Uso diário", "https://images.unsplash.com/photo-1602143407151-7111542de6e8?auto=format&fit=crop&w=800&q=80", 0, 89, "https://trends.google.com.br/trends/explore?geo=BR&q=Garrafa%20Termica%20Inox", "https://lista.mercadolivre.com.br/garrafa-termica-inox", "https://shopee.com.br/search?keyword=garrafa%20termica%20inox", "https://shopee.com.br/search?keyword=garrafa%20termica%20inox", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Curso Automação WhatsApp & IA BR", "Formação Prática de IA & Automação Comercial no WhatsApp", "Brasil", "Brasil 🇧🇷", "Cursos & IA", "acesso_imediato", "Treinamento mais procurado por empresas e profissionais que querem automatizar atendimento.", "Demanda crescente por redução de custos operacionais com agentes de IA.", "Donos de negócios locais, clínicas, infoprodutores e gestores.", "Google Autocomplete BR", "Modalidade", "ACESSO IMEDIATO", "★ 4.9 • Hotmart/Kiwify • Passo a passo", "https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=800&q=80", 0, 96, "https://trends.google.com.br/trends/explore?geo=BR&q=Automacao%20WhatsApp%20IA", "https://lista.mercadolivre.com.br/curso-automacao-whatsapp", "https://hotmart.com/pt-br/marketplace/produtos?q=automacao+whatsapp+ia", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Planilha Controle Financeiro 2026 BR", "Planilha Automática de Finanças Pessoais & Investimentos", "Brasil", "Brasil 🇧🇷", "Templates & Planilhas", "ticket_baixo", "Dashboard pronto em Excel e Google Sheets para organizar orçamento e metas mensais.", "Produto digital de entrega imediata e altíssima conversão no início e fim de mês.", "Assalariados, autônomos, casais e investidores iniciantes.", "Google Autocomplete BR", "A partir de", "R$ 37", "★ 4.9 • Entrega imediata • Excel & Sheets", "https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com.br/trends/explore?geo=BR&q=Planilha%20Controle%20Financeiro", "https://lista.mercadolivre.com.br/planilha-controle-financeiro", "https://hotmart.com/pt-br/marketplace/produtos?q=planilha+controle+financeiro", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # ESTADOS UNIDOS
            ("Prompt Engineering Masterclass", "Formação Engenharia de Prompts para Negócios", "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA", "acesso_imediato", "Biblioteca de comandos prontos para extrair resultados profissionais de ChatGPT e Claude.", "Alta procura por profissionais buscando produtividade imediata.", "Redatores, advogados, médicos, professores e consultores.", "Google Trends US", "A partir de", "R$ 67", "★ 4.8 • Top IA EUA • Acesso imediato", "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?auto=format&fit=crop&w=800&q=80", 0, 90, "https://trends.google.com/trends/explore?geo=US&q=Prompt%20Engineering", "https://lista.mercadolivre.com.br/curso-engenharia-de-prompts", "https://hotmart.com/pt-br/marketplace/produtos?q=engenharia+de+prompts", "https://hotmart.com", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("AI Video Dubbing & Avatar Studio", "Ferramenta de Dublagem & Vídeos com Avatares de IA", "Estados Unidos", "Estados Unidos 🇺🇸", "Cursos & IA", "acesso_imediato", "Plataforma americana que traduz vídeos com sincronia labial perfeita em segundos.", "Forte adoção por criadores de conteúdo e canais dark nos EUA.", "YouTubers, criadores de conteúdo, afiliados e professores.", "Product Hunt US", "Modalidade", "PLANO GRÁTIS + PRO", "★ 4.9 • Viral EUA • Uso online", "https://images.unsplash.com/photo-1633356122544-f134324a6cee?auto=format&fit=crop&w=800&q=80", 0, 92, "https://trends.google.com/trends/explore?geo=US&q=AI%20Video%20Dubbing", "https://lista.mercadolivre.com.br/dublagem-ia", "https://www.google.com/search?q=AI+Video+Dubbing+Tool", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # EUROPA
            ("Notion Second Brain 2026 System", "Sistema Segundo Cérebro no Notion (Produtividade)", "Europa", "Europa (Reino Unido) 🇬🇧", "Templates & Planilhas", "ticket_baixo", "Template completo de gestão de projetos, finanças e metas pessoais com alta demanda na Europa.", "Custo zero de estoque e entrega imediata via link duplicável do Notion.", "Estudantes universitários, freelancers e criadores de conteúdo.", "Google Trends UK", "A partir de", "R$ 47", "★ 4.9 • Entrega imediata • Modelo Notion", "https://images.unsplash.com/photo-1484480974693-6ca0a78fb36b?auto=format&fit=crop&w=800&q=80", 0, 91, "https://trends.google.com/trends/explore?geo=GB&q=Notion%20Second%20Brain", "https://lista.mercadolivre.com.br/template-notion", "https://www.notion.so/templates/search?query=second+brain", "https://hotmart.com", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Portable Espresso Maker Travel", "Cafeteira Portátil de Pressão para Viagem e Escritório", "Europa", "Europa (Alemanha) 🇩🇪", "Produtos Validados", "faixa_media", "Gadget compacto que prepara café expresso sem eletricidade, viral em lojas europeias.", "Vídeos de demonstração com alto engajamento na Alemanha e Itália.", "Viajantes frequentes, motoristas, campistas e amantes de café.", "Google Trends DE", "Faixa de", "R$ 189", "★ 4.9 • Sucesso EU • Sem eletricidade", "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80", 0, 93, "https://trends.google.com/trends/explore?geo=DE&q=Portable%20Espresso%20Maker", "https://lista.mercadolivre.com.br/cafeteira-portatil-expresso", "https://pt.aliexpress.com/wholesale?SearchText=portable+espresso+maker", "https://www.amazon.com.br/s?k=cafeteira+portatil+expresso", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Smart Posture Corrector Sensor", "Corretor Postural Inteligente com Sensor de Vibração", "Europa", "Europa (Reino Unido) 🇬🇧", "Produtos Validados", "recorrencia", "Dispositivo discreto que vibra suavemente ao detectar má postura no computador.", "Grande procura entre trabalhadores em regime home office na Europa.", "Programadores, analistas, estudantes e trabalhadores de escritório.", "Google Trends UK", "Faixa de", "R$ 79", "★ 4.7 • Home Office • Uso diário", "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=800&q=80", 0, 88, "https://trends.google.com/trends/explore?geo=GB&q=Smart%20Posture%20Corrector", "https://lista.mercadolivre.com.br/corretor-postural-sensor", "https://pt.aliexpress.com/wholesale?SearchText=smart+posture+corrector", "https://www.amazon.com.br/s?k=corretor+postural+sensor", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Minimalist Desk Mat & Organizer", "Tapete de Mesa Ergonômico em Feltro & Organizador Setup", "Europa", "Europa (Alemanha) 🇩🇪", "Produtos Validados", "ticket_baixo", "Acessório minimalista campeão de buscas para organização de mesas de trabalho e estudo.", "Alta viralização em vídeos de setup minimalista e produtividade.", "Designers, editores, estudantes e profissionais de TI.", "Google Trends DE", "Faixa de", "R$ 69", "★ 4.8 • Setup Pro • Ticket baixo", "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?auto=format&fit=crop&w=800&q=80", 0, 89, "https://trends.google.com/trends/explore?geo=DE&q=Felt%20Desk%20Mat", "https://lista.mercadolivre.com.br/desk-mat-feltro", "https://pt.aliexpress.com/wholesale?SearchText=felt+desk+mat", "https://www.amazon.com.br/s?k=desk+mat+feltro", datetime.now().strftime("%d/%m/%Y %H:%M")),

            # AMÉRICA DO SUL
            ("Sistema Gestión Clínicas & Turnos AR", "Sistema Inteligente de Agendamento & Gestão de Clínicas", "América do Sul", "Argentina 🇦🇷", "Templates & Planilhas", "acesso_imediato", "Plataforma/planilha argentina de controle de pacientes, agendas e faturamento recorrente.", "Forte adoção por clínicas pequenas e consultórios buscando reduzir faltas.", "Fisioterapeutas, dentistas, psicólogos e clínicas de estética.", "Google Trends AR", "A partir de", "R$ 67", "★ 4.9 • LATAM • Acesso imediato", "https://images.unsplash.com/photo-1551288049-bebda4e38f71?auto=format&fit=crop&w=800&q=80", 0, 92, "https://trends.google.com/trends/explore?geo=AR&q=gestion%20turnos%20clinicas", "https://lista.mercadolivre.com.br/planilha-gestao-clinica", "https://hotmart.com/pt-br/marketplace/produtos?q=gestao+clinica", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Kit Mate Térmico Acero Inox UY", "Garrafa Térmica Inox de Precisão & Kit Chimarrão/Mate", "América do Sul", "Uruguai 🇺🇾", "Produtos Validados", "faixa_media", "Modelo térmico de alta retenção de temperatura campeão de vendas no Uruguai e Sul do Brasil.", "Alta demanda regional e ticket médio elevado com ótima comissão.", "Consumidores de chimarrão, tereré e bebidas térmicas.", "Tendência Sul-Americana", "Faixa de", "R$ 149", "★ 4.9 • Top UY • Alta durabilidade", "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=800&q=80", 0, 90, "https://www.google.com/search?q=termo+mate+acero+inoxidable+uruguay", "https://lista.mercadolivre.com.br/garrafa-termica-inox-mate", "https://www.amazon.com.br/s?k=garrafa+termica+inox+mate", "https://www.amazon.com.br/s?k=garrafa+termica+inox+mate", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Curso E-commerce & Dropshipping LATAM CO", "Método de Vendas Sem Estoque para América Latina", "América do Sul", "Colômbia 🇨🇴", "Cursos & IA", "acesso_imediato", "Treinamento colombiano focado em operação enxuta e fornecedores locais rápidos.", "Forte interesse de iniciantes buscando renda extra online sem estoque.", "Empreendedores iniciantes e lojistas virtuais.", "Google Trends CO", "Modalidade", "ACESSO COMPLETO", "★ 4.8 • Top CO • Sem estoque", "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?auto=format&fit=crop&w=800&q=80", 0, 88, "https://trends.google.com/trends/explore?geo=CO&q=curso%20ecommerce", "https://lista.mercadolivre.com.br/curso-ecommerce", "https://hotmart.com/pt-br/marketplace/produtos?q=ecommerce+sem+estoque", "https://hotmart.com", datetime.now().strftime("%d/%m/%Y %H:%M")),
            ("Plantilla Finanzas & Inversiones CL", "Planilha Automatizada de Fluxo de Caixa e Metas", "América do Sul", "Chile 🇨🇱", "Templates & Planilhas", "ticket_baixo", "Modelo financeiro limpo criado no Chile com gráficos automáticos de receitas e despesas.", "Alta procura por organização financeira pessoal e de pequenos negócios.", "Autônomos, pequenos comerciantes e famílias.", "Google Trends CL", "A partir de", "R$ 39", "★ 4.8 • Top CL • Entrega imediata", "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=800&q=80", 0, 90, "https://trends.google.com/trends/explore?geo=CL&q=plantilla%20finanzas", "https://lista.mercadolivre.com.br/planilha-fluxo-de-caixa", "https://hotmart.com/pt-br/marketplace/produtos?q=planilha+fluxo+de+caixa", "https://kiwify.com.br", datetime.now().strftime("%d/%m/%Y %H:%M"))
        ]
        c.executemany('''
            INSERT OR IGNORE INTO opportunities (
                term_origin, term_br, continent, region, format_type, offer_tag, description,
                why_trending, target_audience, source_name, price_prefix, price_value, social_proof,
                image_url, is_featured, gap_score, trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    offer_tag = "acesso_imediato" if fmt in ("Cursos & IA", "Templates & Planilhas") else "ticket_baixo"
    price_prefix = "Modalidade" if fmt == "Cursos & IA" else "Faixa de"
    price_value = "ACESSO IMEDIATO" if fmt == "Cursos & IA" else "R$ 79"
    social_proof = "★ 4.8 • Captado Ao Vivo • Radar 24h"
    desc = f"Oportunidade internacional captada via {source_name} ({region_label}) antes da saturação no Brasil." if geo_code != "BR" else f"Tendência em alta captada via {source_name}."
    why = f"Sinal validado em {region_label} pela fonte {source_name} com alto potencial de conversão."
    audience = "Empreendedores digitais, profissionais buscando produtividade ou consumidores de novidades."
    img_url = DEFAULT_IMAGES.get(fmt)
    trend_url = f"https://trends.google.com/trends/explore?geo={geo_code}&q={requests.utils.quote(term_origin)}"
    br_url = f"https://lista.mercadolivre.com.br/{requests.utils.quote(term_br)}"
    supp_url = build_supplier_url(fmt, term_origin, term_br)
    gap_score = 95 if geo_code in ("US", "GB", "DE") else 92

    try:
        c.execute('''
            INSERT INTO opportunities (
                term_origin, term_br, continent, region, format_type, offer_tag, description,
                why_trending, target_audience, source_name, price_prefix, price_value, social_proof,
                image_url, is_featured, gap_score, trend_source_url, br_market_url, supplier_url, affiliate_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (term_origin, term_br, continent, region_label, fmt, offer_tag, desc, why, audience, source_name, price_prefix, price_value, social_proof, img_url, 0, gap_score, trend_url, br_url, supp_url, br_url, datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def run_radar_cycle(nicho="geral"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    translator = GoogleTranslator(source='auto', target='pt')

    br_prefixes = ["melhor curso de ", "ferramenta de ia para ", "planilha de ", "melhor produto para "]
    for term in fetch_google_trends_rss("BR") + fetch_native_autocomplete("br", "pt-BR", br_prefixes):
        if is_commercial_opportunity(term, nicho):
            save_opportunity(c, conn, term, term.title(), "Brasil", "Brasil 🇧🇷", "Radar Nacional BR", "BR")

    if nicho == "brasil":
        conn.close()
        return

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

# --- 1. VITRINE PÚBLICA COM VALORES EM AMARELO-OURO DE ALTA DETECÇÃO VISUAL ---
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

        <div id="vitrine" class="mt-8 max-w-3xl mx-auto space-y-3.5">
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

            <div class="flex flex-wrap justify-center gap-1.5 text-[11px] font-bold pt-1">
                <button onclick="setOffer('ALL', this)" class="offer-btn bg-amber-400 text-slate-950 border border-amber-500 px-3 py-1 rounded-full transition">Todas as Ofertas</button>
                <button onclick="setOffer('ticket_baixo', this)" class="offer-btn bg-white text-slate-600 border border-slate-200 hover:border-amber-400 px-3 py-1 rounded-full transition">💸 Até R$ 100</button>
                <button onclick="setOffer('recorrencia', this)" class="offer-btn bg-white text-slate-600 border border-slate-200 hover:border-amber-400 px-3 py-1 rounded-full transition">🔄 Uso Diário & Recompra</button>
                <button onclick="setOffer('acesso_imediato', this)" class="offer-btn bg-white text-slate-600 border border-slate-200 hover:border-amber-400 px-3 py-1 rounded-full transition">⚡ Acesso Digital Imediato</button>
                <button onclick="setOffer('faixa_media', this)" class="offer-btn bg-white text-slate-600 border border-slate-200 hover:border-amber-400 px-3 py-1 rounded-full transition">💎 R$ 100 – R$ 250</button>
            </div>
        </div>
    </header>

    <!-- TOP 3 ACHADOS DA SEMANA (SEM DUPLICAR NO CATÁLOGO ABAIXO) -->
    <section id="destaques" class="max-w-5xl mx-auto px-4 mb-10">
        <div class="text-center mb-5">
            <span class="bg-amber-300 text-slate-950 text-[11px] font-black uppercase tracking-wider px-3.5 py-1 rounded-full shadow-sm">🔥 Top 3 Achados da Semana</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in featured_items %}}
            <div class="bg-white border-2 border-amber-400 rounded-2xl overflow-hidden shadow-md hover:shadow-lg transition flex flex-col justify-between text-center">
                <div>
                    <div class="relative h-40 w-full bg-slate-200 overflow-hidden">
                        <img src="{{{{ item[14] }}}}" alt="{{{{ item[2] }}}}" onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" class="w-full h-full object-cover">
                        <span class="absolute top-2.5 left-2.5 bg-amber-400 text-slate-950 text-[10px] font-black uppercase px-2.5 py-1 rounded-full shadow">🔥 Top 3</span>
                        <span class="absolute top-2.5 right-2.5 bg-slate-900/85 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">{{{{ item[4] }}}}</span>
                    </div>
                    <div class="p-5">
                        <span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">{{{{ item[5] }}}}</span>
                        <h3 class="text-lg font-extrabold text-[#0A2540] leading-snug mt-2">{{{{ item[2] }}}}</h3>
                        <p class="text-xs text-slate-600 mt-2 leading-relaxed">{{{{ item[7] }}}}</p>

                        <!-- FAIXA DE PREÇO AMARELO-OURO DE ALTA DETECÇÃO VISUAL -->
                        <div class="mt-3.5 bg-gradient-to-r from-amber-300 via-yellow-300 to-amber-300 border-2 border-amber-400 rounded-xl py-2.5 px-3 shadow-sm">
                            {{% if 'R$' in item[12] %}}
                            <div class="flex items-baseline justify-center gap-1.5">
                                <span class="text-[10px] font-black uppercase tracking-wider text-slate-900">{{{{ item[11] }}}}</span>
                                <span class="text-2xl font-black text-slate-950 tracking-tight">{{{{ item[12] }}}}</span>
                            </div>
                            {{% else %}}
                            <span class="inline-block bg-[#0A2540] text-amber-300 text-xs font-black tracking-wide px-3 py-1 rounded-lg uppercase">⚡ {{{{ item[12] }}}}</span>
                            {{% endif %}}
                            <p class="text-[10px] font-bold text-slate-900 mt-1">{{{{ item[13] }}}}</p>
                        </div>
                    </div>
                </div>
                <div class="px-5 pb-5">
                    <a href="{{{{ item[20] }}}}" target="_blank" class="block w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-sm transition shadow-sm">
                        {{{{ 'Acessar Treinamento / Ferramenta →' if item[5] == 'Cursos & IA' else ('Baixar Modelo Pronto →' if item[5] == 'Templates & Planilhas' else 'Conferir Menor Preço →') }}}}
                    </a>
                </div>
            </div>
            {{% endfor %}}
        </div>
    </section>

    <!-- CATÁLOGO COMPLETO (SEM REPETIR O TOP 3) -->
    <main class="max-w-5xl mx-auto px-4 pb-16">
        <div class="text-center mb-6">
            <h2 class="text-sm font-extrabold uppercase tracking-wider text-slate-500">Catálogo Completo Monitorado ({{{{ items|length }}}} Oportunidades)</h2>
        </div>
        <div id="cardsGrid" class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in items %}}
            <div class="opp-card bg-white border border-slate-200/90 rounded-2xl overflow-hidden shadow-sm hover:shadow-md transition flex flex-col justify-between text-center"
                 data-cont="{{{{ item[3] }}}}"
                 data-cat="{{{{ item[5] }}}}"
                 data-offer="{{{{ item[6] }}}}"
                 data-text="{{{{ item[2]|lower }}}} {{{{ item[1]|lower }}}} {{{{ item[7]|lower }}}} {{{{ item[4]|lower }}}}">
                <div>
                    <div class="relative h-36 w-full bg-slate-100 overflow-hidden">
                        <img src="{{{{ item[14] }}}}" alt="{{{{ item[2] }}}}" onerror="this.src='https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80'" class="w-full h-full object-cover">
                        <span class="absolute top-2.5 left-2.5 bg-white/95 text-slate-800 text-[10px] font-bold px-2.5 py-1 rounded-full shadow-sm">{{{{ item[4] }}}}</span>
                        <span class="absolute top-2.5 right-2.5 bg-sky-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-sm">{{{{ item[5] }}}}</span>
                    </div>
                    <div class="p-5">
                        <h3 class="text-base font-extrabold text-[#0A2540] leading-snug">{{{{ item[2] }}}}</h3>
                        <p class="text-xs text-slate-600 mt-2 leading-relaxed">{{{{ item[7] }}}}</p>

                        <!-- FAIXA DE PREÇO AMARELO-OURO DE ALTA DETECÇÃO VISUAL -->
                        <div class="mt-3.5 bg-gradient-to-r from-amber-200 via-yellow-200 to-amber-200 border border-amber-400 rounded-xl py-2 px-3 shadow-sm">
                            {{% if 'R$' in item[12] %}}
                            <div class="flex items-baseline justify-center gap-1.5">
                                <span class="text-[10px] font-black uppercase tracking-wider text-slate-800">{{{{ item[11] }}}}</span>
                                <span class="text-2xl font-black text-slate-950 tracking-tight">{{{{ item[12] }}}}</span>
                            </div>
                            {{% else %}}
                            <span class="inline-block bg-[#0A2540] text-amber-300 text-[11px] font-black tracking-wide px-2.5 py-1 rounded-lg uppercase">⚡ {{{{ item[12] }}}}</span>
                            {{% endif %}}
                            <p class="text-[10px] font-bold text-slate-800 mt-1">{{{{ item[13] }}}}</p>
                        </div>
                    </div>
                </div>
                <div class="px-5 pb-5">
                    <a href="{{{{ item[20] }}}}" target="_blank" class="block w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-2.5 rounded-xl text-xs transition shadow-sm">
                        {{{{ 'Acessar Treinamento / Ferramenta →' if item[5] == 'Cursos & IA' else ('Baixar Modelo Pronto →' if item[5] == 'Templates & Planilhas' else 'Conferir Menor
