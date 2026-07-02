import threading
import time
import urllib.request
import urllib.error
from bitalino import BITalino

from shared import Command


# –––––––––––––––––––––––––––––– Configuração

# Identificador do jogador
PLAYER_ID = "a"

# Endereço e porta do servidor onde o jogo está a correr
API_HOST = "127.0.0.1"
# API_HOST = "10.6.1.31"
API_PORT = 8000

# The macAddress variable on Windows can be "XX:XX:XX:XX:XX:XX" or "COMX"
# while on Mac OS can be "/dev/tty.BITalino-XX-XX-DevB" for devices ending with the last 4 digits of the MAC address or "/dev/tty.BITalino-DevB" for the remaining
macAddress = "00:00:00:00:00:00"

# This example will collect data for 5 sec.
running_time = 5

acqChannels = [0, 1, 2]
samplingRate = 1000
nSamples = 100


# –––––––––––––––––––––––––––––– Funções

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
            print(e)
            result = "failed"
        finally:
            print(f"{time.strftime('%H:%M:%S')} → {cmd.name} ({result})")
    threading.Thread(target=_post_request, daemon=True).start()


def process_data(data):
    # Process the acquired data here
    # For example, you can print the data or perform some analysis
    print("Processing data:", data)

    # send_command(Command.UP)  # Exemplo de envio do comando UP para o jogo
    # send_command(Command.DOWN)  # Exemplo de envio do comando DOWN para o jogo
    # send_command(Command.SHOOT)  # Exemplo de envio do comando SHOOT para o jogo
    # send_command(Command.BLOCK)  # Exemplo de envio do comando BLOCK para o jogo
    

def acquire_data(device, nSamples, running_time):
    start = time.time()
    end = time.time()
    while (end - start) < running_time:
        # Read samples
        dados = device.read(nSamples)
        print(dados)
        end = time.time()


# –––––––––––––––––––––––––––––– Programa principal

# Ligar ao dispositivo BITalino através do endereço MAC definido acima
device = BITalino(macAddress)

# Mostrar a versão do firmware do BITalino (útil para verificar a ligação)
print(device.version())

# Iniciar a aquisição de dados nos canais e frequência de amostragem definidos
device.start(samplingRate, acqChannels)

# Recolher e processar os dados durante o tempo definido
acquire_data(device, nSamples, running_time)

# Parar a aquisição de dados
device.stop()

# Fechar a ligação com o dispositivo
device.close()