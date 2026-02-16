import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

# --- CONFIGURAÇÕES ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'd473e6b9amsh975ef6df91017dap1b8259jsn7bad65cc2295')

ODD_MINIMA = 1.50
ODD_MAXIMA = 2.25
JOGOS_POR_BILHETE = 1  # Ajustado para 1 para seu teste imediato

# Cache para economizar API-Football (limite 100/dia)
cache_estatisticas = {}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Ativo com Cache")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def obter_media_gols_real(nome_time):
    agora = datetime.now()
    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        res_team = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", 
                                headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not res_team.get('response'):
            return 0
            
        team_id = res_team['response'][0]['team']['id']
        res_fixtures = requests.get("https://api-football-v1.p.rapidapi.com/v3/fixtures", 
                                   headers=headers, params={"team": team_id, "last": 5}, timeout=10).json()
        
        total_gols = 0
        jogos_contados = 0
        for f in res_fixtures.get('response', []):
            g_h = f['goals']['home'] if f['goals']['home'] is not None else 0
            g_a = f['goals']['away'] if f['goals']['away'] is not None else 0
            total_gols += (g_h + g_a)
            jogos_contados += 1
        
        media = total_gols / jogos_contados if jogos_contados > 0 else 0
        cache_estatisticas[nome_time] = {
            "media": media,
            "expira": agora + timedelta(hours=24)
        }
        return media
    except Exception as e:
        print(f"Erro ao buscar stats para {nome_time}: {e}")
        return 0

def enviar_msg(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=20)
    except: pass

def buscar_palpites():
    url_odds = f"https://api
