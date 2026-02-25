import requests
import time
from datetime import datetime, timezone

# ==========================================
# CONFIGURAÇÕES E CHAVES
# ==========================================
TELEGRAM_TOKEN = '8348998630:AAEtB2fQTIKkn2_w6dLmzfSMm7Jhl85vX9M'
CHAT_ID = '8073333859'
API_KEY_ODDS = '4fca1f2e9d9cca4384f0003c81aab497'
RAPIDAPI_KEY = 'd473e6bd9amsh975ef6df91017dap1b8259jsn7bad65cc2295'

# Ligas mais relevantes para focar as requisições
RELEVANT_LEAGUES = [
    'soccer_epl',             # Premier League
    'soccer_spain_la_liga',   # La Liga
    'soccer_italy_serie_a',   # Serie A
    'soccer_brazil_campeonato'# Brasileirão Série A
]

HEADERS_RAPIDAPI = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

def get_upcoming_matches():
    """Busca jogos pré-live e odds de Ambos Marcam na The Odds API."""
    all_matches = []
    
    for league in RELEVANT_LEAGUES:
        url = f'https://api.the-odds-api.com/v4/sports/{league}/odds'
        params = {
            'apiKey': API_KEY_ODDS,
            'regions': 'eu',
            'markets': 'btts',
            'oddsFormat': 'decimal',
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            all_matches.extend(response.json())
            
    return all_matches

def get_team_id(team_name):
    """Busca o ID do time na API-Football usando o nome."""
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    # Pegamos apenas a primeira palavra do time para facilitar o "match" entre APIs diferentes
    search_name = team_name.split()[0] 
    
    response = requests.get(url, headers=HEADERS_RAPIDAPI, params={"search": search_name})
    data = response.json()
    
    if data.get('response') and len(data['response']) > 0:
        return data['response'][0]['team']['id']
    return None

def calculate_btts_percentage(team_id):
    """Busca os últimos 5 jogos do time e calcula a % de Ambos Marcam."""
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    params = {"team": team_id, "last": 5}
    
    response = requests.get(url, headers=HEADERS_RAPIDAPI, params=params)
    data = response.json()
    
    if not data.get('response'):
        return 50.0 # Retorna 50% como neutro se não achar dados
        
    btts_count = 0
    total_games = len(data['response'])
    
    for match in data['response']:
        goals_home = match['goals']['home']
        goals_away = match['goals']['away']
        
        # Se nenhum for None e ambos forem maiores que 0, foi BTTS SIM
        if goals_home is not None and goals_away is not None:
            if goals_home > 0 and goals_away > 0:
                btts_count += 1
                
    return (btts_count / total_games) * 100

def get_historical_btts_probability(home_team, away_team):
    """Cruza o histórico real de ambos os times."""
    home_id = get_team_id(home_team)
    time.sleep(0.5) # Pausa para não tomar block da RapidAPI
    away_id = get_team_id(away_team)
    time.sleep(0.5)
    
    if not home_id or not away_id:
        return 50.0, 50.0
        
    home_btts_pct = calculate_btts_percentage(home_id)
    time.sleep(0.5)
    away_btts_pct = calculate_btts_percentage(away_id)
    time.sleep(0.5)
    
    # Média de chance do BTTS SIM acontecer baseado na fase dos dois times
    prob_yes = (home_btts_pct + away_btts_pct) / 2
    prob_no = 100.0 - prob_yes
    
    return prob_yes, prob_no

def analyze_btts_opportunities(matches):
    """Analisa e ranqueia as opções."""
    analyzed_matches = []
    now = datetime.now(timezone.utc)
    
    # Limitando a análise aos primeiros 15 jogos para poupar requisições da sua API
    for match in matches[:15]: 
        try:
            commence_time = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
            
            if commence_time <= now:
                continue
                
            home_team = match['home_team']
            away_team = match['away_team']
            
            print(f"Analisando estatísticas de: {home_team} x {away_team}...")
            prob_yes, prob_no = get_historical_btts_probability(home_team, away_team)
            
            bookmaker = match['bookmakers'][0]
            market = bookmaker['markets'][0]
            
            odd_yes = next(item['price'] for item in market['outcomes'] if item['name'] == 'Yes')
            odd_no = next(item['price'] for item in market['outcomes'] if item['name'] == 'No')
            
            # Filtro de confiança: Só pega se o histórico indicar mais de 65% de chance
            if prob_yes >= 65.0:
                recommendation = "SIM"
                prob = prob_yes
                odd = odd_yes
            elif prob_no >= 65.0:
                recommendation = "NÃO"
                prob = prob_no
                odd = odd_no
            else:
                continue 
                
            analyzed_matches.append({
                'match': f"{home_team} x {away_team}",
                'league': match['sport_title'],
                'start_time': commence_time.strftime('%d/%m %H:%M'),
                'recommendation': recommendation,
                'probability': prob,
                'odd': odd,
                'bookmaker': bookmaker['title']
            })
            
        except Exception as e:
            continue

    analyzed_matches.sort(key=lambda x: x['probability'], reverse=True)
    return analyzed_matches[:10]

def send_telegram_message(message):
    """Envia a mensagem via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)

def main():
    print("1. Buscando jogos pré-live na API de Odds...")
    matches = get_upcoming_matches()
    
    if not matches:
        print("Nenhum jogo encontrado.")
        return
        
    print(f"2. Cruzando dados de {min(len(matches), 15)} jogos com histórico da RapidAPI...")
    top_10 = analyze_btts_opportunities(matches)
    
    if not top_10:
        msg_erro = "🤖 Sem dados suficientes com alta confiança (>65%) para montar um Top 10 hoje."
        send_telegram_message(msg_erro)
        print(msg_erro)
        return

    msg = "🎯 <b>TOP 10 - AMBOS MARCAM (DADOS REAIS DA API)</b> 🎯\n\n"
    
    for i, match in enumerate(top_10, 1):
        icone = "✅" if match['recommendation'] == "SIM" else "❌"
        msg += f"<b>{i}. {match['match']}</b>\n"
        msg += f"🏆 Liga: {match['league']}\n"
        msg += f"🕒 Início: {match['start_time']}\n"
        msg += f"📊 Recomendação: <b>Ambos Marcam {match['recommendation']}</b> {icone}\n"
        msg += f"📈 Confiança do Histórico: {match['probability']:.1f}%\n"
        msg += f"💰 Odd: <b>{match['odd']}</b> ({match['bookmaker']})\n"
        msg += "➖" * 12 + "\n"
        
    send_telegram_message(msg)
    print("✅ Lista final calculada e enviada para o Telegram!")

if __name__ == "__main__":
    main()
