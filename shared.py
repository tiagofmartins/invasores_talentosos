"""
Este módulo é partilhado entre o jogo (game.py) e a API (api.py).
"""
import queue
from collections import defaultdict
from enum import Enum


# Lista de todos os comandos que um jogador pode enviar.
class Command(Enum):
    UP    = "up"
    DOWN  = "down"
    SHOOT = "shoot"
    BLOCK = "block"


# Dicionário de filas de comandos. Uma fila por jogador.
# A API coloca comandos na fila e o jogo lê os comandos a cada frame.
# O uso de defaultdict permite que a fila de um jogador seja criada
# automaticamente quando é acedida pela primeira vez.
player_commands: defaultdict = defaultdict(queue.Queue)
