import yfinance as yf
import pandas as pd
import requests
import os

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    requests.get(url)

def run_scanner():
    # הודעה ראשונה כדי שתדע שהסריקה התחילה
    send_telegram("🚀 *סריקת שוק רחבה התחילה...* (זה יקח כ-12 דקות)")
    
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    tickers = requests.get(url).text.split('\n')
    all_tickers = [t.strip() for t in tickers if t.strip() and t.isalpha() and len(t) < 6]

    matches = []
    batch_size = 100
    
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i+batch_size]
        try:
            data = yf.download(batch, period="200d", group_by='ticker', threads=True, progress=False)
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                df = data[ticker].dropna()
                if len(df) < 150: continue

                current_price = df['Close'].iloc[-1]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                diff_pct = ((current_price - sma150) / sma150) * 100

                # פילטר 0-2%
                if abs(diff_pct) <= 2.0:
                    stock_info = yf.Ticker(ticker).info
                    if stock_info.get('marketCap', 0) >= 2_000_000_000:
                        icon = "🔽" if current_price < df['Close'].iloc[-2] else "↔️"
                        matches.append(f"{icon} *{ticker}* — ${current_price:.2f} ({abs(diff_pct):.2f}% near SMA150)")
        except: continue

    # הודעת סיכום סופית
    if matches:
        header = f"🔍 *US Market Scanner Alert*\n{len(matches)} stock(s) found:\n\n"
        send_telegram(header + "\n".join(matches))
    else:
        send_telegram("🔍 *סריקה הושלמה:* לא נמצאו מניות שעונות על התנאים בשעה זו.")

if __name__ == "__main__":
    run_scanner()
