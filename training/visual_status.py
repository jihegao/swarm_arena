from __future__ import annotations

import re
from dataclasses import dataclass


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


def ga_status_from_progress(message: str) -> TrainingStatus | None:
    evaluating = _GA_EVALUATING_RE.match(message)
    if evaluating:
        generation = int(evaluating.group("generation"))
        total = int(evaluating.group("total"))
        genomes = evaluating.group("genomes")
        return TrainingStatus(
            title="GA Training",
            primary=f"第 {generation} 代 / 共 {total} 代",
            secondary=f"Evaluating {genomes} genomes",
        )

    summary = _GA_SUMMARY_RE.match(message)
    if summary:
        generation = int(summary.group("generation"))
        total = int(summary.group("total"))
        return TrainingStatus(
            title="GA Training",
            primary=f"第 {generation} 代 / 共 {total} 代",
            secondary=summary.group("metrics"),
        )

    return None


class PygameStatusWindow:
    def __init__(self, width: int = 520, height: int = 220):
        import pygame

        pygame.init()
        self.pygame = pygame
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Training Status")
        self.width = width
        self.height = height
        self.title_font = pygame.font.SysFont(None, 32)
        self.primary_font = pygame.font.SysFont(None, 42)
        self.secondary_font = pygame.font.SysFont(None, 24)
        self.clock = pygame.time.Clock()
        self.closed = False

    def update(self, status: TrainingStatus):
        if self.closed:
            return

        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                self.closed = True
                return
            if event.type == self.pygame.KEYDOWN and event.key == self.pygame.K_ESCAPE:
                self.closed = True
                return

        self.screen.fill((12, 14, 18))
        self._draw_text(status.title, self.title_font, (180, 190, 210), 26)
        self._draw_text(status.primary, self.primary_font, (255, 230, 80), 82)
        self._draw_text(status.secondary, self.secondary_font, (220, 220, 230), 145)
        self.pygame.display.flip()
        self.clock.tick(30)

    def close(self):
        self.pygame.quit()

    def _draw_text(self, text: str, font, color: tuple[int, int, int], y: int):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.width // 2, y))
        self.screen.blit(surface, rect)
