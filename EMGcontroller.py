import threading
import time
import urllib.request
import urllib.error
from bitalino import BITalino

from shared import Command



# Identificador do jogador
PLAYER_ID = "a"

# Endereço e porta do servidor onde o jogo está a correr
API_HOST = "127.0.0.1"
# API_HOST = "10.6.1.31"
API_PORT = 8000

# The macAddress variable on Windows can be "XX:XX:XX:XX:XX:XX" or "COMX"
# while on Mac OS can be "/dev/tty.BITalino-XX-XX-DevB" for devices ending with the last 4 digits of the MAC address or "/dev/tty.BITalino-DevB" for the remaining
macAddress = "00:00:00:00:00:00"

SENSOR_CHANNELS = [0, 1, 2]  # Canais do BITalino a utilizar
SAMPLING_RATE = 1000  # 10, 100, ou 1000 Hz
SAMPLE_SIZE = 100  # Quantos valores recolher antes de processar os dados



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



def process_data(device, sample_size):
    while True:
        # –––––––––– Adquirar os dados do BITalino
        data = device.read(sample_size)
        
        # –––––––––– Processar os dados do BITalino
        print(data)
        # TODO processar os dados aqui

        # –––––––––– Enviar comandos para o jogo com base nos dados processados
        # TODO enviar comandos para o jogo aqui
        # Exemplo de envio de comandos:
        # send_command(Command.UP)
        # send_command(Command.DOWN)
        # send_command(Command.SHOOT)
        # send_command(Command.BLOCK)



if __name__ == "__main__":

    # Ligar ao dispositivo BITalino através do endereço MAC definido acima
    device = BITalino(macAddress)

    # Mostrar a versão do firmware do BITalino (útil para verificar a ligação)
    print(device.version())

    # Iniciar a aquisição de dados nos canais e frequência de amostragem definidos
    device.start(SAMPLING_RATE, SENSOR_CHANNELS)

    # Recolher e processar os dados durante o tempo definido
    process_data(device, SAMPLE_SIZE)

    # Parar a aquisição de dados
    device.stop()

    # Fechar a ligação com o dispositivo
    device.close()