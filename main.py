import yfinance as yf
import pandas as pd
import requests
import os
import time

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    # פיצול הודעה אם היא ארוכה מדי
    if len(message) > 4000:
        for i in range(0, len(message), 4000):
            url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message[i:i+4000]}&parse_mode=Markdown"
            requests.get(url)
    else:
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
        requests.get(url)

def get_full_market_tickers():
    # מושך רשימה רחבה מאוד של מניות ארה"ב (NYSE + NASDAQ)
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url)
        tickers = [t.strip().replace('.', '-') for t in r.text.split('\n') if t.strip() and t.isalpha()]
        return list(set(tickers))
    except:
        return []

def run_scanner():
    send_telegram("🔍 *US Market Scanner Alert*\nהתחלתי סריקה מלאה של כל הבורסה האמריקאית...")
    
    tickers = get_full_market_tickers()
    if not tickers:
        send_telegram("❌ שגיאה במשיכת רשימת המניות.")
        return

    matches = []
    batch_size = 100
    
    # הורדה מרוכזת של מחירים (זה השלב המהיר)
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            data = yf.download(batch, period="200d", group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                df = data[ticker].dropna()
                if len(df) < 150: continue

                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2]
                price_5d_ago = df['Close'].iloc[-6]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                diff_pct = ((current_price - sma150) / sma150) * 100

                # שלב 1: פילטר 3%
                if abs(diff_pct) <= 3.0:
                    # שלב 2: בדיקת שווי שוק מעל 2 מיליארד (רק למתאימים)
                    stock = yf.Ticker(ticker)
                    mkt_cap = stock.info.get('marketCap', 0)
                    
                    if mkt_cap >= 2_000_000_000:
                        icon = "🔽" if current_price < prev_price else "↔️"
                        trend = "Pulled back" if current_price < price_5d_ago else "Holding"
                        
                        match_str = f"{icon} *{ticker}* — ${current_price:.2f} ({abs(diff_pct):.2f}% {'above' if diff_pct > 0 else 'below'} SMA150)\n"
                        match_str += f"   ↳ {trend} near SMA150"
                        matches.append(match_str)
        except:
            continue

    # בניית ההודעה הסופית בפורמט שביקשת
    if matches:
        header = f"🔍 *US Market Scanner Alert*\n{len(matches)} stock(s) near SMA150 this hour:\n\n"
        footer = f"\n\nTotal in zone: {len(matches)} · Market cap >$2B · 0–3% SMA150"
        send_telegram(header + "\n".join(matches) + footer)
    else:
        send_telegram("🔍 *US Market Scanner Alert*\nהסריקה הסתיימה. לא נמצאו מניות בטווח 3% מעל שווי שוק $2B.")

if __name__ == "__main__":
    run_scanner()
