"""
Código do jogo.
"""
import json
import math
import random
import time
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional, Tuple
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import yaml

from shared import Command, player_commands

CONFIG_PATH = Path(__file__).parent / "config.yaml"
IMAGES_PATH = Path(__file__).parent / "images"


class Bullet:
    def __init__(self, x: float, y: float, vx: float, owner: str):
        self.x = x
        self.y = y
        self.vx = vx
        self.owner = owner


class Invader:
    def __init__(self, x: float, y: float, vx: float, vy: float, row: int, osc_amp: float, osc_freq: float, osc_phase: float):
        self.x = x
        self.y = y
        self.base_y = y
        self.vx = vx
        self.vy = vy
        self.row = row
        self.dying = False
        self.death_time = 0.0
        self.osc_amp = osc_amp
        self.osc_freq = osc_freq
        self.osc_phase = osc_phase


class Ship:
    def __init__(self, player_id: str, x: float, y: float, facing_right: bool):
        self.player_id = player_id
        self.x = x
        self.y = y
        self.facing_right = facing_right
        self.score = 0
        self.consecutive_hits = 0
        self.special_available = False
        self.blocked_until = 0.0
        self.bullets: List[Bullet] = []
        self.last_shot_time = 0.0


class GamePhase(Enum):
    MENU = "menu"
    PLAYING = "playing"
    PAUSED = "paused"
    GAME_OVER = "game_over"


