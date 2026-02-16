import requests
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Ativo")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')

ODD_MINIMA = 1.50
ODD_MAXIMA = 2.25
JOGOS_POR_BILHETE = 3

def enviar_msg(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=20)
    except:
        pass

def buscar_palpites():
    if not API_KEY_ODDS:
        return "Erro: API_KEY faltando"
    
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    
    try:
        res = requests.get(url, timeout=30)
        dados = res.json()
        if not isinstance(dados, list):
            return "Erro na resposta da API"

        agora = datetime.now(timezone.utc)
        lista = []
        
        for jogo in dados:
            try:
                dt = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt <= agora:
                    continue
                
                bks = jogo.get('bookmakers', [])
                if not bks:
                    continue
                mkt = bks[0].get('markets', [])
                if not mkt:
                    continue
                outcomes = mkt[0].get('outcomes', [])
                
                viaveis = [o for o in outcomes if ODD_MINIMA <= o['price'] <= ODD_MAXIMA]
                if not viaveis:
                    continue
                
                escolha = min(viaveis, key=lambda x: x['price'])
                traducao = "Mais de" if escolha['name'].lower() == "over" else "Menos de"
                
                lista.append({
                    'liga': jogo['sport_title'],
                    'times': f"{jogo['home_team']} x {jogo['away_team']}",
                    'hora': dt.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"),
                    'palpite': traducao,
                    'ponto': escolha['point'],
                    'odd': escolha['price'],
                    'ts': dt
                })
            except:
                continue

        if len(lista) < JOGOS_POR_BILHETE:
            return "Sem jogos suficientes no criterio"
        
        lista.sort(key=lambda x: x['ts'])
        tops = lista[:JOGOS_POR_BILHETE]
        
        msg = "💎 *BILHETE DE ALTO VALOR* 💎\n\n"
        total = 1.0
        for s in tops:
            total *= s['odd']
            msg += f"🏆 *{s['liga']}*\n⏰ {s['hora']} - {s['times']}\n🔥 *{s['palpite']} {s['ponto']} Gols* (@{s['odd']})\n\n"
        
        msg += f"--------------------------\n💰 *ODD TOTAL: {total:.2f}*"
        return msg
    except Exception as e:
        return f"Erro de conexao: {e}"

if __name__ == "__main__":
    threading.Thread(target=run_health_check, daemon=True).start()
    print("🚀 Robo Iniciado com Sucesso!")
    
    while True:
        bilhete = buscar_palpites()
        if "💎" in bilhete:
            enviar_msg(bilhete)
            print("✅ Bilhete enviado ao Telegram")
        else:
            print(f"ℹ️ {bilhete}")
        
        time.sleep(3600)
