import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    requests.get(url)

def get_all_us_tickers():
    # מושך רשימה רחבה של מניות אמריקאיות ממקור ציבורי אמין
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        response = requests.get(url)
        tickers = response.text.split('\n')
        # ניקוי רשימה בסיסי
        return [t.strip() for t in tickers if t.strip() and t.isalpha() and len(t) < 6]
    except:
        # גיבוי אם הלינק לא עובד - רשימה מורחבת
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'OXY', 'BRK-B', 'V', 'JPM']

def run_scanner():
    print(f"Starting Full Market Scan at {datetime.now()}")
    all_tickers = get_all_us_tickers()
    
    matches = []
    # סריקה במקבצים של 100 כדי לא לקרוס
    batch_size = 100
    
    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i+batch_size]
        try:
            # הורדה מהירה של נתוני מחיר לכל המקבץ
            data = yf.download(batch, period="200d", interval="1d", group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                if ticker not in data or data[ticker].empty: continue
                
                df = data[ticker].dropna()
                if len(df) < 150: continue

                current_price = df['Close'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                price_5d_ago = df['Close'].iloc[-6]
                sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                
                # חישוב אחוז מרחק
                diff_pct = ((current_price - sma150) / sma150) * 100

                # פילטר 0-2% (מעל או מתחת)
                if abs(diff_pct) <= 2.0:
                    # בדיקת שווי שוק (רק למניות שעברו את סינון הממוצע, כדי לחסוך זמן)
                    stock_info = yf.Ticker(ticker).info
                    mkt_cap = stock_info.get('marketCap', 0)
                    
                    if mkt_cap >= 2_000_000_000:
                        # לוגיקה למניה מתחת לממוצע - חייבת להיות במגמה עולה ב-5 ימים האחרונים
                        if current_price < sma150 and current_price <= price_5d_ago:
                            continue
                        
                        icon = "🔽" if current_price < prev_close else "↔️"
                        move_desc = "Pulled back to SMA150" if current_price < price_5d_ago else "Holding near SMA150"
                        
                        match_str = f"{icon} *{ticker}* — ${current_price:.2f} ({abs(diff_pct):.2f}% {'above' if diff_pct > 0 else 'below'} SMA150)\n"
                        match_str += f"   ↳ {move_desc}"
                        matches.append(match_str)
        except:
            continue

    # בניית ההודעה בפורמט שביקשת
    if matches:
        count = len(matches)
        header = f"🔍 *US Market Scanner Alert*\n{count} stock(s) near SMA150 this hour:\n\n"
        footer = f"\n\nTotal in zone: {count} · Market cap >$2B · 0–2% SMA150"
        full_message = header + "\n".join(matches) + footer
        send_telegram(full_message)
    else:
        print("Scan complete. No matches found.")

if __name__ == "__main__":
    run_scanner()
