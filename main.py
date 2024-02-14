import requests
import pandas as pd
import numpy as np
import time
import hmac
import hashlib


class SwingBreakoutBot:
    def __init__(self, api_key, api_secret, base_url, symbol, timeframe, equity, risk_per_trade):
        self.api_key = api_key
        self.api_secret = api_secret.encode()
        self.base_url = base_url
        self.symbol = symbol
        self.timeframe = timeframe
        self.equity = equity
        self.risk_per_trade = risk_per_trade
        self.headers = {'X-MBX-APIKEY': self.api_key}

    def fetch_market_data(self):
        endpoint = f'{self.base_url}/api/v3/klines'
        params = {
            'symbol': self.symbol,
            'interval': self.timeframe,
            'limit': 500
        }
        response = requests.get(endpoint, params=params)
        data = response.json()
        df = pd.DataFrame(data, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close Time',
                                         'Quote Asset Volume', 'Number of Trades', 'Taker Buy Base Asset Volume',
                                         'Taker Buy Quote Asset Volume', 'Ignore'])
        df['Close'] = df['Close'].astype(float)
        return df

    def identify_signals(self, df):
        short_window = 20
        long_window = 50
        df['short_mavg'] = df['Close'].rolling(window=short_window, min_periods=1).mean()
        df['long_mavg'] = df['Close'].rolling(window=long_window, min_periods=1).mean()
        df['signal'] = 0
        df['signal'][short_window:] = np.where(df['short_mavg'][short_window:] > df['long_mavg'][short_window:], 1, -1)
        df['positions'] = df['signal'].diff()
        return df[df['positions'] != 0]

    def calculate_position_size(self, entry_price, stop_loss_price):
        risk_per_share = abs(entry_price - stop_loss_price)
        shares_to_buy = (self.equity * self.risk_per_trade) / risk_per_share
        return shares_to_buy

    def generate_signature(self, params):
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def execute_trades(self, signals):
        for index, signal in signals.iterrows():
            entry_price = signal['Close']
            stop_loss_price = entry_price * 0.98
            position_size = self.calculate_position_size(entry_price, stop_loss_price)
            side = 'BUY' if signal['positions'] > 0 else 'SELL'
            params = {
                'symbol': self.symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': position_size,
                'timestamp': int(time.time() * 1000)
            }
            params['signature'] = self.generate_signature(params)
            response = requests.post(f"{self.base_url}/api/v3/order", params=params, headers=self.headers)
            data = response.json()
            print(f"Trade Response: {data}")

    def run(self):
        while True:
            try:
                df = self.fetch_market_data()
                if not df.empty:
                    signals = self.identify_signals(df)
                    if not signals.empty:
                        self.execute_trades(signals)
                else:
                    print("Keine neuen Daten verfügbar.")
            except Exception as e:
                print(f"Ein Fehler ist aufgetreten: {e}")

            # Waiting time between polling processes, e.g. 60 seconds
            time.sleep(20)


if __name__ == '__main__':
    API_KEY = 'my_api_key'
    API_SECRET = 'my_api_secret'
    BASE_URL = 'https://api.binance.com'
    SYMBOL = 'BTCUSDT'
    TIMEFRAME = '1h'
    EQUITY = 10000  # Example capital in USD
    RISK_PER_TRADE = 0.01  # 1% risk per trade

    bot = SwingBreakoutBot(API_KEY, API_SECRET, BASE_URL, SYMBOL, TIMEFRAME, EQUITY, RISK_PER_TRADE)
    bot.run()