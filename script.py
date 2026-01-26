import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from collections import defaultdict
import threading


intervalos = {"5m":300, "15m":900, "1h":3600, "1d":86400}
intervals_dict={'1d': '15m', '1mo': '4h', '1y': '1d', '10y': '1wk', 'max': '1mo'} 
#Relación god: 1:3600
# lista de periodos en orden para bucle
periods = list(intervals_dict.keys())
ticker_list = ["BTC-USD", "^GSPC", "NLR", "PPFB.DE"]
ticker_list_plot = ["BTC-USD", "S&P 500", "Uranium and Nuclear", "Physical Gold"]


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
    def __init__(self, df, interval, ticker):
        self.df = df
        self.interval = interval
        self.ticker = ticker
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
    
    def __getitem__(self, key):
        asset, interval = key
        return self.data[asset][interval]

data_dict = MarketData()
    
def descargar_datos(ticker: str, period: str, interval: str) -> TimeSeriesData:
    data = yf.download(tickers=ticker, period=period, interval=interval)
    data.columns = data.columns.get_level_values(0) #type: ignore
    data = TimeSeriesData(data, interval=interval, ticker=ticker)
    data_dict.add(data.ticker, data.interval, data)
    return data

def logaritmicar(data: TimeSeriesData, interval:str, ticker: str) -> TimeSeriesData:
    data_log = pd.DataFrame()
    data_log["Low"] = np.log(data["Low"])
    data_log["High"] = np.log(data["High"])
    data_log = TimeSeriesData(data_log, interval=interval, ticker=ticker)
    return data_log

# Activar modo interactivo
plt.ion()

# Inicializamos la figura y los ejes
sns.set_theme(style="darkgrid")
fig, ax = plt.subplots()
line_low, = ax.plot([], [], label="Low")
line_high, = ax.plot([], [], label="High")
ax.legend()

def plot_update(data, ticker, log):
    # Actualizamos los datos de las líneas
    line_low.set_data(data.index, data["Low"])
    line_high.set_data(data.index, data["High"])
    
    # Si cambia el tamaño del eje x, actualizarlo también
    ax.set_xlim(data.index.min(), data.index.max())
    ax.set_ylim(min(data["Low"]),
                float(max(data["High"])))
    if log==True:
        title = f"{ticker} (log)"
    else: title = ticker
    ax.set_title(title)
    fig.canvas.draw()
    fig.canvas.flush_events()


index_asset = 0
index_period = -1
log = False

while True:
    period = periods[index_period]
    interval = intervals_dict[period]
    if index_asset!=1 and index_period in (4, -1): #Si no es spx y está en max, dejar interval en 1wk
        interval = "1wk"
    
    ticker = ticker_list[index_asset]

    try:
        data = data_dict[ticker, interval]
        print("Datos reciclados de data_dict")
    except KeyError:
        data = descargar_datos(ticker, period, interval)
        print("Datos descargados nuevos")

    if log: data = logaritmicar(data, interval=interval, ticker=ticker)
    plot_update(data, ticker_list_plot[index_asset], log=log)
    last = data.index[-1]

    boton = input("(Next: n. Prev: p | Bigger: b. Smaller: s | Loga: l) -> ")

    if boton=='n': index_asset +=1
    elif boton=='p': index_asset -=1
    elif boton=='b': index_period +=1
    elif boton=='s': index_period -=1
    elif boton=='l':
        log = not log

    # Ajuste de índices para bucle circular
    index_asset %= len(ticker_list)
    index_period %= len(periods)