class Game:
    def __init__(self):
        config_data = yaml.safe_load(CONFIG_PATH.read_text())
        self.config = json.loads(json.dumps(config_data), object_hook=lambda d: SimpleNamespace(**d))
        cfg = self.config

        pygame.init()
        pygame.display.set_caption("Invasores Talentosos")

        w, h = cfg.screen_width, cfg.screen_height
        if cfg.fullscreen:
            self.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        else:
            w, h = w // cfg.dev_scale, h // cfg.dev_scale
            self.screen = pygame.display.set_mode((w, h))
        self.w, self.h = w, h
        self.clock = pygame.time.Clock()

        self.font_small = pygame.font.SysFont("helvetica", h // 26, bold=False)
        self.font_large = pygame.font.SysFont("helvetica", h // 16, bold=False)

        unit = w // 9
        self.area_a = pygame.Rect(0, 0, 4 * unit, h)
        self.area_stats = pygame.Rect(4 * unit, 0, unit, h)
        self.area_b = pygame.Rect(5 * unit, 0, w - 5 * unit,  h)

        self.ship_size = int(h * cfg.ship_size_percent / 100)
        self.inv_size = int(h * cfg.invader_size_percent / 100)
        self.bullet_radius = max(3, int(h * cfg.bullet_size_percent / 100))
        self.inv_speed_x = h * cfg.invader_horizontal_speed_percent / 100
        self.inv_speed_y = h * cfg.invader_vertical_speed_percent / 100
        self.bullet_speed = h * cfg.bullet_speed_percent / 100
        self.move_step = h * cfg.player_move_step_percent / 100
        self.osc_amp_max = h * cfg.invader_oscillation_amplitude_percent / 100

        self._ship_img_r = pygame.transform.smoothscale(pygame.image.load(IMAGES_PATH / "ship.png").convert_alpha(), (self.ship_size, self.ship_size))
        self._ship_img_l = pygame.transform.flip(self._ship_img_r, True, False)
        self._inv_img = pygame.transform.smoothscale(pygame.image.load(IMAGES_PATH / "invader.png").convert_alpha(), (self.inv_size, self.inv_size))
        self._cover_img = pygame.transform.smoothscale(pygame.image.load(IMAGES_PATH / "cover_ver.jpg").convert_alpha(), (self.area_stats.width, self.area_stats.height))

        margin = int(self.area_a.width * cfg.ship_margin_percent / 100)
        self._ship_a_x = self.area_a.x + margin + self.ship_size
        self._ship_b_x = self.area_b.right - margin - self.ship_size

        self.color_a = (0, 210, 255)
        self.color_b = (255, 120, 0)
        self.inv_colors = [(0, 230, 80), (230, 230, 0), (230, 80, 200), (160, 80, 255)]

        self.keys_a = {pygame.K_w: Command.UP, pygame.K_s: Command.DOWN, pygame.K_SPACE: Command.SHOOT, pygame.K_LSHIFT: Command.BLOCK}
        self.keys_b = {pygame.K_UP: Command.UP, pygame.K_DOWN: Command.DOWN, pygame.K_RETURN: Command.SHOOT, pygame.K_RSHIFT: Command.BLOCK}

        self.stars = [(random.randint(0, w), random.randint(0, h), random.uniform(0.5, 2.5)) for _ in range(cfg.star_count)]

        self.id_left = cfg.player_left
        self.id_right = cfg.player_right

        self.phase: GamePhase = GamePhase.MENU
        self.winner: Optional[str] = None
        self.ship_a: Optional[Ship] = None
        self.ship_b: Optional[Ship] = None
        self.invaders_a: List[Invader] = []
        self.invaders_b: List[Invader] = []
        self._spawn_timer = 0.0
        self._pause_start = 0.0

    def _new_game(self) -> None:
        self.ship_a = Ship(self.id_left,  self._ship_a_x, self.h / 2, True)
        self.ship_b = Ship(self.id_right, self._ship_b_x, self.h / 2, False)
        self.invaders_a = []
        self.invaders_b = []
        self.winner = None
        self.phase = GamePhase.PLAYING
        self._spawn_timer = time.time() + 3.0

    def _apply_command(self, ship: Ship, cmd: Command, now: float) -> None:
        opponent = self.ship_b if ship.player_id == self.id_left else self.ship_a
        if cmd == Command.UP and now > ship.blocked_until:
            ship.y = max(self.ship_size / 2, ship.y - self.move_step)
        elif cmd == Command.DOWN and now > ship.blocked_until:
            ship.y = min(self.h - self.ship_size / 2, ship.y + self.move_step)
        elif cmd == Command.SHOOT:
            if now - ship.last_shot_time >= self.config.min_shot_interval:
                ship.last_shot_time = now
                vx = self.bullet_speed if ship.facing_right else -self.bullet_speed
                ship.bullets.append(Bullet(ship.x, ship.y, vx, ship.player_id))
        elif cmd == Command.BLOCK and ship.special_available and opponent is not None:
            opponent.blocked_until = now + self.config.special_ability_duration
            ship.special_available = False
            ship.consecutive_hits  = 0

    def _update(self, dt: float, now: float) -> None:
        # Comandos da API
        for pid, q in player_commands.items():
            ship = self.ship_a if pid == self.id_left else self.ship_b
            if ship is None:
                continue
            while not q.empty():
                try:
                    self._apply_command(ship, q.get_nowait(), now)
                except Exception:
                    pass

        # Spawn de ondas de invaders simétricas nos dois lados
        if now >= self._spawn_timer:
            cfg = self.config
            wave = [
                (random.uniform(self.inv_size, self.h - self.inv_size),
                 random.uniform(-self.inv_speed_y * 0.4, self.inv_speed_y * 0.4),
                 random.uniform(0, self.osc_amp_max),
                 random.uniform(cfg.invader_oscillation_freq_min, cfg.invader_oscillation_freq_max),
                 random.uniform(0, math.pi * 2))
                for _ in range(cfg.invaders_per_wave)
            ]
            for inv_list, spawn_x, vx in (
                (self.invaders_a, float(self.area_stats.left), -self.inv_speed_x),
                (self.invaders_b, float(self.area_stats.right), self.inv_speed_x),
            ):
                for row, (y, vy, amp, freq, phase) in enumerate(wave):
                    inv_list.append(Invader(spawn_x, y, vx, vy, row, amp, freq, phase))
            self._spawn_timer = now + cfg.invader_spawn_interval

        # Atualizar invasores
        for inv_list, ship, wall_x, going_left in (
            (self.invaders_a, self.ship_a, 0, True),
            (self.invaders_b, self.ship_b, self.w, False),
        ):
            assert ship is not None
            half_size = self.inv_size / 2
            for inv in inv_list[:]:
                if inv.dying:
                    if now - inv.death_time > 0.4:
                        inv_list.remove(inv)
                    continue
                inv.x += inv.vx * dt
                inv.base_y += inv.vy * dt
                if inv.base_y < half_size:
                    inv.base_y = half_size
                    inv.vy = abs(inv.vy)
                elif inv.base_y > self.h - half_size:
                    inv.base_y = self.h - half_size
                    inv.vy = -abs(inv.vy)
                inv.y = inv.base_y + inv.osc_amp * math.sin(now * inv.osc_freq * math.pi * 2 + inv.osc_phase)

                hit_wall = inv.x < wall_x if going_left else inv.x > wall_x
                hit_ship = (abs(inv.x - ship.x) < (self.inv_size + self.ship_size) / 2 and
                            abs(inv.y - ship.y) < (self.inv_size + self.ship_size) / 2)
                if hit_wall or hit_ship:
                    inv_list.remove(inv)
                    self._player_hit(ship)

        # Atualizar projéteis
        for ship, inv_list, boundary_x, going_right in (
            (self.ship_a, self.invaders_a, self.area_stats.left, True),
            (self.ship_b, self.invaders_b, self.area_stats.right, False),
        ):
            assert ship is not None
            for bullet in ship.bullets[:]:
                bullet.x += bullet.vx * dt
                missed = bullet.x >= boundary_x if going_right else bullet.x <= boundary_x
                if missed:
                    ship.consecutive_hits = 0
                    ship.bullets.remove(bullet)
                    continue
                if bullet.x < 0 or bullet.x > self.w:
                    ship.bullets.remove(bullet)
                    continue
                for inv in inv_list:
                    if not inv.dying and (abs(bullet.x - inv.x) < self.inv_size * 0.6 and
                                          abs(bullet.y - inv.y) < self.inv_size * 0.6):
                        inv.dying = True
                        inv.death_time = now
                        ship.score += 1
                        ship.consecutive_hits += 1
                        if ship.consecutive_hits >= self.config.special_ability_hits_required:
                            ship.special_available = True
                        ship.bullets.remove(bullet)
                        break

    def _player_hit(self, ship: Ship) -> None:
        if self.phase == GamePhase.GAME_OVER:
            self.winner = None  # ambos atingidos no mesmo frame — empate
        else:
            self.phase  = GamePhase.GAME_OVER
            self.winner = self.id_right if ship == self.ship_a else self.id_left
    
    def _draw_background(self) -> None:
        pygame.draw.rect(self.screen, (0, 5, 30), self.area_a)
        pygame.draw.rect(self.screen, (30, 5, 0), self.area_b)
        for x, y, radius in self.stars:
            brightness = random.randint(128, 255)
            pygame.draw.circle(self.screen, (brightness, brightness, brightness), (x, y), int(radius))
        self.screen.blit(self._cover_img, (self.area_stats.left, 0))

    def _draw_ship(self, ship: Ship, now: float) -> None:
        img = self._ship_img_r if ship.facing_right else self._ship_img_l
        x, y = int(ship.x) - self.ship_size // 2, int(ship.y) - self.ship_size // 2
        self.screen.blit(img, (x, y))
        if now < ship.blocked_until:
            radius = self.ship_size + int(self.ship_size * 0.3 * abs(math.sin(now * 6)))
            shield = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(shield, (255, 60, 60, 90), (radius + 2, radius + 2), radius, 3)
            self.screen.blit(shield, (int(ship.x) - radius - 2, int(ship.y) - radius - 2))

    def _draw_invader(self, inv: Invader, now: float) -> None:
        if inv.dying:
            elapsed = now - inv.death_time
            if elapsed < 0.35:
                color = self.inv_colors[inv.row % len(self.inv_colors)]
                dist = elapsed * self.inv_size * 5
                radius = max(2, int(self.inv_size * 0.25 * (1 - elapsed / 0.35)))
                for i in range(8):
                    angle = i * math.pi / 4
                    pygame.draw.circle(self.screen, color, (int(inv.x + math.cos(angle) * dist), int(inv.y + math.sin(angle) * dist)), radius)
            return
        self.screen.blit(self._inv_img, (int(inv.x) - self.inv_size // 2, int(inv.y) - self.inv_size // 2))

    def _draw_bullet(self, bullet: Bullet, color: Tuple) -> None:
        bx, by = int(bullet.x), int(bullet.y)
        pygame.draw.circle(self.screen, color, (bx, by), max(2, self.bullet_radius))
        vx_sign = 1 if bullet.vx > 0 else -1
        pygame.draw.line(self.screen, (*color, 120),
                         (bx, by), (bx - vx_sign * self.bullet_radius * 6, by),
                         max(1, self.bullet_radius // 2))

    def _draw_stats(self) -> None:
        assert self.ship_a and self.ship_b
        pad = max(4, self.h // 80)
        left_x, right_x = self.area_stats.left, self.area_stats.right
        req = self.config.special_ability_hits_required

        def blit_left(surf: pygame.Surface, y: int) -> None:
            self.screen.blit(surf, (left_x + pad, y))

        def blit_right(surf: pygame.Surface, y: int) -> None:
            self.screen.blit(surf, (right_x - surf.get_width() - pad, y))

        # Nomes no topo
        blit_left(self.font_small.render(self.ship_a.player_id, True, self.color_a), pad)
        blit_right(self.font_small.render(self.ship_b.player_id, True, self.color_b), pad)

        # Score e strikes no fundo
        line_height = self.font_small.get_height() + 2
        bottom_y = self.h - pad - line_height * 2

        strike_a = "SPECIAL" if self.ship_a.special_available else f"{self.ship_a.consecutive_hits}/{req}"
        strike_b = "SPECIAL" if self.ship_b.special_available else f"{self.ship_b.consecutive_hits}/{req}"

        blit_left(self.font_small.render(str(self.ship_a.score), True, self.color_a), bottom_y)
        blit_right(self.font_small.render(str(self.ship_b.score), True, self.color_b), bottom_y)
        blit_left(self.font_small.render(strike_a, True, self.color_a), bottom_y + line_height)
        blit_right(self.font_small.render(strike_b, True, self.color_b), bottom_y + line_height)

    def _draw_playing(self, now: float) -> None:
        self._draw_background()
        for inv in self.invaders_a + self.invaders_b:
            self._draw_invader(inv, now)
        assert self.ship_a and self.ship_b
        for b in self.ship_a.bullets:
            self._draw_bullet(b, self.color_a)
        for b in self.ship_b.bullets:
            self._draw_bullet(b, self.color_b)
        self._draw_ship(self.ship_a, now)
        self._draw_ship(self.ship_b, now)
        self._draw_stats()
        if self.config.show_fps:
            fps_surf = self.font_small.render(str(round(self.clock.get_fps())), True, (255, 255, 255))
            self.screen.blit(fps_surf, (20, 20))

    def _draw_menu(self, now: float) -> None:
        self._draw_background()

        cy = self.h // 2
        name_a = self.font_large.render(self.id_left, True, self.color_a)
        name_b = self.font_large.render(self.id_right, True, self.color_b)
        self.screen.blit(name_a, (self.area_a.centerx - name_a.get_width() // 2, cy - name_a.get_height() // 2))
        self.screen.blit(name_b, (self.area_b.centerx - name_b.get_width() // 2, cy - name_b.get_height() // 2))

        pulse = int(155 + 100 * abs(math.sin(now * 1.5)))
        start = self.font_small.render("Press S to start", True, (pulse, pulse, pulse))
        self.screen.blit(start, (self.w // 2 - start.get_width() // 2, self.h * 0.5))

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        game_over_surf = self.font_large.render("GAME OVER", True, (255, 50, 50))
        self.screen.blit(game_over_surf, (self.w // 2 - game_over_surf.get_width() // 2, self.h // 2 - game_over_surf.get_height() // 2))

    def _draw_paused(self) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        pause_surf = self.font_large.render("PAUSE", True, (255, 255, 255))
        self.screen.blit(pause_surf, (self.w // 2 - pause_surf.get_width() // 2, self.h // 2 - pause_surf.get_height() // 2))
    
    def run(self) -> None:
        running = True
        while running:
            dt  = min(self.clock.tick(self.config.fps) / 1000.0, 0.05)
            now = time.time()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s and self.phase == GamePhase.MENU:
                        self._new_game()
                    elif event.key == pygame.K_r and self.phase != GamePhase.MENU:
                        self._new_game()
                    elif event.key == pygame.K_p:
                        if self.phase == GamePhase.PLAYING:
                            self.phase = GamePhase.PAUSED
                            self._pause_start = now
                        elif self.phase == GamePhase.PAUSED:
                            self._spawn_timer += now - self._pause_start
                            self.phase = GamePhase.PLAYING
                    elif self.phase == GamePhase.PLAYING:
                        if event.key in self.keys_a and self.ship_a:
                            self._apply_command(self.ship_a, self.keys_a[event.key], now)
                        if event.key in self.keys_b and self.ship_b:
                            self._apply_command(self.ship_b, self.keys_b[event.key], now)

            if self.phase == GamePhase.PLAYING:
                self._update(dt, now)

            self.screen.fill((0, 0, 0))
            if self.phase == GamePhase.MENU:
                self._draw_menu(now)
            elif self.phase == GamePhase.GAME_OVER:
                self._draw_playing(now)
                self._draw_game_over()
            elif self.phase == GamePhase.PAUSED:
                self._draw_playing(now)
                self._draw_paused()
            else:
                self._draw_playing(now)

            pygame.display.flip()

        pygame.quit()
