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
    # קבלת רשימת מניות גדולה (S&P 500 + NASDAQ 100 כבסיס רחב)
    # הערה: סריקה של 8,000 מניות בבת אחת עלולה לקחת יותר מדי זמן בגיטהאב חינמי
    tickers = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    nasdaq_100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
    tickers = list(set(tickers + nasdaq_100 + ['OXY'])) # איחוד רשימות

    matches = []
    for ticker in tickers:
        try:
            symbol = ticker.replace('.', '-')
            stock = yf.Ticker(symbol)
            
            # בדיקת שווי שוק (Market Cap > 2 Billion)
            market_cap = stock.info.get('marketCap', 0)
            if market_cap < 2_000_000_000: continue

            hist = stock.history(period="200d")
            if len(hist) < 150: continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-5] # מחיר לפני שבוע
            sma150 = hist['Close'].rolling(window=150).mean().iloc[-1]

            # חישוב מרחק באחוזים מהממוצע
            diff_pct = (current_price - sma150) / sma150

            # לוגיקה: בטווח של פלוס/מינוס 2%
            if abs(diff_pct) <= 0.02:
                # אם המניה מתחת לממוצע (diff_pct < 0), היא חייבת להיות במגמה עולה
                if diff_pct < 0 and current_price <= prev_price:
                    continue
                
                status = "Above SMA150" if diff_pct > 0 else "Below SMA150 (Uptrend)"
                matches.append(f"🎯 *{ticker}*\nPrice: ${current_price:.2f}\nSMA 150: ${sma150:.2f}\nStatus: {status}")
        except: continue

    if matches:
        send_telegram("🚀 *Hourly Scan Matches (Market Cap > 2B):*\n\n" + "\n\n".join(matches))
