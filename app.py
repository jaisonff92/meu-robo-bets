import requests
import time
from datetime import datetime, timezone
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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
# SERVIDOR WEB FANTASMA (PARA O RENDER NÃO DESLIGAR O BOT)
# ==========================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot de Apostas rodando com sucesso!")

def keep_alive_server():
    """Cria um servidor local para o Render reconhecer que o Web Service está ativo."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Servidor web fantasma rodando na porta {port} para manter o Render ativo...")
    server.serve_forever()

# ==========================================
# LÓGICA DO BOT DE APOSTAS
# ==========================================
def get_all_soccer_leagues():
    """Busca dinamicamente todas as ligas de futebol ativas no mundo."""
    url = 'https://api.the-odds-api.com/v4/sports'
    params = {'apiKey': API_KEY_ODDS}
    response = requests.get(url, params=params)
    
    leagues = []
    if response.status_code == 200:
        for sport in response.json():
            if sport.get('group') == 'Soccer':
                leagues.append(sport['key'])
    else:
        print("Erro ao buscar ligas: " + response.text)
        
    return leagues

def get_upcoming_matches(leagues):
    """Busca jogos pré-live e odds de Ambos Marcam para todas as ligas mundiais."""
    all_matches = []
    
    print("Baixando odds para " + str(len(leagues)) + " ligas globais...")
    for league in leagues:
        url = 'https://api.the-odds-api.com/v4/sports/' + league + '/odds'
        params = {
            'apiKey': API_KEY_ODDS,
            'regions': 'eu,uk', 
            'markets': 'btts',
            'oddsFormat': 'decimal',
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            all_matches.extend(response.json())
        elif response.status_code == 429:
            print("AVISO: Limite da The Odds API atingido.")
            break
            
        time.sleep(0.2) 
            
    return all_matches

def get_team_id(team_name):
    """Busca o ID do time na API-Football usando o nome."""
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    search_name = team_name.split()[0] 
    
    response = requests.get(url, headers=HEADERS_RAPIDAPI, params={"search": search_name})
    data = response.json()
    
    if data.get('response') and len(data['response']) > 0:
        return data['response'][0]['team']['id']
    return None

def calculate_btts_percentage(team_id):
    """Busca os últimos 5 jogos reais do time e calcula a % de Ambos Marcam."""
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
    """Cruza o histórico real de ambos os times."""
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
    """Varre o mundo usando o pré-filtro e retorna as 5 melhores opções."""
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
    
    print("Pré-filtro concluiu. Checando histórico dos " + str(len(targets)) + " jogos mais prováveis do mundo...")
    
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
            'match': home_team + " x " + away_team,
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
    """Envia o resultado para o Telegram sem usar colchetes na URL para evitar erros de sintaxe."""
    # O URL agora usa sinais de mais (+) ao invés de chaves ({})
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print("Erro ao enviar para o Telegram: " + response.text)
    except Exception as e:
        print("Erro de conexão ao tentar enviar mensagem: " + str(e))

def main():
    print("1. Mapeando todas as ligas mundiais disponíveis...")
    leagues = get_all_soccer_leagues()
    
    if not leagues:
        print("Erro ao carregar as ligas mundiais.")
        return
        
    print("2. Buscando a grade completa de jogos mundiais...")
    matches = get_upcoming_matches(leagues)
    
    if not matches:
        print("Nenhum jogo encontrado na varredura global.")
        return
        
    print("3. Executando inteligência de filtro e estatística...")
    top_5 = analyze_btts_opportunities(matches)
    
    if not top_5:
        msg_erro = "🤖 A varredura mundial terminou, mas nenhum jogo bateu os 65% de confiança nas estatísticas para hoje."
        send_telegram_message(msg_erro)
        print(msg_erro)
        return

    msg = "🌍 <b>TOP 5 MUNDIAL - AMBOS MARCAM</b> 🌍\n"
    msg += "<i>Analisado em todas as ligas globais ativas</i>\n\n"
    
    for i, match in enumerate(top_5, 1):
        icone = "✅" if match['recommendation'] == "SIM" else "❌"
        msg += "<b>" + str(i) + ". " + match['match'] + "</b>\n"
        msg += "🏆 Liga: " + match['league'] + "\n"
        msg += "🕒 Início: " + match['start_time'] + "\n"
        msg += "📊 Recomendação: <b>Ambos Marcam " + match['recommendation'] + "</b> " + icone + "\n"
        msg += "📈 Confiança do Histórico: " + str(round(match['probability'], 1)) + "%\n"
        msg += "💰 Odd: <b>" + str(match['odd']) + "</b> (" + match['bookmaker'] + ")\n"
        msg += "➖" * 12 + "\n"
        
    send_telegram_message(msg)
    print("✅ Lista mundial enviada para o Telegram!")

if __name__ == "__main__":
    # 1. Inicia o servidor fantasma para o Render não matar o processo
    threading.Thread(target=keep_alive_server, daemon=True).start()
    
    # 2. Roda o bot continuamente
    print("Iniciando o loop principal do Bot Global...")
    while True:
        try:
            main()
        except Exception as e:
            print("Ocorreu um erro crítico durante a execução: "
