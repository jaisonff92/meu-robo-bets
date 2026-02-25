import requests
import time
from datetime import datetime, timezone
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import builtins

# Força o Python a mostrar os prints imediatamente
def print_flush(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)
print = print_flush

# ==========================================
# CONFIGURAÇÕES E CHAVES
# ==========================================
TELEGRAM_TOKEN = '8348998630:AAEtB2fQTIKkn2_w6dLmzfSMm7Jhl85vX9M'
CHAT_ID = '8073333859'
API_KEY_ODDS = '4fca1f2e9d9cca4384f0003c81aab497'
RAPIDAPI_KEY = 'd473e6bd9amsh975ef6df91017dap1b8259jsn7bad65cc2295'

HEADERS_RAPIDAPI = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# ==========================================
# SERVIDOR WEB FANTASMA (PARA O RENDER)
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot online e aguardando comandos no Telegram!")

def keep_alive_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print("Servidor fantasma rodando na porta " + str(port))
    server.serve_forever()

# ==========================================
# LÓGICA DO BOT DE APOSTAS
# ==========================================
def get_all_soccer_leagues():
    url = 'https://api.the-odds-api.com/v4/sports'
    params = {'apiKey': API_KEY_ODDS}
    response = requests.get(url, params=params)
    
    leagues = []
    if response.status_code == 200:
        for sport in response.json():
            if sport.get('group') == 'Soccer':
                leagues.append(sport['key'])
    return leagues

