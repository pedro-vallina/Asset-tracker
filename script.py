import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from collections import defaultdict
import threading


intervalos = {"5m":300, "15m":900, "1h":3600, "1d":86400}
periods_intervals = {"15m":"1d", "1h":"1mo", "1d":"1y", "1wk":"10y", "1wk":"max"}
intervals = list(periods_intervals.keys())
ticker_list = ["BTC-USD", "^GSPC", "NLR", "PPFB.DE"]
data_log = pd.DataFrame()

def interval_to_timedelta(interval: str) -> pd.Timedelta:
    if interval.endswith("mo"):
        return pd.Timedelta(days=30*int(interval[:-2]))  # aproximación
    if interval.endswith("wk"):
        return pd.Timedelta(weeks=int(interval[:-2]))
    if interval.endswith("d"):
        return pd.Timedelta(days=int(interval[:-1]))
    if interval.endswith("h"):
        return pd.Timedelta(hours=int(interval[:-1]))
    if interval.endswith("m"):
        return pd.Timedelta(minutes=int(interval[:-1]))
    raise ValueError(f"Intervalo no soportado: {interval}")


class TimeSeriesData():
    def __init__(self, df, interval, asset):
        self.df = df
        self.interval = interval
        self.asset = asset
        self.delta = interval_to_timedelta(self.interval)
        self.index = df.index
    
    def needs_update(self):
        last = self.df.index[-1]
        if last.tzinfo is None: now = pd.Timestamp.now()
        else: now = pd.Timestamp.now(tz=last.tz)
        return now-last >= self.delta
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, columna):
        return self.df[columna]
    
    def __str__(self):
        return str(self.df)

    
class MarketData():
    def __init__(self):
        self.data = defaultdict(dict)
        self.lock = threading.Lock()
    
    def add(self, asset, interval, ts: TimeSeriesData):
        with self.lock:
            self.data[asset][interval] = ts
    
    
def descargar_datos(ticker: str, period: str, interval: str, log: bool=False):
    data = TimeSeriesData(df=yf.download(tickers=ticker, period=period, interval=interval), interval=interval, asset=ticker)

    if log: return logaritmicar(data)
    else: return data

def logaritmicar(data):
    data_log["Low"] = np.log(data["Low"])
    data_log["High"] = np.log(data["High"])
    return data_log

def plot(data):
    plt.figure()
    sns.set_theme(style="darkgrid")
    sns.axes_style("darkgrid")
    plt.plot(data["Low"])
    plt.plot(data["High"])
    plt.show(block=False)


index_asset = 0
index_period = -1
log=False
while True:
    interval = intervals[index_period]
    data = descargar_datos(ticker_list[index_asset], periods_intervals[interval], interval, log=log)
    plot(data)
    last = data.index[-1]

    if last.tzinfo is None:
        now = pd.Timestamp.now()
    else:
        now = pd.Timestamp.now(tz=last.tz)
    print(now-last)

    boton = input("(Next: n. Prev: p | Nigger: u. Schmaller: s | Loga: l) -> ")

    while True:
        if boton=='n': index_asset +=1
        elif boton=='p': index_asset -=1
        elif boton=='u': index_period +=1
        elif boton=='s': index_period -=1
        elif boton=='l':
            if log==False: log=True
            else: log=False
        break
        

    if index_asset in (-4, 4): index_asset=0
    if index_period in (-5, 5): index_period=0
