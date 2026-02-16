import requests
import time
import os
from datetime import datetime, timezone, timedelta

# --- CONFIGURAÇÕES VIA VARIÁVEIS DE AMBIENTE ---
# No Render, vamos configurar essas 3 chaves nas opções do Worker
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
API_KEY_ODDS = os.getenv('API_KEY_ODDS')

ODD_MINIMA_JOGO = 1.50
ODD_MAXIMA_JOGO = 2.25
JOGOS_POR_BILHETE = 3

def enviar_para_telegram(mensagem):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Erro: Variáveis de ambiente do Telegram não configuradas.")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload, timeout=20)
        return response.status_code == 200
    except:
        return False

def buscar_palpites_lucrativos():
    if not API_KEY_ODDS:
        return "❌ Erro: API_KEY_ODDS não configurada."

    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        dados = response.json()
        
        if not isinstance(dados, list):
            return "⚠️ Erro na resposta da API."

        agora_utc = datetime.now(timezone.utc)
        lista_de_valor = []

        for jogo in dados:
            try:
                dt_jogo = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt_jogo <= agora_utc: continue

                bks = jogo.get('bookmakers', [])
                if not bks: continue
                mkts = bks[0].get('markets', [])
                if not mkts: continue
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
            except:
                continue

        if len(lista_de_valor) < JOGOS_POR_BILHETE:
            return "⚠️ Sem jogos no critério agora."

        lista_de_valor.sort(key=lambda x: x['timestamp'])
        selecionados = lista_de_valor[:JOGOS_POR_BILHETE]

        texto = "💎 *BILHETE DE ALTO VALOR* 💎\n"
        texto += "--------------------------------------\n"
        odd_final = 1.0
        for s in selecionados:
            odd_final *= s['odd']
            texto += f"🏆 *{s['liga']}*\n⏰ {s['horario']} - {s['times']}\n🔥 *{s['palpite']} {s['ponto']}* (@{s['odd']})\n\n"

        texto += "--------------------------------------\n"
        texto += f"💰 *ODD TOTAL: {odd_final:.2f}*"
        return texto

    except Exception as e:
        return f"❌ Erro de conexão: {e}"

if __name__ == "__main__":
    print("🚀 Robô em execução no Render...")
    while True:
        resultado = buscar_palpites_lucrativos()
        if "💎" in resultado:
            enviar_para_telegram(resultado)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Check executado.")
        time.sleep(3600)
