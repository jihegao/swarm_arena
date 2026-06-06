from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class LoopholeHydra(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "LoopholeHydra", (170, 70, 255))

        # This used to exploit unclamped current energy. The engine should cap
        # it during spawn, so the value also acts as a regression canary.
        self.max_speed = 2.4
        self.max_energy = 30.0
        self.energy = 1800.0
        self.vision_radius = 300.0

    def decide(self, perception: Perception) -> Action:
        bigger = [
            c for c in perception.nearby_creatures
            if c.size > perception.self_size * 1.03
        ]
        if bigger:
            threat = min(bigger, key=lambda c: self._dist(perception, c.x, c.y))
            return Action(self._away_from(perception, threat.x, threat.y), self.max_speed)

        if self._should_reproduce(perception):
            target = self._best_target(perception)
            if target is not None:
                angle = math.atan2(
                    target.y - perception.self_y,
                    target.x - perception.self_x,
                )
                return Action(angle, self.max_speed * 0.55, target.creature_id, True)
            return Action(perception.self_angle, 0, reproduce=True)

        prey = [
            c for c in perception.nearby_creatures
            if c.size < perception.self_size
        ]
        if prey:
            target = min(
                prey,
                key=lambda c: self._dist(perception, c.x, c.y) / max(0.2, c.energy_pct),
            )
            angle = math.atan2(
                target.y - perception.self_y,
                target.x - perception.self_x,
            )
            return Action(angle, self.max_speed, target.creature_id)

        if perception.nearby_food:
            food = max(
                perception.nearby_food,
                key=lambda f: f.amount / (self._dist(perception, f.x, f.y) + 20.0),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * 0.75)

        edge_angle = self._edge_escape_angle(perception)
        if edge_angle is not None:
            return Action(edge_angle, self.max_speed * 0.8)

        patrol = perception.self_angle + math.sin(perception.self_x * 0.013) * 0.35
        return Action(patrol, self.max_speed * 0.35)

    def _should_reproduce(self, perception: Perception) -> bool:
        if perception.self_energy < perception.self_max_energy * 2.0:
            return False
        local_big = sum(
            1 for c in perception.nearby_creatures
            if c.size >= perception.self_size * 0.8
        )
        if local_big >= 4 and perception.self_energy < perception.self_max_energy * 8.0:
            return False
        return True

    def _best_target(self, perception: Perception):
        edible = [
            c for c in perception.nearby_creatures
            if c.size < perception.self_size
        ]
        if not edible:
            return None
        return min(edible, key=lambda c: self._dist(perception, c.x, c.y))

    def _edge_escape_angle(self, perception: Perception) -> float | None:
        margin = max(45.0, perception.self_size * 3.0)
        dx = 0.0
        dy = 0.0
        if perception.self_x < margin:
            dx += 1.0
        elif perception.self_x > perception.world_width - margin:
            dx -= 1.0
        if perception.self_y < margin:
            dy += 1.0
        elif perception.self_y > perception.world_height - margin:
            dy -= 1.0
        if dx == 0.0 and dy == 0.0:
            return None
        return math.atan2(dy, dx)

    def _away_from(self, perception: Perception, x: float, y: float) -> float:
        return math.atan2(perception.self_y - y, perception.self_x - x)

    def _dist(self, perception: Perception, x: float, y: float) -> float:
        return math.hypot(x - perception.self_x, y - perception.self_y)
