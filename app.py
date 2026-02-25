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

HEADERS_RAPIDAPI = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

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
        print(f"Erro ao buscar ligas: {response.text}")
        
    return leagues

def get_upcoming_matches(leagues):
    """Busca jogos pré-live e odds de Ambos Marcam para todas as ligas mundiais."""
    all_matches = []
    
    print(f"Baixando odds para {len(leagues)} ligas globais. Isso pode levar alguns segundos...")
    for league in leagues:
        url = f'https://api.the-odds-api.com/v4/sports/{league}/odds'
        params = {
            'apiKey': API_KEY_ODDS,
            'regions': 'eu,uk', # 'eu' e 'uk' englobam gigantes que operam no Brasil (Bet365, Pinnacle, 1xBet, etc)
            'markets': 'btts',
            'oddsFormat': 'decimal',
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            all_matches.extend(response.json())
            
        time.sleep(0.2) # Pausa leve para não tomar bloqueio por spam na API de Odds
            
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
    
    # 1. PRÉ-FILTRO: Acha as maiores tendências globais sem gastar cota da RapidAPI
    for match in matches:
        try:
            commence_time = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
            if commence_time <= now:
                continue
                
            bookmaker = match['bookmakers'][0]
            market = bookmaker['markets'][0]
            
            odd_yes = next(item['price'] for item in market['outcomes'] if item['name'] == 'Yes')
            odd_no = next(item['price'] for item in market['outcomes'] if item['name'] == 'No')
            
            # Só armazena se o mercado já indica favoritismo (Odd menor que 1.80)
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
            
    # Ordena os jogos pelas menores odds (maior favoritismo segundo o mercado)
    pre_filtered_matches.sort(key=lambda x: min(x['odd_yes'], x['odd_no']))
    
    # 2. ANÁLISE PROFUNDA: Só checa estatísticas dos 10 melhores do mundo para poupar API
    analyzed_matches = []
    targets = pre_filtered_matches[:10]
    
    print(f"Pré-filtro concluiu. Checando histórico dos {len(targets)} jogos mais prováveis do mundo...")
    
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
            'match': f"{home_team} x {away_team}",
            'league': match['sport_title'],
            'start_time': item['commence_time'].strftime('%d/%m %H:%M'),
            'recommendation': recommendation,
            'probability': prob,
            'odd': odd,
            'bookmaker': item['bookmaker']
        })

    # Ordena pelo histórico e pega o Top 5
    analyzed_matches.sort(key=lambda x: x['probability'], reverse=True)
    return analyzed_matches[:5]

def send_telegram_message(message):
    """Envia o resultado para o Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN
