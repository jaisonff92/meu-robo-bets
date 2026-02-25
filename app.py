import requests
from datetime import datetime, timezone
import json

# ==========================================
# CONFIGURAÇÕES E CHAVES
# ==========================================
TELEGRAM_TOKEN = '8348998630:AAEtB2fQTIKkn2_w6dLmzfSMm7Jhl85vX9M'
CHAT_ID = '8073333859'
API_KEY_ODDS = '4fca1f2e9d9cca4384f0003c81aab497'

# Configurações da API de Odds
SPORT = 'soccer' # Pode especificar ligas como 'soccer_brazil_campeonato'
REGIONS = 'eu,us' # Regiões das casas de apostas
MARKETS = 'h2h' # Head to head (Vitória/Empate/Derrota)
ODDS_FORMAT = 'decimal'
DATE_FORMAT = 'iso'

def get_upcoming_matches():
    """Busca os próximos jogos de futebol e suas odds."""
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'
    params = {
        'apiKey': API_KEY_ODDS,
        'regions': REGIONS,
        'markets': MARKETS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Erro na API de Odds: {response.status_code} - {response.text}")
        return []
        
    return response.json()

def analyze_best_options(matches):
    """
    Filtra jogos ao vivo e seleciona as 10 melhores opções.
    A lógica de 'jogos passados' e 'melhor aposta' é simulada aqui.
    """
    valid_matches = []
    now = datetime.now(timezone.utc)
    
    for match in matches:
        # Pega o horário do jogo
        commence_time = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
        
        # 1. Filtro: O jogo NÃO PODE estar acontecendo agora (deve ser no futuro)
        # e deve ser do dia de hoje (limite de 24h)
        time_diff = (commence_time - now).total_seconds()
        if 0 < time_diff < 86400: # Jogo nas próximas 24 horas e não começou
            
            # Aqui você integraria sua lógica de jogos passados (ex: banco de dados local ou outra API).
            # Para este exemplo, vamos calcular a "força" da aposta baseada na diferença de odds.
            # Quanto maior a discrepância, mais claro é o favorito.
            
            try:
                # Pegando as odds da primeira casa de apostas disponível
                bookmaker = match['bookmakers'][0]
                outcomes = bookmaker['markets'][0]['outcomes']
                
                # Coletando odds do time A, B e empate (se houver)
                odds = [outcome['price'] for outcome in outcomes]
                min_odd = min(odds)
                max_odd = max(odds)
                
                # Score da aposta (Apenas um exemplo: buscamos favoritos claros)
                # Favoritos com odds entre 1.2 e 1.7 costumam ter alta probabilidade
                score = 0
                if 1.2 <= min_odd <= 1.7:
                    score = (max_odd - min_odd) # Discrepância alta = bom indicativo
                
                valid_matches.append({
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'start_time': commence_time.strftime('%H:%M (UTC)'),
                    'best_odd': min_odd,
                    'bookmaker': bookmaker['title'],
                    'score': score
                })
            except (IndexError, KeyError):
                continue

    # 2. Ordena as partidas pelo maior "score" (melhores oportunidades)
    valid_matches.sort(key=lambda x: x['score'], reverse=True)
    
    # 3. Retorna apenas as 10 melhores opções
    return valid_matches[:10]

def send_telegram_message(message):
    """Envia uma mensagem para o canal/chat do Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Mensagem enviada com sucesso ao Telegram!")
    else:
        print(f"Erro ao enviar mensagem: {response.text}")

def main():
    print("Buscando jogos...")
    matches = get_upcoming_matches()
    
    if not matches:
        print("Nenhum jogo encontrado ou erro na API.")
        return
        
    print("Analisando as melhores opções...")
    top_10 = analyze_best_options(matches)
    
    if not top_10:
        send_telegram_message("🤖 Não há boas oportunidades de apostas para os jogos restantes de hoje que não estejam ao vivo.")
        return

    # Montando a mensagem para o Telegram
    msg = "⚽ <b>TOP 10 MELHORES OPORTUNIDADES DO DIA</b> ⚽\n"
    msg += "<i>Jogos que ainda não começaram, baseados em análise de favoritismo:</i>\n\n"
    
    for i, match in enumerate(top_10, 1):
        msg += f"<b>{i}. {match['home_team']} vs {match['away_team']}</b>\n"
        msg += f"🕒 Horário: {match['start_time']}\n"
        msg += f"📈 Melhor Odd (Favorito): {match['best_odd']} ({match['bookmaker']})\n"
        msg += "➖" * 10 + "\n"
        
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
