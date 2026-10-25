#!/bin/bash
cd /home/pedro/Asset-tracker

# Esperar a que la interfaz gráfica y red inicien
sleep 3

export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export PYTHONUNBUFFERED=1
export XCURSOR_THEME="blank"
export XCURSOR_SIZE="24"

# Iniciar unclutter en segundo plano para ocultar el ratón automáticamente
if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle 0.1 -root >/dev/null 2>&1 &
fi

while true; do
    echo "[$(date)] Iniciando Asset Tracker..."
    .venv/bin/python script_nuevo.py
    EXIT_CODE=$?
    echo "[$(date)] Asset Tracker se detuvo (código $EXIT_CODE). Reiniciando en 5 segundos..."
    sleep 5
done
