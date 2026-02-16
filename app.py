import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

# --- SISTEMA PARA MANTER O RENDER VIVO (HEALTH CHECK) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- CONFIGURAÇÕES VIA VARIÁVEIS DE AMBIENTE ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')

ODD_MINIMA_JOGO = 1.50
ODD_MAXIMA_JOGO = 2.25
JOGOS_POR_BILHETE = 3

def enviar_para_telegram(mensagem):
    if not TELEGRAM_TOKEN or not CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=20)
        return True
    except:
        return False

def buscar_palpites_lucrativos():
    if not API_KEY_ODDS: return "❌ Erro: Chave API ausente."
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        dados = response.json()
        if not isinstance(dados, list): return "⚠️ Erro API."

        agora_utc = datetime.now(timezone.utc)
        lista_de_valor = []
        for jogo in dados:
            try:
                dt_jogo = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt_jogo <= agora_utc: continue
                bks = jogo.get('bookmakers', [])
                if not bks: continue
                mkts = bks[0].get('markets', [])
                outcomes = mkts[0].get('outcomes', [])
                
                opcoes = [o for o in outcomes if ODD_MINIMA_JOGO <= o['price'] <= ODD_MAXIMA_JOGO]
                if not opcoes: continue
                escolha = min(opcoes, key=lambda x: x['price'])
                
                lista_de_valor.append({
                    'liga': jogo['sport_title'],
                    'times': f"{jogo['home_team']} x {jogo['away_team']}",
                    'horario': dt_jogo.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"),
                    'palpite': "Mais de" if escolha['name'].lower() == "over" else "Menos de",
                    'ponto': escolha['point'],
                    'odd': escolha['price'],
                    'timestamp': dt_jogo
                })
            except: continue

        if len(lista_de_valor) < JOGOS_POR_BILHETE: return "⚠️ Sem jogos no critério."
        lista_de_valor.sort(key=lambda x: x['timestamp'])
        selecionados = lista_de_valor[:JOGOS_POR_BILHETE]
        
        texto = "💎 *BILHETE DE ALTO VALOR* 💎\n--------------------------------------\n"
        odd_final = 1.0
        for s in selecionados:
            odd_final *= s['odd']
            texto += f"🏆 *{s['liga']}*\n⏰ {s['horario']} - {s['times']}\n🔥 *{s['palpite']} {s['ponto']}* (@{s['odd']})\n\n"
        texto += f"--------------------------------------\n💰 *ODD TOTAL: {odd_final:.2f}*"
        return texto
    except Exception as e: return f"❌ Erro: {e}"

if __name__ == "__main__":
    # Inicia servidor de saúde em segundo plano para o Render não desligar
    threading.Thread(target=run_health_check, daemon=True).start()
    
    print("🚀 Robô Online no Render!")
    while True:
        resultado = buscar_palpites_lucrativos()
        if "💎" in resultado:
            enviar_para_telegram(resultado)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Bilhete enviado!")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {resultado}")
        
        time.sleep(3600) # Espera 1 hora
