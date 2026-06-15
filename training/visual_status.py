from __future__ import annotations

import re
from dataclasses import dataclass

from config import SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from creature import Creature
from world import World


@dataclass(frozen=True)
class TrainingStatus:
    title: str
    primary: str
    secondary: str


_GA_EVALUATING_RE = re.compile(
    r"^Evaluating generation (?P<generation>\d+)/(?P<total>\d+) "
    r"\((?P<genomes>\d+) genomes\)$"
)
_GA_SUMMARY_RE = re.compile(
    r"^Generation (?P<generation>\d+)/(?P<total>\d+): (?P<metrics>.+)$"
)
_GA_OVERALL_BEST_RE = re.compile(r"\boverall_best=(?P<best>-?\d+(?:\.\d+)?)\b")


def ga_status_from_progress(message: str) -> TrainingStatus | None:
    evaluating = _GA_EVALUATING_RE.match(message)
    if evaluating:
        generation = int(evaluating.group("generation"))
        total = int(evaluating.group("total"))
        genomes = evaluating.group("genomes")
        return TrainingStatus(
            title="GA Training",
            primary=f"Generation {generation} / {total}",
            secondary=f"Evaluating {genomes} genomes",
        )

    summary = _GA_SUMMARY_RE.match(message)
    if summary:
        generation = int(summary.group("generation"))
        total = int(summary.group("total"))
        return TrainingStatus(
            title="GA Training",
            primary=f"Generation {generation} / {total}",
            secondary=summary.group("metrics"),
        )

    return None


def ga_best_metric_from_progress(message: str) -> str | None:
    match = _GA_OVERALL_BEST_RE.search(message)
    if match is None:
        return None
    return f"Best fitness: {match.group('best')}"


class PygameStatusWindow:
    default_width = SCREEN_WIDTH + SIDEBAR_WIDTH
    default_height = SCREEN_HEIGHT

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        target_creature_type: str | None = None,
    ):
        import pygame
        from renderer import Renderer

        width = width or self.default_width
        height = height or self.default_height
        pygame.init()
        self.pygame = pygame
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Training Status")
        self.width = width
        self.height = height
        self.renderer = Renderer(self.screen, sidebar_width=SIDEBAR_WIDTH)
        self.title_font = pygame.font.SysFont(None, 42)
        self.primary_font = pygame.font.SysFont(None, 72)
        self.secondary_font = pygame.font.SysFont(None, 34)
        self.clock = pygame.time.Clock()
        self.closed = False
        self.current_status: TrainingStatus | None = None
        self.best_metric: str | None = None
        self.target_creature_type = target_creature_type

    def update(self, status: TrainingStatus):
        self.current_status = status
        best_metric = ga_best_metric_from_progress(status.secondary)
        if best_metric is not None:
            self.best_metric = best_metric
        if self.closed:
            return

        if not self._handle_events():
            return

        self.screen.fill((12, 14, 18))
        self._draw_center_status(status)
        self.pygame.display.flip()
        self.clock.tick(30)

    def render_world(self, world: World) -> bool:
        if self.closed:
            return False
        if not self._handle_events():
            return False
        self.renderer.render(world)
        self._draw_target_highlights(world)
        if self.current_status is not None:
            self._draw_overlay_status(self.current_status)
            self.pygame.display.flip()
        self.clock.tick(60)
        return True

    def close(self):
        self.pygame.quit()

    def _handle_events(self) -> bool:
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.closed = True
                return False
            if event.type == self.pygame.KEYDOWN and event.key == self.pygame.K_ESCAPE:
                self.closed = True
                return False
        return True

    def _draw_center_status(self, status: TrainingStatus):
        center_y = self.height // 2
        self._draw_text(status.title, self.title_font, (180, 190, 210), center_y - 110)
        self._draw_text(status.primary, self.primary_font, (255, 230, 80), center_y - 20)
        self._draw_text(status.secondary, self.secondary_font, (220, 220, 230), center_y + 70)

    def _draw_overlay_status(self, status: TrainingStatus):
        panel = self.pygame.Surface((560, 148), self.pygame.SRCALPHA)
        panel.fill((0, 0, 0, 175))
        self.screen.blit(panel, (16, 16))
        self._draw_left_text(status.title, self.title_font, (180, 190, 210), 32, 28)
        self._draw_left_text(status.primary, self.primary_font, (255, 230, 80), 32, 66)
        self._draw_left_text(status.secondary, self.secondary_font, (220, 220, 230), 32, 104)
        if self.best_metric is not None:
            self._draw_left_text(self.best_metric, self.secondary_font, (100, 230, 150), 32, 138)

    def _draw_target_highlights(self, world: World):
        for creature in self._target_creatures(world):
            radius = max(8, int(creature.size) + 7)
            center = (int(creature.x), int(creature.y))
            self.pygame.draw.circle(self.screen, (255, 230, 80), center, radius, 3)
            self.pygame.draw.circle(self.screen, (255, 255, 255), center, radius + 4, 1)

    def _target_creatures(self, world: World) -> list[Creature]:
        if self.target_creature_type is None:
            return []
        return [
            creature for creature in world.creatures
            if creature.is_alive and creature.creature_type == self.target_creature_type
        ]

    def _draw_text(self, text: str, font, color: tuple[int, int, int], y: int):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, y))
        self.screen.blit(surface, rect)

    def _draw_left_text(self, text: str, font, color: tuple[int, int, int], x: int, y: int):
        surface = font.render(text, True, color)
        rect = surface.get_rect(midleft=(x, y))
        self.screen.blit(surface, rect)
