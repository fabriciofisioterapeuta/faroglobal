import os
import time
import sqlite3
import threading
import requests
from datetime import datetime, timedelta
from functools import wraps
from deep_translator import GoogleTranslator
from pytrends.request import TrendReq
from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for

app = Flask(__name__)

# --- CONFIGURAÇÕES DE SEGURANÇA (Defina no painel do Render) ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "faroglobal-secret-key-2026")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@2026!")
CRON_SECRET_KEY = os.environ.get("CRON_SECRET_KEY", "radar2026")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DB_PATH = "faroglobal.db"

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

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_origin TEXT UNIQUE,
            term_br TEXT,
            region TEXT,
            format_type TEXT,
            br_listings INTEGER,
            gap_score INTEGER,
            origin_url TEXT,
            br_url TEXT,
            affiliate_url TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- ALERTA TELEGRAM ---
def send_telegram_alert(item):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    msg = (
        f"🚨 *FARO GLOBAL — NOVA OPORTUNIDADE (GAP: {item['gap_score']}/100)*\n\n"
        f"🌍 *Origem:* {item['region']} — {item['term_origin']}\n"
        f"🇧🇷 *Brasil:* {item['term_br']}\n"
        f"📦 *Formato:* {item['format_type']} | *Concorrentes BR:* {item['br_listings']}\n\n"
        f"🔗 [Ver Fonte Original]({item['origin_url']})\n"
        f"🔍 [Checar Brasil]({item['br_url']})"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception:
        pass

# --- MOTOR DE VARREDURA (EUA & EUROPA -> BRASIL) ---
def check_br_saturation(term_br):
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={requests.utils.quote(term_br)}&limit=1"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("paging", {}).get("total", 9999)
    except Exception:
        pass
    return 9999

def run_radar_cycle():
    regions = [
        ("united_states", "Estados Unidos 🇺🇸"),
        ("united_kingdom", "Europa (Reino Unido) 🇬🇧"),
        ("germany", "Europa (Alemanha) 🇩🇪")
    ]
    translator = GoogleTranslator(source='auto', target='pt')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for pn, region_label in regions:
        try:
            pytrends = TrendReq(hl='en-US', tz=360)
            df = pytrends.trending_searches(pn=pn)
            for term in df[0].tolist()[:6]:
                term_br = translator.translate(term)
                br_count = check_br_saturation(term_br)
                gap_score = 96 if br_count == 0 else (88 if br_count <= 5 else (78 if br_count <= 20 else 45))
                fmt = "Digital / Cursos & IA" if any(k in term.lower() for k in ["ai", "template", "notion", "app", "software", "course", "plan"]) else "Produto / Tendência"
                origin_url = f"https://www.google.com/search?q={requests.utils.quote(term)}"
                br_url = f"https://lista.mercadolivre.com.br/{requests.utils.quote(term_br)}"

                try:
                    c.execute('''
                        INSERT INTO opportunities (term_origin, term_br, region, format_type, br_listings, gap_score, origin_url, br_url, affiliate_url, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (term, term_br, region_label, fmt, br_count, gap_score, origin_url, br_url, br_url, datetime.now().strftime("%d/%m/%Y %H:%M")))
                    conn.commit()
                    if gap_score >= 80:
                        send_telegram_alert({"term_origin": term, "term_br": term_br, "region": region_label, "format_type": fmt, "br_listings": br_count, "gap_score": gap_score, "origin_url": origin_url, "br_url": br_url})
                except sqlite3.IntegrityError:
                    pass
                time.sleep(1.2)
        except Exception:
            continue
    conn.close()

# --- LOGO VETORIAL OFICIAL FARO GLOBAL ---
LOGO_SVG = """
<svg width="56" height="56" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" class="mx-auto">
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

# --- 1. SITE PÚBLICO CENTRALIZADO (faroglobal.com.br) ---
PUBLIC_HTML = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Faro Global • Radar de Tendências & Oportunidades</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans antialiased">
    <nav class="pt-5 px-4 flex justify-center">
        <div class="bg-white/90 backdrop-blur border border-slate-200 shadow-sm rounded-full px-5 py-2 flex items-center gap-4 text-xs font-semibold">
            <span class="text-emerald-600 flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> Radar Ativo 24/7</span>
            <span class="text-slate-300">|</span>
            <a href="/admin" class="text-slate-600 hover:text-slate-900 transition">Painel Administrativo</a>
        </div>
    </nav>

    <header class="max-w-4xl mx-auto px-4 pt-10 pb-8 text-center">
        {LOGO_SVG}
        <h1 class="mt-3 text-3xl md:text-4xl font-black tracking-tight">
            <span class="text-[#0A2540]">FARO</span> <span class="text-emerald-500">GLOBAL</span>
        </h1>
        <p class="text-[11px] font-bold tracking-[0.22em] text-[#0A2540] uppercase mt-1">Radar de Tendências & Oportunidades</p>
        <p class="mt-4 text-slate-600 text-sm md:text-base max-w-2xl mx-auto">
            Monitoramento automatizado dos mercados dos <strong>Estados Unidos</strong> e da <strong>Europa</strong> para você acessar ferramentas, cursos e produtos validados antes de virarem tendência no Brasil.
        </p>
    </header>

    <main class="max-w-5xl mx-auto px-4 pb-16">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            {{% for item in items %}}
            <div class="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm hover:shadow-md transition flex flex-col justify-between text-center">
                <div>
                    <div class="flex justify-center items-center gap-2 text-xs font-bold text-slate-500 mb-3">
                        <span class="bg-slate-100 px-2.5 py-1 rounded-full">{{{{ item[3] }}}}</span>
                        <span class="bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full">{{{{ item[4] }}}}</span>
                    </div>
                    <h3 class="text-lg font-extrabold text-[#0A2540]">{{{{ item[2] }}}}</h3>
                    <p class="text-xs text-slate-400 mt-1">Original: {{{{ item[1] }}}}</p>
                </div>
                <a href="{{{{ item[9] }}}}" target="_blank" class="mt-6 block w-full bg-[#0A2540] hover:bg-emerald-600 text-white font-bold py-3 rounded-xl text-sm transition">
                    Acessar Oportunidade →
                </a>
            </div>
            {{% else %}}
            <div class="col-span-3 text-center py-14 bg-white rounded-2xl border border-slate-200">
                <p class="text-slate-600 font-semibold">Radar pronto para operar. Entre no <a href="/admin" class="text-emerald-600 underline">Painel Administrativo</a> para iniciar a primeira varredura.</p>
            </div>
            {{% endfor %}}
        </div>
    </main>

    <footer class="border-t border-slate-200 py-8 text-center text-xs text-slate-500">
        <p class="font-bold text-[#0A2540]">FARO GLOBAL • faroglobal.com.br</p>
        <p class="mt-1">Inteligência de Mercado & Curadoria Internacional 24/7</p>
    </footer>
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

# --- 3. PAINEL ADMINISTRATIVO CENTRALIZADO ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin • Faro Global 24/7</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900 font-sans p-6">
    <div class="max-w-5xl mx-auto">
        <div class="bg-white border border-slate-200 rounded-2xl p-6 mb-8 text-center shadow-sm">
            <h1 class="text-2xl font-black text-[#0A2540]">📡 Central Administrativa • <span class="text-emerald-500">Faro Global</span></h1>
            <p class="text-xs text-slate-500 mt-1">Análise de Gap (EUA & Europa → Brasil) e Gestão de Links de Monetização</p>
            <div class="flex flex-wrap justify-center gap-3 mt-5">
                <a href="/admin/run-now" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-5 py-2.5 rounded-xl text-xs transition">⚡ Forçar Varredura Agora</a>
                <a href="/" target="_blank" class="bg-[#0A2540] hover:bg-slate-800 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition">Abrir Vitrine Pública</a>
                <a href="/admin/logout" class="bg-red-50 text-red-600 border border-red-200 font-semibold px-4 py-2.5 rounded-xl text-xs">Bloquear Painel</a>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            {% for item in items %}
            <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-bold text-sky-600">{{ item[3] }} • {{ item[4] }}</span>
                    <span class="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-extrabold px-2.5 py-0.5 rounded-full">Gap Score: {{ item[6] }}/100</span>
                </div>
                <h3 class="text-lg font-bold text-[#0A2540]">{{ item[2] }}</h3>
                <p class="text-xs text-slate-500 mb-3">Original: <b>{{ item[1] }}</b> | Concorrentes no Brasil: <b>{{ item[5] }}</b></p>
                <form method="POST" action="/admin/update-link/{{ item[0] }}" class="flex gap-2 mb-3">
                    <input type="url" name="affiliate_url" value="{{ item[9] }}" placeholder="Cole seu link Kiwify / Hotmart / Afiliado" class="flex-1 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs">
                    <button type="submit" class="bg-[#0A2540] hover:bg-emerald-600 text-white font-bold px-3.5 py-2 rounded-lg text-xs transition">Salvar</button>
                </form>
                <div class="flex gap-2 text-xs font-semibold">
                    <a href="{{ item[7] }}" target="_blank" class="flex-1 text-center bg-slate-100 py-2 rounded-lg hover:bg-slate-200">Ver Fonte Original</a>
                    <a href="{{ item[8] }}" target="_blank" class="flex-1 text-center bg-slate-100 py-2 rounded-lg hover:bg-slate-200">Checar Mercado BR</a>
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
    c.execute("SELECT * FROM opportunities WHERE gap_score >= 70 ORDER BY id DESC LIMIT 30")
    items = c.fetchall()
    conn.close()
    return render_template_string(PUBLIC_HTML, items=items)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if is_ip_blocked(ip):
        return render_template_string(LOGIN_HTML, error="Muitas tentativas incorretas. IP bloqueado por 30 minutos."), 429
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
    c.execute("SELECT * FROM opportunities ORDER BY gap_score DESC, id DESC LIMIT 50")
    items = c.fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, items=items)

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

@app.route("/admin/run-now")
@login_required
def run_now():
    threading.Thread(target=run_radar_cycle).start()
    return redirect(url_for("admin_dashboard"))

@app.route("/scan")
def cron_scan():
    if request.args.get("key") != CRON_SECRET_KEY:
        return jsonify({"error": "unauthorized"}), 401
    threading.Thread(target=run_radar_cycle).start()
    return jsonify({"status": "ok", "time": str(datetime.now())})

@app.route("/ping")
def ping():
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
