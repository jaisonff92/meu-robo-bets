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
# Chave extraída da sua imagem do RapidAPI
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY', 'd473e6b9amsh975ef6df91017dap1b8259jsn7bad65cc2295')

ODD_MINIMA = 1.50
ODD_MAXIMA = 2.25
JOGOS_POR_BILHETE = 3

# Dicionário para armazenar médias e economizar API (Cache)
# Estrutura: {"Nome do Time": {"media": 2.5, "expira": datetime}}
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
    
    # Verifica se já temos o time no cache e se ainda é válido (24h)
    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        # 1. Busca o ID do time
        res_team = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", 
                                headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not res_team.get('response'):
            return 0
            
        team_id = res_team['response'][0]['team']['id']

        # 2. Busca os últimos 5 jogos
        res_fixtures = requests.get("https://api-football-v1.p.rapidapi.com/v3/fixtures", 
                                   headers=headers, params={"team": team_id, "last": 5}, timeout=10).json()
        
        total_gols = 0
        jogos_contados = 0
        for f in res_fixtures.get('response', []):
            gols_jogo = (f['goals']['home'] or 0) + (f['goals']['away'] or 0)
            total_gols += gols_jogo
            jogos_contados += 1
        
        media = total_gols / jogos_contados if jogos_contados > 0 else 0
        
        # Salva no cache por 24 horas
        cache_estatisticas[nome_time] = {
            "media": media,
            "expira": agora + timedelta(hours=24)
        }
        
        return media
    except Exception as e:
        print(f"Erro ao buscar stats para {nome_time}: {
