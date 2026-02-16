import requests
import time
import os
from datetime import datetime, timezone, timedelta

# --- LIMPEZA DE AMBIENTE ---
os.environ['http_proxy'] = ""
os.environ['https_proxy'] = ""

# --- CONFIGURAÇÕES ---
TELEGRAM_TOKEN = '8348998630:AAEtB2fQTIKkn2_w6dLmzfSMm7Jhl85vX9M'
CHAT_ID = '8073333859'
API_KEY_ODDS = '4fca1f2e9d9cca4384f0003c81aab497'

ODD_MINIMA_JOGO = 1.50
ODD_MAXIMA_JOGO = 2.25
JOGOS_POR_BILHETE = 3

def enviar_para_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload, timeout=20)
        if response.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Enviado ao Telegram.")
            return True
        print(f"❌ Erro Telegram: {response.status_code}")
        return False
    except:
        return False

def buscar_palpites_lucrativos():
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        dados = response.json()
        if not isinstance(dados, list):
            return "⚠️ Erro nos dados da API."

        agora_utc = datetime.now(timezone.utc)
        lista_de_valor = []

        for jogo in dados:
            try:
                # 1. Validar Horário
                dt_jogo = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt_jogo <= agora_utc:
                    continue

                # 2. Validar Estrutura de Odds
                bks = jogo.get('bookmakers', [])
                if not bks: continue
                mkts = bks[0].get('markets', [])
                if not mkts: continue
                outcomes = mkts[0].get('outcomes', [])
                if len(outcomes) < 2: continue

                # 3. Filtrar por Lucratividade
                opcoes = [o for o in outcomes if ODD_MINIMA_JOGO <= o['price'] <= ODD_MAXIMA_JOGO]
                if not opcoes:
                    continue
                
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
            except Exception:
                continue # Se der erro em UM jogo, pula para o próximo

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

# --- LOOP ---
if __name__ == "__main__":
    print("🚀 Robô Iniciado...")
    while True:
        resultado = buscar_palpites_lucrativos()
        if "💎" in resultado:
            enviar_para_telegram(resultado)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {resultado}")
        time.sleep(3600)