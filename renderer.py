from __future__ import annotations
import math
import pygame
from creature import Creature
from food import Food
from world import World
from config import (
    BG_COLOR,
    HUD_TEXT_COLOR,
    GAME_OVER_COLOR,
    FOOD_COLOR,
    DEFAULT_CREATURE_COLOR,
    GAME_OVER_TICK,
    SIDEBAR_WIDTH,
)


LEARNING_CREATURE_TYPE = "LearningCreature"
LEARNING_HIGHLIGHT_COLOR = (255, 230, 80)


class Renderer:
    def __init__(self, screen: pygame.Surface, sidebar_width: int = SIDEBAR_WIDTH):
        self.screen = screen
        self.sw = screen.get_width()
        self.sh = screen.get_height()
        self.sidebar_width = sidebar_width
        self.world_area_width = self.sw - sidebar_width
        self.font = pygame.font.SysFont(None, 22)
        self.big_font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 18)
        self.title_font = pygame.font.SysFont(None, 26)
        self.row_font = pygame.font.SysFont(None, 20)

    def render(self, world: World):
        self.screen.fill(BG_COLOR)
        self._draw_food(world.foods)
        self._draw_creatures(world.creatures)
        self._draw_hud(world)
        self._draw_sidebar(world)
        if world.game_over:
            self._draw_game_over(world)
        pygame.display.flip()

    def _draw_food(self, foods: list[Food]):
        for f in foods:
            if f.depleted:
                continue
            radius = max(2, int(f.size))
            pygame.draw.circle(self.screen, FOOD_COLOR, (int(f.x), int(f.y)), radius)

    def _draw_creatures(self, creatures: list[Creature]):
        for c in creatures:
            if not c.is_alive:
                continue
            radius = max(2, int(c.size))
            pygame.draw.circle(self.screen, c.color, (int(c.x), int(c.y)), radius)
            if c.creature_type == LEARNING_CREATURE_TYPE:
                self._draw_learning_highlight(c, radius)
            dir_len = radius * 0.7
            tip_x = int(c.x + math.cos(c.angle) * dir_len)
            tip_y = int(c.y + math.sin(c.angle) * dir_len)
            pygame.draw.line(self.screen, (255, 255, 255), (int(c.x), int(c.y)), (tip_x, tip_y), 1)

    def _draw_learning_highlight(self, creature: Creature, radius: int):
        center = (int(creature.x), int(creature.y))
        outer_radius = radius + 5
        pygame.draw.circle(self.screen, LEARNING_HIGHLIGHT_COLOR, center, outer_radius, 2)
        pygame.draw.circle(self.screen, (255, 255, 255), center, outer_radius + 3, 1)

        label = self.small_font.render("LC", True, LEARNING_HIGHLIGHT_COLOR)
        label_rect = label.get_rect(center=(center[0], center[1] - outer_radius - 8))
        self.screen.blit(label, label_rect)

    def _draw_hud(self, world: World):
        counts = world.alive_count_by_type()
        parts = [f"{t}: {n}" for t, n in sorted(counts.items())]
        alive_str = "  ".join(parts)
        total = world.alive_count

        lines = [
            f"Tick: {world.tick} / {GAME_OVER_TICK}    Alive: {total}",
            alive_str,
        ]

        bar_height = 18 * len(lines) + 12
        bar_surface = pygame.Surface((self.world_area_width, bar_height), pygame.SRCALPHA)
        bar_surface.fill((0, 0, 0, 160))
        self.screen.blit(bar_surface, (0, 0))

        for i, text in enumerate(lines):
            surf = self.font.render(text, True, HUD_TEXT_COLOR)
            self.screen.blit(surf, (10, 6 + i * 18))

    def _draw_sidebar(self, world: World):
        sx = self.world_area_width
        sw = self.sidebar_width
        pygame.draw.rect(self.screen, (18, 18, 28), pygame.Rect(sx, 0, sw, self.sh))
        pygame.draw.line(self.screen, (50, 50, 70), (sx, 0), (sx, self.sh), 2)

        y = 10

        # --- Section 1: Population ---
        title = self.title_font.render("POPULATION", True, (220, 220, 255))
        self.screen.blit(title, (sx + 10, y))
        y += 26
        pygame.draw.line(self.screen, (50, 50, 70), (sx + 8, y), (sx + sw - 8, y))
        y += 6

        pop = world.population_ranking()
        colors_by_type = self._colors_by_type(world.creatures)
        total = sum(n for _, n in pop)
        max_pop = max(n for _, n in pop) if pop else 1
        bar_max_w = sw - 100

        for ctype, count in pop:
            color = colors_by_type.get(ctype, DEFAULT_CREATURE_COLOR)
            pygame.draw.rect(self.screen, color, (sx + 10, y + 3, 10, 10))
            if ctype == LEARNING_CREATURE_TYPE:
                pygame.draw.rect(self.screen, LEARNING_HIGHLIGHT_COLOR, (sx + 8, y + 1, sw - 16, 24), 1)
                marker = self.small_font.render("LC", True, LEARNING_HIGHLIGHT_COLOR)
                self.screen.blit(marker, (sx + sw - 62, y + 1))
            label_color = LEARNING_HIGHLIGHT_COLOR if ctype == LEARNING_CREATURE_TYPE else (200, 200, 200)
            label = self.row_font.render(f"{ctype}", True, label_color)
            self.screen.blit(label, (sx + 24, y))
            num = self.row_font.render(f"{count}", True, (255, 255, 255))
            self.screen.blit(num, (sx + sw - 36, y))

            bar_w = int(bar_max_w * count / max_pop) if max_pop > 0 else 0
            pygame.draw.rect(self.screen, (*color[:3],), (sx + 24, y + 18, bar_w, 6))
            pygame.draw.rect(self.screen, (50, 50, 60), (sx + 24, y + 18, bar_max_w, 6), 1)
            y += 28

        y += 12
        pygame.draw.line(self.screen, (50, 50, 70), (sx + 8, y), (sx + sw - 8, y))
        y += 10

        # --- Section 2: Top Individuals ---
        title2 = self.title_font.render("TOP INDIVIDUALS", True, (220, 220, 255))
        self.screen.blit(title2, (sx + 10, y))
        y += 26

        header = self.small_font.render("#  Name            Energy   Size", True, (120, 120, 140))
        self.screen.blit(header, (sx + 8, y))
        y += 16

        top = world.top_creatures(limit=12)
        for rank, (name, ctype, energy, size, color) in enumerate(top, 1):
            pygame.draw.rect(self.screen, color, (sx + 6, y + 2, 4, 14))
            if ctype == LEARNING_CREATURE_TYPE:
                pygame.draw.rect(self.screen, LEARNING_HIGHLIGHT_COLOR, (sx + 4, y, sw - 12, 17), 1)

            display_name = name[:14]
            line = f"{rank:>2} {display_name:<14} {energy:>7.0f}  {size:>5.1f}"
            line_color = LEARNING_HIGHLIGHT_COLOR if ctype == LEARNING_CREATURE_TYPE else (200, 200, 200)
            surf = self.row_font.render(line, True, line_color)
            self.screen.blit(surf, (sx + 14, y))
            y += 17

        y += 16
        pygame.draw.line(self.screen, (50, 50, 70), (sx + 8, y), (sx + sw - 8, y))
        y += 10

        # --- Section 3: Controls ---
        ctrl_title = self.font.render("Controls", True, (140, 140, 160))
        self.screen.blit(ctrl_title, (sx + 10, y))
        y += 20
        for line in ["SPACE  Pause/Resume", "R      Restart", "ESC    Quit"]:
            surf = self.small_font.render(line, True, (120, 120, 140))
            self.screen.blit(surf, (sx + 10, y))
            y += 15

    def _draw_game_over(self, world: World):
        overlay = pygame.Surface((self.world_area_width, self.sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        if world.winner:
            winner_color = world.winner.color
            wtype = world.winner.creature_type
            text = f"{wtype} Wins!"
        else:
            winner_color = GAME_OVER_COLOR
            text = "No Winner"

        surf = self.big_font.render(text, True, winner_color)
        rect = surf.get_rect(center=(self.world_area_width // 2, self.sh // 2 - 30))
        self.screen.blit(surf, rect)

        pop = world.population_ranking()
        if pop:
            sub_text = "  ".join(f"{t}: {n}" for t, n in pop)
            sub = self.font.render(sub_text, True, HUD_TEXT_COLOR)
            sub_rect = sub.get_rect(center=(self.world_area_width // 2, self.sh // 2 + 15))
            self.screen.blit(sub, sub_rect)

        hint = self.font.render("Press R to restart", True, (140, 140, 160))
        hint_rect = hint.get_rect(center=(self.world_area_width // 2, self.sh // 2 + 45))
        self.screen.blit(hint, hint_rect)

    def _alive_color_by_type(self, world: World) -> dict[str, tuple[int, int, int]]:
        colors: dict[str, tuple[int, int, int]] = {}
        for creature in world.creatures:
            if creature.is_alive and creature.creature_type not in colors:
                colors[creature.creature_type] = creature.color
        return colors

    def _display_color(
        self,
        creature_type: str,
        colors_by_type: dict[str, tuple[int, int, int]],
    ) -> tuple[int, int, int]:
        return colors_by_type.get(
            creature_type,
            CREATURE_COLORS.get(creature_type, DEFAULT_CREATURE_COLOR),
        )