def get_upcoming_matches(leagues):
    all_matches = []
    for league in leagues:
        url = 'https://api.the-odds-api.com/v4/sports/' + league + '/odds'
        params = {
            'apiKey': API_KEY_ODDS,
            'regions': 'eu,uk,us,au', 
            'markets': 'btts',
            'oddsFormat': 'decimal',
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            all_matches.extend(response.json())
        elif response.status_code == 429:
            print("AVISO: Limite da The Odds API atingido!")
            break
        time.sleep(0.2) 
    return all_matches

def get_team_id(team_name):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    search_name = team_name.split()[0] 
    response = requests.get(url, headers=HEADERS_RAPIDAPI, params={"search": search_name})
    data = response.json()
    if data.get('response') and len(data['response']) > 0:
        return data['response'][0]['team']['id']
    return None

def calculate_btts_percentage(team_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"team": team_id, "last": 5}
    response = requests.get(url, headers=HEADERS_RAPIDAPI, params=params)
    data = response.json()
    if not data.get('response'):
        return 50.0 
    btts_count = 0
    total_games = len(data['response'])
    for match in data['response']:
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']
        if goals_home is not None and goals_away is not None:
            if goals_home > 0 and goals_away > 0:
                btts_count += 1
    return (btts_count / total_games) * 100

def get_historical_btts_probability(home_team, away_team):
    home_id = get_team_id(home_team)
    time.sleep(0.5) 
    away_id = get_team_id(away_team)
    time.sleep(0.5)
    if not home_id or not away_id:
        return 50.0, 50.0
    home_btts_pct = calculate_btts_percentage(home_id)
    time.sleep(0.5)
    away_btts_pct = calculate_btts_percentage(away_id)
    time.sleep(0.5)
    prob_yes = (home_btts_pct + away_btts_pct) / 2
    prob_no = 100.0 - prob_yes
    return prob_yes, prob_no

def analyze_btts_opportunities(matches):
    now = datetime.now(timezone.utc)
    pre_filtered_matches = []
    for match in matches:
        try:
            commence_time = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
            if commence_time <= now:
                continue
            bookmaker = match['bookmakers'][0]
            market = bookmaker['markets'][0]
            odd_yes = next(item['price'] for item in market['outcomes'] if item['name'] == 'Yes')
            odd_no = next(item['price'] for item in market['outcomes'] if item['name'] == 'No')
            if odd_yes <= 1.80 or odd_no <= 1.80:
                pre_filtered_matches.append({
                    'raw': match,
                    'commence_time': commence_time,
                    'odd_yes': odd_yes,
                    'odd_no': odd_no,
                    'bookmaker': bookmaker['title']
                })
        except Exception:
            continue
            
    pre_filtered_matches.sort(key=lambda x: min(x['odd_yes'], x['odd_no']))
    analyzed_matches = []
    targets = pre_filtered_matches[:10]
    
    for item in targets:
        match = item['raw']
        home_team = match['home_team']
        away_team = match['away_team']
        prob_yes, prob_no = get_historical_btts_probability(home_team, away_team)
        
        if prob_yes >= 65.0:
            recommendation = "SIM"
            prob = prob_yes
            odd = item['odd_yes']
        elif prob_no >= 65.0:
            recommendation = "NÃO"
            prob = prob_no
            odd = item['odd_no']
        else:
            continue 
            
        analyzed_matches.append({
            'match': home_team.replace('&', 'e').replace('<', '') + " x " + away_team.replace('&', 'e').replace('<', ''),
            'league': match['sport_title'],
            'start_time': item['commence_time'].strftime('%d/%m %H:%M'),
            'recommendation': recommendation,
            'probability': prob,
            'odd': odd,
            'bookmaker': item['bookmaker']
        })

    analyzed_matches.sort(key=lambda x: x['probability'], reverse=True)
    return analyzed_matches[:5]

def send_telegram_message(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
         print("Erro de conexão ao enviar mensagem: " + str(e))

def run_analysis():
    """Função que executa a varredura completa quando o comando é acionado."""
    print("=======================================")
    print("INICIANDO BUSCA MUNDIAL PELO COMANDO: " + datetime.now().strftime('%H:%M:%S'))
    
    leagues = get_all_soccer_leagues()
    if not leagues:
        send_telegram_message("🤖 Alerta: Nenhuma liga encontrada na API de odds.")
        return
        
    matches = get_upcoming_matches(leagues)
    if not matches:
        send_telegram_message("🤖 Alerta: Nenhum jogo futuro com mercado BTTS encontrado agora.")
        return
        
    top_5 = analyze_btts_opportunities(matches)
    
    if not top_5:
        send_telegram_message("🤖 Varredura concluída. Nenhum jogo com 65% de confiança estatística no momento.")
        return

    msg = "🌍 <b>TOP 5 (AMÉRICAS, EUROPA E ÁSIA) - AMBOS MARCAM</b> 🌍\n\n"
    for i, match in enumerate(top_5, 1):
        icone = "✅" if match['recommendation'] == "SIM" else "❌"
        msg += "<b>" + str(i) + ". " + match['match'] + "</b>\n"
        msg += "🏆 Liga: " + match['league'] + "\n"
        msg += "🕒 Início: " + match['start_time'] + "\n"
        msg += "📊 Recomendação: <b>BTTS " + match['recommendation'] + "</b> " + icone + "\n"
        msg += "📈 Confiança: " + str(round(match['probability'], 1)) + "%\n"
        msg += "💰 Odd: <b>" + str(match['odd']) + "</b>\n"
        msg += "➖" * 12 + "\n"
        
    send_telegram_message(msg)
    print("Busca concluída e enviada!")

# ==========================================
# OUVINTE DO TELEGRAM (LISTENER)
# ==========================================
def listen_for_commands():
    """Fica escutando o chat do Telegram em busca de comandos."""
    print("🤖 Bot conectado ao Telegram! Aguardando você digitar /buscar...")
    offset = None
    
    while True:
        try:
            # Pede para a API do Telegram as últimas mensagens enviadas para o bot
            url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/getUpdates?timeout=30"
            if offset:
                url += "&offset=" + str(offset)
            
            response = requests.get(url, timeout=40)
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    # Marca a mensagem como lida
                    offset = update["update_id"] + 1
                    
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    
                    # Se você enviou /buscar no seu chat, ele aciona o motor!
                    if text == "/buscar" and chat_id == CHAT_ID:
                        send_telegram_message("🔎 <b>Comando recebido!</b> Iniciando a varredura das odds mundiais. Te envio o bilhete em alguns segundos...")
                        
                        # Roda a busca em segundo plano para não travar o ouvinte
                        threading.Thread(target=run_analysis).start()
                        
        except requests.exceptions.Timeout:
            continue # Timeout normal do Telegram, apenas tenta de novo
        except Exception as e:
            print("Erro no listener do Telegram: " + str(e))
            time.sleep(5)

if __name__ == "__main__":
    # 1. Inicia o servidor para o Render manter o programa online
    threading.Thread(target=keep_alive_server, daemon=True).start()
    
    # 2. Inicia o ouvinte do Telegram que vai ficar aguardando o seu comando para sempre
    listen_for_commands()
