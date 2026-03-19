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
    send_telegram("🚀 *מתחיל סריקה של כ-650 המניות הגדולות בארה\"ב...*")
    
    # משיכת רשימות מויקיפדיה - הדרך הכי אמינה שיש
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        tickers = list(set(sp500 + nasdaq + ['OXY']))
        tickers = [t.replace('.', '-') for t in tickers]
        print(f"Scanning {len(tickers)} tickers...")
    except Exception as e:
        print(f"Error: {e}")
        tickers = ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA', 'GOOGL', 'AMZN', 'META']

    matches = []
    # הורדה במקבצים של 50 לשיפור מהירות ויציבות
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
                diff = ((price - sma150) / sma150) * 100

                # תנאי המרחק (3%)
                if abs(diff) <= 3.0:
                    # בדיקת שווי שוק מעל 2 מיליארד
                    stock_info = yf.Ticker(ticker).info
                    if stock_info.get('marketCap', 0) >= 2_000_000_000:
                        icon = "🔽" if price < df['Close'].iloc[-2] else "↔️"
                        matches.append(f"{icon} *{ticker}* — ${price:.2f} ({abs(diff):.1f}% ל-SMA150)")
        except:
            continue

    if matches:
        header = f"🔍 *US Market Alert*\nנמצאו {len(matches)} מניות בטווח 3% מהממוצע:\n\n"
        send_telegram(header + "\n".join(matches))
    else:
        send_telegram("🔍 סריקה הושלמה. לא נמצאו מניות בטווח של 3% כרגע.")

if __name__ == "__main__":
    run_scanner()
