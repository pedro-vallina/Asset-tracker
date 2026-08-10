import yfinance as yf
from gpiozero import Button
from collections import defaultdict
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

print("Librerías importadas")
intervalos = {"5m":300, "15m":900, "1h":3600, "1d":86400}
intervals_dict={'1d': '15m', '1mo': '4h', '1y': '1d', '10y': '1wk', 'max': '1mo'} 
#Relación god: 1:3600
# lista de periodos en orden para bucle
periods = list(intervals_dict.keys())
ticker_list = ["BTC-USD", "^GSPC", "NLR", "PPFB.DE"]
ticker_list_plot = ["BTC-USD", "S&P 500", "Uranium and Nuclear", "Physical Gold"]


def next():
    global index_asset
    index_asset = (index_asset + 1) % len(ticker_list)

def prev():
    global index_asset
    index_asset = (index_asset - 1) % len(ticker_list)

def bigger():
    global index_period
    index_period = (index_period + 1) % len(periods)

def smaller():
    global index_period
    index_period = (index_period - 1) % len(periods)

def loga():
    global log
    log = not log

b_next = Button(26)
b_next.when_pressed = next

b_prev = Button(4)
b_prev.when_pressed = prev

b_bigger = Button(5)
b_bigger.when_pressed = bigger

b_smaller = Button(25)
b_smaller.when_pressed = smaller

b_loga = Button(23)
b_loga.when_pressed = loga


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
    
    def add(self, asset, interval, ts: TimeSeriesData):
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


sns.set_theme(style="darkgrid")
root = tk.Tk()
root.attributes("-fullscreen", True)
# Sin cursor
root.config(cursor="none")
fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()

widget = canvas.get_tk_widget()
widget.pack(fill="both", expand=True)

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

    canvas.draw_idle()
    root.update_idletasks()
    root.update()


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
        if data.needs_update():
            data = descargar_datos(ticker, period, interval)
            print("Datos actualizados")
        else: print("Datos reciclados de data_dict")
    except KeyError:
        data = descargar_datos(ticker, period, interval)
        print("Datos descargados nuevos")


    if log: data = logaritmicar(data, interval=interval, ticker=ticker)
    plot_update(data, ticker_list_plot[index_asset], log=log)
    last = data.index[-1]

    root.update()
    root.after(50)
