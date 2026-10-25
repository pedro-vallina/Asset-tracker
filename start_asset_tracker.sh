#!/bin/bash
cd /home/pedro/Asset-tracker

# Esperar a que la interfaz gráfica y red inicien
sleep 3

export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export PYTHONUNBUFFERED=1

while true; do
    echo "[$(date)] Iniciando Asset Tracker..."
    .venv/bin/python script_nuevo.py
    EXIT_CODE=$?
    echo "[$(date)] Asset Tracker se detuvo (código $EXIT_CODE). Reiniciando en 5 segundos..."
    sleep 5
done
