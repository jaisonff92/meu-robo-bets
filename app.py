def buscar_palpites():
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?apiKey={API_KEY_ODDS}&regions=eu&markets=totals&oddsFormat=decimal"
    try:
        res = requests.get(url, timeout=30).json()
        agora = datetime.now(timezone.utc)
        lista = []
        
        # Dicionário para tradução
        traducoes = {"Over": "Acima de", "Under": "Abaixo de"}

        for jogo in res:
            try:
                dt = datetime.strptime(jogo['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if dt <= agora: continue
                mkt = next((m for m in jogo['bookmakers'][0]['markets'] if m['key'] == 'totals'), None)
                if not mkt: continue
                
                escolha = min([o for o in mkt['outcomes'] if ODD_MINIMA <= o['price'] <= ODD_MAXIMA], key=lambda x: x['price'])
                
                m_home = obter_media_gols_real(jogo['home_team'])
                m_away = obter_media_gols_real(jogo['away_team'])
                media = (m_home + m_away) / 2
                
                # A lógica de comparação continua em inglês (como vem da API)
                if (escolha['name'].lower() == "over" and media >= escolha['point']) or (escolha['name'].lower() == "under" and media <= escolha['point']):
                    lista.append({
                        'l': jogo['sport_title'], 
                        't': f"{jogo['home_team']} x {jogo['away_team']}", 
                        'h': dt.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M"), 
                        'p': traducoes.get(escolha['name'], escolha['name']), # Aqui aplicamos a tradução
                        'pt': escolha['point'], 
                        'o': escolha['price'], 
                        'm
