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
    send_telegram("🚀 *סריקת שוק מלאה התחילה...*")
    
    # משיכת רשימת כל המניות (S&P 500 + NASDAQ כבסיס בטוח)
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        nasdaq = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        all_tickers = list(set(sp500 + nasdaq + ['OXY']))
        all_tickers = [t.replace('.', '-') for t in all_tickers]
    except Exception as e:
        print(f"Error fetching list: {e}")
        all_tickers = ['AAPL', 'MSFT', 'NVDA', 'OXY', 'TSLA'] # גיבוי

    matches = []
    print(f"Scanning {len(all_tickers)} tickers...")

    # הורדת נתונים במכה אחת לכל הרשימה (חוסך המון זמן)
    data = yf.download(all_tickers, period="200d", group_by='ticker', threads=True, progress=False)

    for ticker in all_tickers:
        try:
            df = data[ticker].dropna()
            if len(df) < 150: continue

            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            price_5d_ago = df['Close'].iloc[-6]
            sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
            
            diff_pct = ((current_price - sma150) / sma150) * 100

            # בדיקת טווח 0-2%
            if abs(diff_pct) <= 2.0:
                # סינון שווי שוק רק למניות שמעניינות אותנו (חוסך זמן יקר)
                stock_info = yf.Ticker(ticker).info
                if stock_info.get('marketCap', 0) >= 2_000_000_000:
                    
                    # בדיקת מגמה אם המניה מתחת לממוצע
                    if current_price < sma150 and current_price <= price_5d_ago:
                        continue
                    
                    icon = "🔽" if current_price < prev_price else "↔️"
                    trend = "Pulled back" if current_price < price_5d_ago else "Holding"
                    
                    matches.append(f"{icon} *{ticker}* — ${current_price:.2f} ({abs(diff_pct):.2f}% near SMA150)\n   ↳ {trend} near SMA150")
        except:
            continue

    # שליחת הסיכום
    if matches:
        header = f"🔍 *US Market Scanner Alert*\n{len(matches)} stock(s) near SMA150:\n\n"
        footer = f"\n\nTotal in zone: {len(matches)} · Market cap >$2B · 0–2% SMA150"
        send_telegram(header + "\n".join(matches) + footer)
    else:
        send_telegram("🔍 *סריקה הושלמה:* לא נמצאו מניות שעונות על התנאים בשעה זו.")

if __name__ == "__main__":
    run_scanner()
