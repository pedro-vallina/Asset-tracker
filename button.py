from gpiozero import Button
from time import sleep

button = Button(21, pull_up=True)

x = 1
def next():
    global x
    print("botón pulsado. Cambiando signo...")
    x *= -1

button.when_pressed = next

while True: 
    print(x)
    sleep(0.2)
