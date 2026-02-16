import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

# --- CONFIGURAÇÕES ---
# Lendo das Variáveis Ambientais do Render
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY') # Puxa a chave que você configurou no Render

# PARÂMETROS DE FILTRO
ODD_MINIMA = 1.25
ODD_MAXIMA = 3.50
JOGOS_POR_BILHETE = 1 # Enviará assim que achar 1 jogo para seu teste agora

# Cache local para evitar múltiplas requisições ao mesmo time no mesmo dia
cache_estatisticas = {}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Operacional - Monitorando Jogos")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def obter_media_gols_real(nome_time):
    agora = datetime.now()
    # Verifica se o time já foi consultado nas últimas 24h
    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        # 1. Busca o ID do time na API
        res_team = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", 
                                headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not res_team.get('response'):
            return 0
            
        team_id = res_team['response'][0]['team']['id']
        
        # 2. Busca
