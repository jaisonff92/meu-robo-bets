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
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

ODD_MINIMA = 1.25
ODD_MAXIMA = 3.50
JOGOS_POR_BILHETE = 1 

cache_estatisticas = {}

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Ativo")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def obter_media_gols_real(nome_time):
    agora = datetime.now()
    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        # 1. Busca ID do time
        res_team = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", 
                                headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not res_team.get('response'):
            return 0
            
        team_id = res_team['response'][0]['team']['id']
        
        # 2. Busca média dos últimos 5 jogos
        res_fixtures = requests.get("https://api-football-v1.p.rapidapi.com/v3/fixtures", 
                                   headers=headers, params={"team": team_id, "last": 5}, timeout=10).json()
        
        total_gols = 0
        jogos_contados = 0
        for f in res_fixtures.get('response', []):
            g_h = f['goals']['home'] if f['goals']['home'] is not None else 0
            g_a = f['goals']['away'] if f['goals']['away'] is not None else 0
            total_gols += (g_h + g_a)
            jogos_contados += 1
        
        media = total_gols / jogos_contados if jogos_contados > 0 else 0
        cache_estatisticas[nome_time] = {"media": media, "expira": agora + timedelta(hours=24)}
        return media
    except Exception as e:
        print(f"Erro na API Football: {e}")
        return 0

def enviar_msg(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=20)
    except:
        pass

def buscar_palpites():
    url_odds = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    try:
        res = requests.get(url_odds, timeout=30).json()
        agora_utc = datetime.now(timezone.utc)
        lista_analisada = []
        
        for jogo in res:
            try:
                dt = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt <= agora_utc: continue
                
                bks = jogo.get('bookmakers', [])
                if not bks: continue
                mkt = next((m for m in bks[0].get('markets', []) if m['key'] == 'totals'), None)
                if not mkt: continue
                
                escolha = min([o for o in mkt['outcomes'] if ODD_MINIMA <= o['price'] <= ODD_MAXIMA], key=lambda x: x['price'])
                
                m_home = obter_media_gols_real(jogo['home_team'])
                m_away = obter_media_gols_real(jogo['away_team'])
                media_geral = (m_home + m_away) / 2

                if (escolha['name'].lower() == "over" and media_geral >= escolha['point']) or \
                   (escolha['name'].lower() == "under" and media_geral <= escolha['point']):
                    lista_analisada.append({
                        'liga': jogo['sport_title'],
                        'times': f"{jogo['home_team']} x {jogo['away_team']}",
                        'hora': dt.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"),
                        'palpite': "Mais de" if escolha['name'].lower() == "over" else "Menos de",
                        'ponto': escolha['point'],
                        'odd': escolha['price'],
                        'media': round(media_geral, 2),
                        'ts': dt    if nome_time in cache_estatisticas:
        if agora < cache_estatisticas[nome_time]['expira']:
            return cache_estatisticas[nome_time]['media']

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
    }
    
    try:
        # Busca o ID do time
        res_team = requests.get("https://api-football-v1.p.rapidapi.com/v3/teams", 
                                headers=headers, params={"search": nome_time}, timeout=10).json()
        
        if not res_team.get('response'):
            return 0
            
        team_id = res_team['response'][0]['team']['id']
        
        # Busca histórico recente para média real
        res_fixtures = requests.get("https://api-football-v1.p.rapidapi.com/v3/fixtures", 
                                   headers=headers, params={"team": team_id, "last": 5}, timeout=10).json()
        
        total_gols = 0
        jogos_contados = 0
        for f in res_fixtures.get('response', []):
            g_h = f['goals']['home'] if f['goals']['home'] is not None else 0
            g_a = f['goals']['away'] if f['goals']['away'] is not None else 0
            total_gols += (g_h + g_a)
            jogos_contados += 1
        
        media = total_gols / jogos_contados if jogos_contados > 0 else 0
        
        # Salva no cache por 24h
        cache_estatisticas[nome_time] = {
            "media": media,
            "expira": agora + timedelta(hours=24)
        }
        return media
    except Exception as e:
        print(f"Erro na API de Stats: {e}")
        return 0

def enviar_msg(texto):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=20)
    except: pass

def buscar_palpites():
    # URL corrigida sem erros de f-string
    url_odds = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    try:
        res = requests.get(url_odds, timeout=30).json()
        agora_utc = datetime.now(timezone.utc)
        lista_analisada = []
        
        for jogo in res:
            try:
                dt = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt <= agora_utc: continue
                
                bks = jogo.get('bookmakers', [])
                if not bks: continue
                mkt = next((m for m in bks[0].get('markets', []) if m['key'] == 'totals'), None)
                if not mkt: continue
                
                outcomes = mkt.get('outcomes', [])
                viaveis = [o for o in outcomes if ODD_MINIMA <= o['price'] <= ODD_MAXIMA]
                if not viaveis: continue
                
                escolha = min(viaveis, key=lambda x: x['price'])
                ponto = escolha['point']
                
                # Validação Estatística
                m_home = obter_media_gols_real(jogo['home_team'])
                m_away = obter_media_gols_real(jogo['away_team'])
                media_geral = (m_home + m_away) / 2

                # Só aprova se a média de gols bater com o palpite (Over/Under)
                if escolha['name'].lower() == "over" and media_geral < ponto: continue
                if escolha['name'].lower() == "under" and media_geral > ponto: continue

                lista_analisada.append({
                    'liga': jogo['sport_title'],
                    'times': f"{jogo['home_team']} x {jogo['away_team']}",
                    'hora': dt.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"),
                    'palpite': "Mais de" if escolha['name'].lower() == "over" else "Menos de",
                    'ponto': ponto,
                    'odd': escolha['price'],
                    'media': round(media_geral, 2),
                    'ts': dt
                })
            except: continue

        if len(lista_analisada) < JOGOS_POR_BILHETE:
            return f"ℹ️ Buscando: {len(lista_analisada)} jogos validados no momento."

        lista_analisada.sort(key=lambda x: x['ts'])
        tops = lista_analisada[:JOGOS_POR_BILHETE]
        
        msg = "💎 *BILHETE ANALISADO (API-FOOTBALL)* 💎\n\n"
        total_odd = 1.0
        for s in tops:
            total_odd *= s['odd']
            msg += f"🏆 *{s['liga']}*\n⏰ {s['hora']} - {s['times']}\n🔥 *{s['palpite']} {s['ponto']} Gols* (@{s['odd']})\n📊 Media Real: {s['media']}\n\n"
        
        msg += f"--------------------------\n💰 *ODD TOTAL: {total_odd:.2f}*"
        return msg
    except Exception as e: return f"Erro no processamento: {e}"

if __name__ == "__main__":
    # Garante que o Render veja o bot como ativo
    threading.Thread(target=run_health_check, daemon=True).start()
    print("🚀 Robo Analisador com API-Football Ativado!")
    
    while True:
        resultado = buscar_palpites()
        if "💎" in resultado:
            enviar_msg(resultado)
            print("✅ Bilhete enviado ao Telegram!")
        else:
            print(resultado)
        
        # Pausa de 1 hora para respeitar limites da API
        time.sleep(3600)

