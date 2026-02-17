import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

ODD_MINIMA = 1.25
ODD_MAXIMA = 3.50
JOGOS_POR_BILHETE = 2 

cache_estatisticas = {}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot OK")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def obter_media_gols_real(nome_time):
    agora = datetime.now()
    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']
    
    headers = {"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"}
    try:
        res_t = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", headers=headers, params={"search": nome_time}, timeout=10).json()
        if not res_t.get('response'): return 0
        tid = res_t['response'][0]['team']['id']
        res_f = requests.get("https://api-football-v1.p.rapidapi.com/v3/fixtures", headers=headers, params={"team": tid, "last": 5}, timeout=10).json()
        total = sum((f['goals']['home'] or 0) + (f['goals']['away'] or 0) for f in res_f.get('response', []))
        count = len(res_f.get('response', []))
        media = total / count if count > 0 else 0
        cache_estatisticas[nome_time] = {"media": media, "expira": agora + timedelta(hours=24)}
        return media
    except:
        return 0

def enviar_msg(texto):
    if not TELEGRAM_TOKEN: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=20)

def buscar_palpites():
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    try:
        res = requests.get(url, timeout=30).json()
        agora = datetime.now(timezone.utc)
        lista = []
        
        # Dicionário de tradução para exibição
        traducoes = {"Over": "Acima de", "Under": "Abaixo de"}

        for jogo in res:
            try:
                dt = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt <= agora: continue
                mkt = next((m for m in jogo['bookmakers'][0]['markets'] if m['key'] == 'totals'), None)
                if not mkt: continue
                
                escolha = min([o for o in mkt['outcomes'] if ODD_MINIMA <= o['price'] <= ODD_MAXIMA], key=lambda x: x['price'])
                
                m_home = obter_media_gols_real(jogo['home_team'])
                m_away = obter_media_gols_real(jogo['away_team'])
                media = (m_home + m_away) / 2
                
                # A lógica de análise mantém o nome original da API
                if (escolha['name'].lower() == "over" and media >= escolha['point']) or (escolha['name'].lower() == "under" and media <= escolha['point']):
                    lista.append({
                        'l': jogo['sport_title'], 
                        't': f"{jogo['home_team']} x {jogo['away_team']}", 
                        'h': dt.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"), 
                        'p': traducoes.get(escolha['name'], escolha['name']), # Traduz apenas para o bilhete
                        'pt': escolha['point'], 
                        'o': escolha['price'], 
                        'm': round(media, 2), 
                        'ts': dt
                    })
            except: continue

        if len(lista) >= JOGOS_POR_BILHETE:
            lista.sort(key=lambda x: x['ts'])
            selecionados = lista[:JOGOS_POR_BILHETE]
            
            msg = "💎 *BILHETE GERADO*\n"
            odd_acumulada = 1.0
            
            for s in selecionados:
                msg += f"\n🏆 {s['l']}\n⏰ {s['h']} - {s['t']}\n🔥 {s['p']} {s['pt']} Gols (@{s['o']})\n📊 Média: {s['m']}\n"
                odd_acumulada *= s['o']
            
            msg += f"\n💰 *Odd Total: {round(odd_acumulada, 2)}*"
            return msg
            
        return f"ℹ️ Analisando: {len(lista)} aprovados."
    except Exception
