import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

# Configurações de Ambiente
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
    # O Render usa a porta da variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check rodando na porta {port}")
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
    if not TELEGRAM_TOKEN or not CHAT_ID: 
        print("Telegram Token ou Chat ID ausente.")
        return
    # CORREÇÃO DA LINHA 52: URL completa e aspas fechadas
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")

# Iniciar servidor de Health Check em uma thread separada para o Render não dar timeout
threading.Thread(target=run_health_check, daemon=True).start()

# Exemplo de loop principal para o bot não fechar
if __name__ == "__main__":
    print("Bot iniciado com sucesso!")
    enviar_msg("🚀 *Bot de Apostas Online e Operacional!*")
    
    while True:
        # Aqui viria sua lógica de busca de odds e análise
        time.sleep(3600) # Espera 1 hora para a próxima verificação
