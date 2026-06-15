from __future__ import annotations

import io
import math
import os
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout

from creature import Action, Creature, Perception
from food import Food
from renderer import Renderer
from world import World


class TypeNamedDifferently(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "DisplayName", (10, 120, 200))
        self.max_energy = 50.0
        self.energy = 120.0

    def decide(self, perception: Perception) -> Action:
        return Action(0.0, 0.0, reproduce=True)


class ExplodingCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "ExplodingCreature", (200, 30, 30))

    def decide(self, perception: Perception) -> Action:
        raise RuntimeError("student code exploded")


class BadActionCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "BadActionCreature", (30, 200, 30))

    def decide(self, perception: Perception):
        return Action(float("nan"), float("inf"))


class StationaryCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "StationaryCreature", (200, 200, 30))

    def decide(self, perception: Perception) -> Action:
        return Action(0.0, 0.0)


class CustomColorCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "CustomColorCreature", (12, 34, 56))

    def decide(self, perception: Perception) -> Action:
        return Action(0.0, 0.0)


class SimulationSafetyTests(unittest.TestCase):
    def setUp(self):
        Creature._next_id = 0
        Food._next_id = 0

    def test_reproduction_uses_runtime_creature_type_mapping(self):
        world = World(160, 160)
        world.spawn_creatures([TypeNamedDifferently])
        parent = world.creatures[0]
        world.creatures = [parent]
        parent.x = 80
        parent.y = 80
        parent.energy = 120.0

        world._resolve_reproduction([parent], [Action(0.0, 0.0, reproduce=True)])

        babies = [
            c for c in world.creatures
            if isinstance(c, TypeNamedDifferently) and c.id != parent.id
        ]
        self.assertEqual(1, len(babies))
        self.assertEqual("DisplayName", babies[0].creature_type)

    def test_decide_exception_falls_back_without_crashing_world(self):
        world = World(160, 160)
        world.spawn_creatures([ExplodingCreature])
        world.creatures = [world.creatures[0]]

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            world.update()

        self.assertEqual(1, len(world.creatures))
        self.assertTrue(math.isfinite(world.creatures[0].x))
        self.assertIn("ExplodingCreature", stdout.getvalue())
        self.assertIn("student code exploded", stdout.getvalue())

    def test_non_finite_action_is_sanitized(self):
        world = World(160, 160)
        world.spawn_creatures([BadActionCreature])
        creature = world.creatures[0]
        creature.x = 80
        creature.y = 80

        world.update()

        self.assertTrue(math.isfinite(creature.x))
        self.assertTrue(math.isfinite(creature.y))
        self.assertTrue(math.isfinite(creature.angle))
        self.assertEqual(0.0, creature.speed)

    def test_food_collision_matches_documented_distance_rule(self):
        world = World(160, 160)
        eater = StationaryCreature(80, 80)
        eater.energy = 40.0
        eater.max_energy = 100.0
        eater.clamp()
        food = Food(82, 80, amount=25.0)
        food.size = eater.size + 4.0
        world.creatures = [eater]
        world.foods = [food]
        world._rebuild_grids()

        world._check_food_collision()

        self.assertTrue(food.depleted)
        self.assertGreater(eater.energy, 40.0)

    def test_top_creatures_reports_actual_creature_color(self):
        world = World(160, 160)
        creature = StationaryCreature(80, 80)
        creature.creature_type = "CustomType"
        creature.color = (12, 34, 56)
        world.creatures = [creature]

        top = world.top_creatures(limit=1)

        self.assertEqual((12, 34, 56), top[0][4])

    def test_renderer_uses_alive_creature_color_for_sidebar_type(self):
        world = World(160, 160)
        creature = StationaryCreature(80, 80)
        creature.creature_type = "CustomType"
        creature.color = (12, 34, 56)
        world.creatures = [creature]
        renderer = Renderer.__new__(Renderer)

        colors = renderer._alive_color_by_type(world)

        self.assertEqual((12, 34, 56), renderer._display_color("CustomType", colors))

    def test_loader_warns_when_file_exports_multiple_creature_classes(self):
        from creature_loader import load_creatures

        source = """
        from creature import Creature, Action

        class One(Creature):
            def __init__(self, x, y):
                super().__init__(x, y, "One")
            def decide(self, perception):
                return Action(0, 0)

        class Two(Creature):
            def __init__(self, x, y):
                super().__init__(x, y, "Two")
            def decide(self, perception):
                return Action(0, 0)
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "many.py")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(textwrap.dedent(source))

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                classes = load_creatures(tmp)

        self.assertEqual(["One", "Two"], [cls.__name__ for cls in classes])
        self.assertIn("many.py exports multiple Creature classes", stdout.getvalue())

    def test_sidebar_leaderboard_uses_runtime_creature_color(self):
        import pygame

        pygame.font.init()
        world = World(160, 160)
        creature = CustomColorCreature(80, 80)
        world.creatures = [creature]

        screen = pygame.Surface((420, 260))
        renderer = Renderer(screen, sidebar_width=180)
        renderer._draw_sidebar(world)

        sx = renderer.world_area_width
        self.assertEqual(creature.color, screen.get_at((sx + 12, 48))[:3])
        self.assertEqual(creature.color, screen.get_at((sx + 7, 138))[:3])


if __name__ == "__main__":
    unittest.main()
