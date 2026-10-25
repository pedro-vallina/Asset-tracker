import yfinance as yf
from gpiozero import Button
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import traceback
import time

print("Librerías importadas")

# Diccionario de periodos e intervalos coherentes y escalonados
# 1d (15m): detalle de la jornada actual
# 5d (30m): semana de trading con detalle intradía
# 1mo (1h): último mes con barras de 1 hora
# 1y (1d): último año día a día
# 5y (1wk): últimos 5 años (ciclos de mercado)
# max (1mo): histórico completo desde el inicio del activo
intervals_dict = {
    '1d': '15m',
    '5d': '30m',
    '1mo': '1h',
    '1y': '1d',
    '5y': '1wk',
    'max': '1mo'
}

periods = list(intervals_dict.keys())

# Tickers optimizados:
# BTC-USD: Bitcoin
# ^GSPC: S&P 500
# NLR: VanEck Uranium and Nuclear Energy ETF (historial desde 2007)
# GLD: SPDR Gold Trust (oro con 22 años de histórico en Yahoo Finance, supera a PPFB.DE que solo tenía 5 años)
ticker_list = ["BTC-USD", "^GSPC", "NLR", "GLD"]
ticker_list_plot = ["Bitcoin (BTC-USD)", "S&P 500", "Uranium & Nuclear", "Gold (GLD)"]

state_changed = True
last_button_time = 0.0
DEBOUNCE_INTERVAL = 0.32  # 320 ms de cooldown para evitar dobles saltos o rebotes mecánicos

def debounce_check() -> bool:
    global last_button_time
    now = time.time()
    if now - last_button_time < DEBOUNCE_INTERVAL:
        return False
    last_button_time = now
    return True

def next():
    global index_asset, state_changed
    if not debounce_check():
        return
    index_asset = (index_asset + 1) % len(ticker_list)
    state_changed = True

def prev():
    global index_asset, state_changed
    if not debounce_check():
        return
    index_asset = (index_asset - 1) % len(ticker_list)
    state_changed = True

def bigger():
    global index_period, state_changed
    if not debounce_check():
        return
    index_period = (index_period + 1) % len(periods)
    state_changed = True

def smaller():
    global index_period, state_changed
    if not debounce_check():
        return
    index_period = (index_period - 1) % len(periods)
    state_changed = True

def loga():
    global log, state_changed
    if not debounce_check():
        return
    log = not log
    state_changed = True

# Inicialización de botones GPIO con filtro de rebote hardware/librería (bounce_time)
try:
    b_next = Button(26, bounce_time=0.25)
    b_next.when_pressed = next

    b_prev = Button(4, bounce_time=0.25)
    b_prev.when_pressed = prev

    b_bigger = Button(5, bounce_time=0.25)
    b_bigger.when_pressed = bigger

    b_smaller = Button(25, bounce_time=0.25)
    b_smaller.when_pressed = smaller

    b_loga = Button(23, bounce_time=0.25)
    b_loga.when_pressed = loga
except Exception as e:
    print(f"Aviso GPIO (no crítico si se ejecuta en PC de pruebas): {e}")


def interval_to_timedelta(interval: str) -> pd.Timedelta:
    if interval.endswith("mo"):
        return pd.Timedelta(days=30 * int(interval[:-2]))
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
            print(f"Aviso: Datos vacíos para {ticker} ({period}, {interval})")
            if (ticker, interval) in data_dict:
                return data_dict[ticker, interval]
            raise ValueError(f"No hay datos para {ticker}")
        
        # Aplanar MultiIndex si viene presente en versiones recientes de yfinance
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

def logaritmicar(data: TimeSeriesData, interval: str, ticker: str) -> TimeSeriesData:
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

# Ocultar cursor y moverlo fuera del área visible
try:
    root.event_generate('<Motion>', warp=True, x=screen_w - 1, y=screen_h - 1)
except Exception:
    pass

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

ax.set_title("Cargando...", color="#ffffff", fontsize=14, pad=10, fontweight="bold")
fig.tight_layout(pad=1.5)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()

widget = canvas.get_tk_widget()
widget.configure(bg="#121212", highlightthickness=0, cursor="none")
widget.pack(fill="both", expand=True)

# Renderizar inmediatamente la ventana inicial oscura
root.update()


def plot_update(data, ticker_title, period, interval, log):
    # Actualizamos los datos de las líneas
    line_low.set_data(data.index, data["Low"])
    line_high.set_data(data.index, data["High"])
    
    # Ajustar límites de ejes con margen para que no toque los bordes
    ax.set_xlim(data.index.min(), data.index.max())
    y_min = float(np.nanmin(data["Low"]))
    y_max = float(np.nanmax(data["High"]))
    margin = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
    ax.set_ylim(y_min - margin, y_max + margin)

    # Título descriptivo con activo, periodo y escala
    log_label = "  (LOG)" if log else ""
    title = f"{ticker_title}  •  {period.upper()} ({interval}){log_label}"
    ax.set_title(title, color="#ffffff", fontsize=14, pad=10, fontweight="bold")

    canvas.draw_idle()
    root.update_idletasks()
    root.update()


index_asset = 0
index_period = -1
log = False
state_changed = True
last_check_time = 0

while True:
    try:
        now = time.time()
        period = periods[index_period]
        interval = intervals_dict[period]
        ticker = ticker_list[index_asset]
        current_title = ticker_list_plot[index_asset]
        
        # Verificar si cambió el estado por botón o si toca refrescar datos en segundo plano
        check_interval = state_changed or ((now - last_check_time) > 15)
        
        if check_interval:
            last_check_time = now
            needs_redraw = False
            
            # Feedback visual inmediato si no está en caché y va a descargar
            if (ticker, interval) not in data_dict:
                ax.set_title(f"{current_title}  •  Descargando...", color="#ffd54f", fontsize=14, pad=10, fontweight="bold")
                canvas.draw_idle()
                root.update()
                data = descargar_datos(ticker, period, interval)
                needs_redraw = True
                print(f"[{ticker}] Datos descargados nuevos ({period}, {interval})")
            else:
                data = data_dict[ticker, interval]
                if data.needs_update():
                    data = descargar_datos(ticker, period, interval)
                    needs_redraw = True
                    print(f"[{ticker}] Datos actualizados ({period}, {interval})")
            
            if state_changed or needs_redraw:
                plot_data = data
                if log:
                    plot_data = logaritmicar(data, interval=interval, ticker=ticker)
                plot_update(plot_data, current_title, period, interval, log=log)
                state_changed = False

    except Exception as e:
        print(f"Error en ciclo de actualización: {e}")
        traceback.print_exc()

    root.update()
    time.sleep(0.04)
