import yfinance as yf
from datetime import timedelta, datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import pytz


intervalos = {"5m":300, "15m":900, "1h":3600, "1d":86400}
periods = {"5m":"2h", "15m":"1d", "1h":"1mo", "1d":"1y", "1mo":"10y", "3mo":"max"}
ticker_list = ["BTC-USD", "^GSPC", "NLR", "PPFB.DE"]
data_log = pd.DataFrame()

class TimeSeriesData():
    def __init__(self, df, interval):
        self.df = df
        self.interval = interval
        self.last_update = df.index[-1]

    def __len__(self):
        return len(self.df)
    
    def needs_update(self):
        pass
        #if self.last_update

def descargar_datos(ticker: str, period: str, interval: str, log: bool=False):
    #time.sleep(intervalos[interval])
    data = yf.download(ticker, period=period, interval=interval)
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


index = 0
while True:
    data = descargar_datos(ticker=ticker_list[index], period="1d", interval="15m", log=False)
    print(data)
    last = data.index[-1]

    if last.tzinfo is None:
        now = pd.Timestamp.now()
    else:
        now = pd.Timestamp.now(tz=last.tz)
    print(now-last)
    print(data.index)

    boton = input("(Next: n. Prev: p) -> ")

    if boton=='n': index +=1
    elif boton=='p': index -=1
    else: continue

    if index in (-4, 4): index=0
