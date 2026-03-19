import os
import requests
import yfinance as yf
import pandas as pd

# פונקציה לשליחת הודעה
def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}&parse_mode=Markdown"
    r = requests.get(url)
    print(f"Telegram response: {r.status_code}")

def run_scanner():
    print("--- Starting Scan Process ---")
    send_telegram("🚀 הבדיקה התחילה! הבוט מחובר לגיטהאב.")
    
    # רשימת בדיקה מצומצמת כדי שזה ירוץ מהר
    test_tickers = ['OXY', 'AAPL', 'NVDA']
    
    for ticker in test_tickers:
        print(f"Checking {ticker}...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period="200d")
        
        if len(hist) < 150:
            print(f"Not enough data for {ticker}")
            continue
            
        current_price = hist['Close'].iloc[-1]
        sma150 = hist['Close'].rolling(window=150).mean().iloc[-1]
        
        # תנאי רחב של 10% רק כדי לראות שמשהו קופץ
        if abs((current_price - sma150) / sma150) <= 0.10:
            send_telegram(f"✅ בדיקה: {ticker} נמצא בטווח הממוצע!")

    print("--- Scan Finished ---")

# חשוב מאוד: השורות האלו חייבות להיות צמודות לשמאל (בלי רווחים לפני)
if __name__ == "__main__":
    run_scanner()
