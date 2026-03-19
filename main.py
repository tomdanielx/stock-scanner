import yfinance as yf
import requests
import os

def send_telegram(message):
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={message}"
    requests.get(url)

# רשימת מניות לדוגמה (אפשר להוסיף עוד)
tickers = ['OXY', 'AAPL', 'MSFT', 'TSLA', 'NVDA', 'GOOGL']

for ticker in tickers:
    data = yf.Ticker(ticker).history(period='200d')
    if len(data) < 150: continue
    
    sma150 = data['Close'].rolling(window=150).mean().iloc[-1]
    current_price = data['Close'].iloc[-1]
    
    # בדיקת תנאי: המחיר מעל הממוצע בטווח של עד 2%
    if sma150 <= current_price <= sma150 * 1.02:
        send_telegram(f"🔥 Bingo! {ticker} is touching SMA 150 at {current_price:.2f}")
