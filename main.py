import yfinance as yf
import pandas as pd
import requests
import os
import time

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    if len(message) > 4000:
        for i in range(0, len(message), 4000):
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message[i:i+4000]}&parse_mode=Markdown"
            requests.get(url)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
        requests.get(url)

def run_scanner():
    send_telegram("📡 *מתחיל סריקה יומית ממוקדת...* (טווח 2%, טופ 50)")
    
    # משיכת רשימה רחבה (S&P 500 + Nasdaq 100) כדי להבטיח איכות
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        tickers = list(set(sp500 + nasdaq + ['OXY']))
        tickers = [t.replace('.', '-') for t in tickers]
    except:
        tickers = ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA']

    results = []
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            data = yf.download(batch, period="200d", group_by='ticker', threads=True, progress=False)
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                df = data[ticker].dropna()
                if len(df) < 150: continue

                price = df['Close'].iloc[-1]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                diff_pct = ((price - sma150) / sma150) * 100

                # פילטר 2 אחוזים
                if abs(diff_pct) <= 2.0:
                    # בדיקת שווי שוק מעל 2 מיליארד
                    info = yf.Ticker(ticker).info
                    if info.get('marketCap', 0) >= 2_000_000_000:
                        icon = "🔽" if price < df['Close'].iloc[-2] else "↔️"
                        results.append({
                            'ticker': ticker,
                            'price': price,
                            'diff': abs(diff_pct),
                            'msg': f"{icon} *{ticker}* — ${price:.2f} ({abs(diff_pct):.2f}% מהממוצע)"
                        })
        except: continue

    # מיון לפי המרחק הקטן ביותר (הכי קרוב ל-SMA150 = הכי מבטיח)
    results.sort(key=lambda x: x['diff'])
    top_50 = results[:50]

    if top_50:
        header = f"🏆 *Daily Top 50 Opportunities*\n(Sorted by Proximity to SMA150)\n\n"
        send_telegram(header + "\n".join([r['msg'] for r in top_50]))
    else:
        send_telegram("🔍 סריקה הושלמה. לא נמצאו מניות בטווח 2% כרגע.")

if __name__ == "__main__":
    run_scanner()
