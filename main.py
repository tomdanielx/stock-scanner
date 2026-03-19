import yfinance as yf
import pandas as pd
import requests
import os
import time

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    requests.get(url)

def run_scanner():
    send_telegram("🕵️ *הבוט נכנס למצב חשאי ומתחיל לסרוק את השוק...*")
    
    # רשימה ממוקדת יותר (S&P 500, Nasdaq 100, ומניות Russell 1000)
    # זה מכסה כמעט את כל החברות מעל 2 מיליארד דולר בלי להעמיס
    try:
        url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/indices/sp500.txt"
        sp500 = requests.get(url).text.split('\n')
        url_nasdaq = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/indices/nasdaq100.txt"
        nasdaq = requests.get(url_nasdaq).text.split('\n')
        tickers = list(set([t.strip() for t in sp500 + nasdaq if t.strip() and t.isalpha()]))
    except:
        tickers = ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA', 'GOOGL', 'AMZN', 'META']

    matches = []
    batch_size = 50 # מקבצים קטנים יותר כדי לא לעורר את ה-Rate Limit
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}...")
        
        try:
            data = yf.download(batch, period="200d", group_by='ticker', threads=False, progress=False)
            time.sleep(1) # "הפסקה קטנה" כדי לא להיחסם
            
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                df = data[ticker].dropna()
                if len(df) < 150: continue

                price = df['Close'].iloc[-1]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                diff = ((price - sma150) / sma150) * 100

                if abs(diff) <= 3.0:
                    # בדיקת שווי שוק
                    info = yf.Ticker(ticker).info
                    if info.get('marketCap', 0) >= 2_000_000_000:
                        icon = "🔽" if price < df['Close'].iloc[-2] else "↔️"
                        matches.append(f"{icon} *{ticker}* — ${price:.2f} ({abs(diff):.1f}% ל-SMA150)")
        except Exception as e:
            print(f"Error in batch: {e}")
            time.sleep(5) # אם נחסמנו, נחכה קצת יותר
            continue

    if matches:
        send_telegram(f"✅ *נמצאו {len(matches)} התאמות בשוק:*\n\n" + "\n".join(matches))
    else:
        send_telegram("🔍 *סריקה הושלמה:* לא נמצאו מניות בטווח 3% כרגע.")

if __name__ == "__main__":
    run_scanner()
