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

def get_all_tickers():
    # מושך רשימה של כל הטיקרים בארה"ב ממאגר מעודכן
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        response = requests.get(url)
        tickers = response.text.split('\n')
        return [t.strip() for t in tickers if t.strip() and t.isalpha() and len(t) < 6]
    except:
        return ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA'] # גיבוי במקרה של תקלה בקישור

def run_scanner():
    send_telegram("🔍 *סריקת כל השוק האמריקאי התחילה...* (שווי שוק >$2B, טווח 3%)")
    
    all_tickers = get_all_tickers()
    matches = []
    near_misses = [] # למעקב כדי שתראה שהבוט עובד
    
    batch_size = 100
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i+batch_size]
        try:
            # הורדה מהירה של נתונים לכל המקבץ
            data = yf.download(batch, period="200d", group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                df = data[ticker].dropna()
                if len(df) < 150: continue

                price = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                diff = ((price - sma150) / sma150) * 100

                # שלב 1: בדיקת מרחק (3%)
                if abs(diff) <= 3.0:
                    # שלב 2: רק למניות קרובות בודקים שווי שוק (חוסך זמן)
                    stock = yf.Ticker(ticker)
                    mkt_cap = stock.info.get('marketCap', 0)
                    
                    if mkt_cap >= 2_000_000_000:
                        icon = "🔽" if price < prev_close else "↔️"
                        price_5d_ago = df['Close'].iloc[-6]
                        status = "Pulled back" if price < price_5d_ago else "Holding"
                        
                        matches.append(f"{icon} *{ticker}* — ${price:.2f} ({abs(diff):.2f}% {'above' if diff > 0 else 'below'} SMA150)\n   ↳ {status} near SMA150")
                
                # שומר את אלו שקצת מחוץ לטווח רק לצורך הדיווח "הכי קרובות"
                elif abs(diff) <= 6.0:
                    near_misses.append((ticker, abs(diff)))

        except: continue

    # בניית ההודעה
    if matches:
        header = f"🔍 *US Market Scanner Alert*\n{len(matches)} stock(s) near SMA150 this hour:\n\n"
        footer = f"\n\nTotal in zone: {len(matches)} · Market cap >$2B · 0–3% SMA150"
        send_telegram(header + "\n".join(matches) + footer)
    else:
        near_misses.sort(key=lambda x: x[1])
        misses_text = "\n".join([f"• {t}: {d:.1f}% מרחק" for t, d in near_misses[:5]])
        send_telegram(f"🔍 *סריקה הושלמה:* לא נמצאו מניות בטווח 3%.\n\n*הכי קרובות שמצאתי (ללא פילטר שווי שוק):*\n{misses_text}")

if __name__ == "__main__":
    run_scanner()
