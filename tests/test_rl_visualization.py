from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from train import parse_args, train_rl
from training.rl import RLConfig, RLTrainer


class RLVisualizationTests(unittest.TestCase):
    def test_rl_cli_visualizes_episodes_by_default(self):
        with patch.object(sys, "argv", ["train.py", "--method", "rl"]):
            args = parse_args()

        self.assertTrue(args.visualize_episodes)

    def test_rl_cli_can_disable_episode_visualization(self):
        with patch.object(sys, "argv", ["train.py", "--method", "rl", "--no-visualize-episodes"]):
            args = parse_args()

        self.assertFalse(args.visualize_episodes)

    def test_train_rl_passes_visual_options_to_config(self):
        captured_configs: list[RLConfig] = []

        class CapturingTrainer:
            def __init__(self, config):
                captured_configs.append(config)

            def train(self, progress_callback=None):
                return type(
                    "Result",
                    (),
                    {"q_table": {}, "best_fitness": 0.0, "history": []},
                )()

        with patch.object(sys, "argv", ["train.py", "--method", "rl", "--visual-fps", "37"]):
            args = parse_args()
        with patch("train.RLTrainer", CapturingTrainer), patch("train.save_rl_result"):
            train_rl(args)

        self.assertTrue(captured_configs[0].visualize_episodes)
        self.assertEqual(captured_configs[0].visual_fps, 37)

    def test_visualized_rl_episode_invokes_frame_renderer(self):
        rendered_ticks: list[int] = []

        def render_frame(world):
            rendered_ticks.append(world.tick)
            world.game_over = True
            return True

        config = RLConfig(
            episodes=1,
            width=80,
            height=80,
            visualize_episodes=True,
            visual_frame_callback=render_frame,
        )
        trainer = RLTrainer(config, opponent_classes=[])

        trainer.train()

        self.assertTrue(rendered_ticks)


if __name__ == "__main__":
    unittest.main()
