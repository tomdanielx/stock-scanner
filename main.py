import yfinance as yf
import pandas as pd
import requests
import os

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    requests.get(url)

def run_scanner():
    send_telegram("🚀 *מתחיל סריקה יומית (טווח 2%, טופ 50)...*")
    
    # רשימה חסינה של ה-700 הגדולות (S&P 500 + Nasdaq 100)
    # אנחנו מביאים אותן ממקור Raw יציב יותר
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        sp500 = pd.read_csv(url)['Symbol'].tolist()
        # הוספת ידנית של מניות חשובות וטיקרים מה-Nasdaq
        extra = ['OXY', 'QQQ', 'TQQQ', 'MSFT', 'AAPL', 'NVDA', 'TSLA', 'GOOGL', 'AMZN', 'META']
        tickers = list(set(sp500 + extra))
        tickers = [t.replace('.', '-') for t in tickers]
    except:
        tickers = ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA', 'GOOGL', 'AMZN', 'META']

    print(f"Scanning {len(tickers)} stocks...")
    results = []
    
    # הורדה במקבצים
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
                
                # חישוב מרחק: $$Diff\% = \frac{|Price - SMA150|}{SMA150} \times 100$$
                diff_pct = (abs(price - sma150) / sma150) * 100

                if diff_pct <= 2.0:
                    # בדיקת שווי שוק מעל 2 מיליארד
                    info = yf.Ticker(ticker).info
                    if info.get('marketCap', 0) >= 2_000_000_000:
                        icon = "🔽" if price < df['Close'].iloc[-2] else "↔️"
                        results.append({
                            'ticker': ticker,
                            'price': price,
                            'diff': diff_pct,
                            'msg': f"{icon} *{ticker}* — ${price:.2f} ({diff_pct:.2f}% מהממוצע)"
                        })
        except: continue

    # מיון לפי הקרבה הכי גדולה לממוצע (הכי "מבטיח")
    results.sort(key=lambda x: x['diff'])
    top_50 = results[:50]

    if top_50:
        header = f"🏆 *Daily Top {len(top_50)} Opportunities*\nסרקתי {len(tickers)} מניות. אלו הכי קרובות ל-SMA150:\n\n"
        send_telegram(header + "\n".join([r['msg'] for r in top_50]))
    else:
        send_telegram(f"🔍 הסריקה הושלמה (סרקתי {len(tickers)} מניות).\nלא נמצאו חברות מעל $2B בטווח של 2%.")

if __name__ == "__main__":
    run_scanner()
