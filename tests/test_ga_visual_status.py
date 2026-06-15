from __future__ import annotations

import unittest

from config import SCREEN_HEIGHT, SCREEN_WIDTH, SIDEBAR_WIDTH
from creature import Action, Perception
from evolvable import EvolvableCreature
from trainer import evaluate_genes
from world import World
from training.visual_status import (
    PygameStatusWindow,
    ga_best_metric_from_progress,
    ga_status_from_progress,
)


class TinyEvolvableCreature(EvolvableCreature):
    gene_defs = {"speed": (0.5, 1.0)}

    def __init__(self, x: float, y: float, genes=None):
        super().__init__(x, y, genes=genes, creature_type="TinyEvolvableCreature", color=(80, 180, 220))

    def decide(self, perception: Perception) -> Action:
        return Action(0.0, 0.0)


class GAVisualStatusTests(unittest.TestCase):
    def test_generation_summary_shows_current_generation(self):
        status = ga_status_from_progress(
            "Generation 003/020: best=12.345 avg=6.789 overall_best=12.345"
        )

        self.assertIsNotNone(status)
        self.assertEqual("GA Training", status.title)
        self.assertEqual("Generation 3 / 20", status.primary)
        self.assertIn("best=12.345", status.secondary)
        self.assertEqual(
            "Best fitness: 12.345",
            ga_best_metric_from_progress("Generation 003/020: best=12.345 avg=6.789 overall_best=12.345"),
        )

    def test_evaluation_progress_shows_current_generation(self):
        status = ga_status_from_progress("Evaluating generation 004/020 (30 genomes)")

        self.assertIsNotNone(status)
        self.assertEqual("Generation 4 / 20", status.primary)
        self.assertEqual("Evaluating 30 genomes", status.secondary)

    def test_status_window_defaults_to_normal_simulation_size(self):
        self.assertEqual(SCREEN_WIDTH + SIDEBAR_WIDTH, PygameStatusWindow.default_width)
        self.assertEqual(SCREEN_HEIGHT, PygameStatusWindow.default_height)

    def test_status_window_identifies_target_creatures_for_highlight(self):
        world = World(80, 80)
        target = TinyEvolvableCreature(20, 20, genes={"speed": 0.75})
        other = TinyEvolvableCreature(40, 40, genes={"speed": 0.75})
        other.creature_type = "OtherCreature"
        world.creatures = [target, other]
        window = PygameStatusWindow.__new__(PygameStatusWindow)
        window.target_creature_type = "TinyEvolvableCreature"

        highlighted = window._target_creatures(world)

        self.assertEqual([target], highlighted)

    def test_evaluate_genes_sends_world_frames_to_visual_callback(self):
        seen_ticks: list[int] = []

        def render_frame(world):
            seen_ticks.append(world.tick)
            world.game_over = True
            return True

        evaluate_genes(
            TinyEvolvableCreature,
            {"speed": 0.75},
            opponent_classes=[],
            width=80,
            height=80,
            visual_frame_callback=render_frame,
        )

        self.assertTrue(seen_ticks)


if __name__ == "__main__":
    unittest.main()
