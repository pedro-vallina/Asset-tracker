import yfinance as yf
from gpiozero import Button
from collections import defaultdict
import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import traceback
import time

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

try:
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
except Exception as e:
    print(f"Aviso GPIO (no crítico si se ejecuta en PC de pruebas): {e}")


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
        if len(self.df) == 0:
            return True
        last = self.df.index[-1]
        if last.tzinfo is None:
            now = pd.Timestamp.now()
        else:
            now = pd.Timestamp.now(tz=last.tz)
        return now - last >= self.delta
    
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

    def __contains__(self, key):
        asset, interval = key
        return asset in self.data and interval in self.data[asset]

data_dict = MarketData()
    
def descargar_datos(ticker: str, period: str, interval: str) -> TimeSeriesData:
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if data is None or data.empty:
            print(f"Aviso: Datos vacíos descargados para {ticker} ({period}, {interval})")
            if (ticker, interval) in data_dict:
                return data_dict[ticker, interval]
            raise ValueError(f"No hay datos para {ticker}")
        
        # Aplanar MultiIndex de columnas si viene de versiones recientes de yfinance
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        ts = TimeSeriesData(data, interval=interval, ticker=ticker)
        data_dict.add(ts.ticker, ts.interval, ts)
        return ts
    except Exception as e:
        print(f"Error descargando datos para {ticker}: {e}")
        if (ticker, interval) in data_dict:
            print("Reutilizando datos previos en caché")
            return data_dict[ticker, interval]
        raise e

def logaritmicar(data: TimeSeriesData, interval:str, ticker: str) -> TimeSeriesData:
    data_log = pd.DataFrame()
    data_log["Low"] = np.log(data["Low"])
    data_log["High"] = np.log(data["High"])
    data_log = TimeSeriesData(data_log, interval=interval, ticker=ticker)
    return data_log


# Configuración de Ventana Tkinter
root = tk.Tk()
root.title("Asset Tracker")
# Sin cursor y fondo oscuro para la ventana raíz
root.config(cursor="none", bg="#121212")

# Atajos de teclado útiles si se conecta un teclado
root.bind("<Escape>", lambda e: root.destroy())
root.bind("n", lambda e: next())
root.bind("p", lambda e: prev())
root.bind("b", lambda e: bigger())
root.bind("s", lambda e: smaller())
root.bind("l", lambda e: loga())

# Pantalla completa real en Labwc / Wayland / X11
screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
root.overrideredirect(True)
root.geometry(f"{screen_w}x{screen_h}+0+0")

# Estilo Oscuro para Matplotlib (Dark Mode moderno tipo TradingView)
plt.style.use("dark_background")
dpi = 100
fig, ax = plt.subplots(figsize=(screen_w / dpi, screen_h / dpi), dpi=dpi)
fig.patch.set_facecolor("#121212")
ax.set_facecolor("#181a20")
ax.grid(True, linestyle="--", alpha=0.3, color="#444a57")

# Formato de ejes, ticks y espinas
ax.tick_params(colors="#a0aab8", labelsize=9)
for spine in ax.spines.values():
    spine.set_color("#2a2e39")

line_low, = ax.plot([], [], label="Low", color="#2979ff", linewidth=1.8)
line_high, = ax.plot([], [], label="High", color="#00e676", linewidth=1.8)

leg = ax.legend(loc="upper left", facecolor="#1e222d", edgecolor="#2a2e39")
for text in leg.get_texts():
    text.set_color("#e0e0e0")

fig.tight_layout(pad=1.5)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()

widget = canvas.get_tk_widget()
widget.configure(bg="#121212", highlightthickness=0)
widget.pack(fill="both", expand=True)


def plot_update(data, ticker, log):
    # Actualizamos los datos de las líneas
    line_low.set_data(data.index, data["Low"])
    line_high.set_data(data.index, data["High"])
    
    # Ajustar límites de ejes con un pequeño margen para que no toque los bordes
    ax.set_xlim(data.index.min(), data.index.max())
    y_min = float(np.nanmin(data["Low"]))
    y_max = float(np.nanmax(data["High"]))
    margin = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
    ax.set_ylim(y_min - margin, y_max + margin)

    if log:
        title = f"{ticker} (log)"
    else:
        title = ticker
    ax.set_title(title, color="#ffffff", fontsize=15, pad=10, fontweight="bold")

    canvas.draw_idle()
    root.update_idletasks()
    root.update()


index_asset = 0
index_period = -1
log = False

while True:
    try:
        period = periods[index_period]
        interval = intervals_dict[period]
        if index_asset != 1 and index_period in (4, -1): # Si no es spx y está en max, dejar interval en 1wk
            interval = "1wk"
        
        ticker = ticker_list[index_asset]

        try:
            data = data_dict[ticker, interval]
            if data.needs_update():
                data = descargar_datos(ticker, period, interval)
                print("Datos actualizados")
            else:
                print("Datos reciclados de data_dict")
        except (KeyError, Exception):
            data = descargar_datos(ticker, period, interval)
            print("Datos descargados nuevos")

        if log:
            data = logaritmicar(data, interval=interval, ticker=ticker)
        
        plot_update(data, ticker_list_plot[index_asset], log=log)

    except Exception as e:
        print(f"Error en ciclo de actualización: {e}")
        traceback.print_exc()

    root.update()
    root.after(50)
