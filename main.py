"""
Código para executar o jogo e a API.
"""
import threading
import uvicorn
from fastapi import FastAPI, HTTPException

from game import Game
from shared import Command, player_commands


def start_api(host: str, port: int, player_ids: list) -> None:
    # Criar a API que vai receber pedidos HTTP
    api = FastAPI(title="Space Invaders API")

    @api.post("/player/{player_id}/{command}")
    async def player_action(player_id: str, command: str):
        # Verificar se o ID do jogador é válido
        if player_id not in player_ids:
            raise HTTPException(400, "Invalid player ID")

        # Verificar se o comando existe no enum Command
        try:
            cmd = Command(command)
        except ValueError:
            raise HTTPException(400, "Invalid command")

        # Colocar o comando na fila de comandos do jogador correspondente
        player_commands[player_id].put(cmd)
        return {"ok": True}
    
    # Iniciar o servidor Uvicorn para servir a API
    uvicorn.run(api, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    # Iniciar o jogo
    game = Game()

    # Iniciar a API numa thread separada
    api_host = game.config.api_host
    api_port = game.config.api_port
    player_ids = [game.config.player_left, game.config.player_right]
    api_thread = threading.Thread(target=start_api, args=(api_host, api_port, player_ids), daemon=True)
    api_thread.start()

    # Iniciar o loop principal do jogo na thread principal
    game.run()
