"""
Controlador para o jogo com 4 botões (UP, DOWN, SHOOT, BLOCK)
que enviam comandos à API do jogo.
Altera as constantes PLAYER_ID, API_HOST e API_PORT no início do script
para configurar qual o jogador a controlar e onde o servidor está a correr.
"""
import threading
import urllib.request
import urllib.error
import sys
import time
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Suprimir a mensagem de boas-vindas do pygame
import pygame

from shared import Command


# –––––––––––––––––––––––––––––– Configuração

# Identificador do jogador
PLAYER_ID = "a"

# Endereço e porta do servidor onde o jogo está a correr
API_HOST = "127.0.0.1"
# API_HOST = "10.6.1.31"
API_PORT = 8000


# –––––––––––––––––––––––––––––– Comunicação com o servidor

def send(cmd: Command):
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

    # Registar até quando o botão deve aparecer como pressionado
    press_until[cmd] = time.time() + 0.1


# –––––––––––––––––––––––––––––– Inicialização

pygame.init()
screen = pygame.display.set_mode((250, 250))
pygame.display.set_caption(f"Player {PLAYER_ID}")
font  = pygame.font.SysFont("helvetica", 14, bold=False)
clock = pygame.time.Clock()

# Posição e tamanho de cada botão no ecrã (x, y, largura, altura)
buttons = {
    Command.UP   : pygame.Rect(30,  30,  90, 90),
    Command.DOWN : pygame.Rect(30,  130, 90, 90),
    Command.SHOOT: pygame.Rect(130, 30,  90, 90),
    Command.BLOCK: pygame.Rect(130, 130, 90, 90),
}

# Guardar para cada botão o instante até ao qual deve ser desenhado como pressionado
press_until = {cmd: 0.0 for cmd in buttons}


# –––––––––––––––––––––––––––––– Ciclo principal

while True:
    # Limitar o número de frames por segundo
    clock.tick(30)

    # Processar eventos (rato, teclado, fechar janela)
    for event in pygame.event.get():

        # Fechar a janela com o botão [x] ou com a tecla Escape
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            pygame.quit()
            sys.exit()

        # Detetar o pressionar de teclas como alternativa aos botões
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                send(Command.UP)
            elif event.key == pygame.K_DOWN:
                send(Command.DOWN)
            elif event.key == pygame.K_SPACE:
                send(Command.SHOOT)
            elif event.key == pygame.K_b:
                send(Command.BLOCK)

        # Detetar o clique do rato dentro de algum botão
        if event.type == pygame.MOUSEBUTTONDOWN:
            for cmd, rect in buttons.items():
                if rect.collidepoint(event.pos):
                    send(cmd)
                    break

    # Desenhar interface
    screen.fill((255, 255, 255))
    now = time.time()
    for cmd, rect in buttons.items():
        pressed = now < press_until[cmd]
        bg = (200, 200, 200) if pressed else (220, 220, 220)
        pygame.draw.rect(screen, bg, rect, border_radius=10)
        text = font.render(cmd.name, True, (40, 40, 40))
        screen.blit(text, text.get_rect(center=rect.center))

    # Enviar desenhado da interface para o ecrã
    pygame.display.flip()
