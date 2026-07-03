import threading
import time
import math

import numpy as np

import urllib.request
import urllib.error


from bitalino import BITalino

from visualization.buffer import SignalBuffer
from visualization.dashboard import run_dashboard
from shared import Command

# ------ configuration
buffer = SignalBuffer(
    [
        "Sensor 1",
        "Sensor 2",
        "Sensor 3",
    ]
)

# commands to send to the game
UP    = "up"
DOWN  = "down"
SHOOT = "shoot"
BLOCK = "block"

# Identificador do jogador
PLAYER_ID = "a"

# Endereço e porta do servidor onde o jogo está a correr.
API_HOST = "localhost"
# API_HOST = "10.6.1.31"
API_PORT = 8000


# The macAddress variable on Windows can be "XX:XX:XX:XX:XX:XX" or "COMX"
# while on Mac OS can be "/dev/tty.BITalino-XX-XX-DevB" for devices ending with the last 4 digits of the MAC address or "/dev/tty.BITalino-DevB" for the remaining
macAddress = "98:D3:41:FD:50:06"

# This example will collect data for 5 sec.
running_time = 600

acqChannels = [0, 1, 2]
samplingRate = 1000
nSamples = 100



# ----- funcoes

def send_command(cmd):
    """
    Envia o comando ao servidor do jogo via HTTP POST.
    O pedido é feito numa thread separada para não bloquear
    a janela enquanto se aguarda a resposta.
    """
    def _post_request():
        result = "ok"
        try:
            url = f"http://{API_HOST}:{API_PORT}/player/{PLAYER_ID}/{cmd.value}"
            request = urllib.request.Request(url, method="POST", data=b"")
            urllib.request.urlopen(request, timeout=2)
        except urllib.error.URLError as e:
            #print(e)
            result = "failed"
        finally:
            print(f"{time.strftime('%H:%M:%S')} → {cmd.name} ({result})")
    threading.Thread(target=_post_request, daemon=True).start()



def process_data(data):
    # Process the acquired data here
    # For example, you can print the data or perform some analysis
    #print("Processing data:", data)
    data = np.array(data, dtype=np.float32)

    # Visualização 
    for i in range(len(data)):
        data[i][-1] = abs((data[i][-1] - 512)/512.0)
        data[i][-2] = abs((data[i][-2] - 512)/512.0)
        data[i][-3] = abs((data[i][-3] - 512)/512.0)

        buffer.add_sample(
            "Sensor 1",
            data[i][-1]
            
        )

        buffer.add_sample(
            "Sensor 2",
            data[i][-2]
        )

        buffer.add_sample(
            "Sensor 3",
            data[i][-3]
        )

    # Logica
    sensor_1 = False
    sensor_2 = False
    sensor_3 = False
    if  data[i][-1] > 0.02:
        sensor_1 = True
    if  data[i][-2] > 0.02:
        sensor_2 = True
    if  data[i][-3] > 0.01:
        sensor_3 = True

    # Enviar comandos
    if sensor_1:
        send_command(Command.UP) 
        send_command(Command.SHOOT)
        print("up")
    if sensor_2:
        send_command(Command.DOWN)
        send_command(Command.SHOOT)
        print("down")
    if sensor_3:
        send_command(Command.SHOOT)
        print("shoot")
    if sensor_2 and sensor_1:
        send_command(Command.BLOCK)
        print("block")##
    #print(data)
    # send_command(UP)  # Example of sending a command to the game
    


def acquire_data(device, nSamples, running_time):

    start = time.time()
    end = time.time()
    while (end - start) < running_time:
        # Read samples
        dados = device.read(nSamples)

        
        process_data(dados)
        end = time.time()


# ------ main
# Connect to BITalino
device = BITalino(macAddress)

# Read BITalino version
print(device.version())

# Start Acquisition
device.start(samplingRate, acqChannels)




threading.Thread(
    target=acquire_data,
    args=(device, nSamples, running_time),
    daemon=True
).start()


run_dashboard(buffer)




# Stop acquisition
device.stop()

# Close connection
device.close()