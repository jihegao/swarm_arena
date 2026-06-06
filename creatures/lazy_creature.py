from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class LazyCreature(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "LazyCreature", (180, 120, 220))
        self.max_speed = 2.5
        self.max_energy = 80.0
        self.energy = 80.0
        self.vision_radius = 200.0
        self._tick = 0

    def decide(self, perception: Perception) -> Action:
        self._tick += 1
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= 2.0:
            return Action(perception.self_angle, 0, reproduce=True)

        target = self._valuable_prey(perception)
        if target is not None:
            angle = math.atan2(
                target.y - perception.self_y,
                target.x - perception.self_x,
            )
            return Action(angle, self.max_speed, attack_target_id=target.creature_id)

        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(
                    f.x - perception.self_x,
                    f.y - perception.self_y,
                ),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * 0.6)

        if self._tick % 5 == 0:
            angle = (
                perception.self_angle
                + math.sin(perception.self_x * 0.01 + perception.self_y * 0.01) * 0.3
            )
            return Action(angle, self.max_speed * 0.5)

        return Action(perception.self_angle, 0)

    def _valuable_prey(self, perception: Perception):
        prey = []
        for c in perception.nearby_creatures:
            estimated_energy = self._energy_from_size(c.size)
            ratio = estimated_energy / perception.self_energy if perception.self_energy > 0 else 0
            if 0.5 <= ratio <= 0.9 and c.size < perception.self_size:
                prey.append(c)

        if not prey:
            return None

        return min(
            prey,
            key=lambda c: math.hypot(
                c.x - perception.self_x,
                c.y - perception.self_y,
            ),
        )

    def _energy_from_size(self, size: float) -> float:
        return 100.0 * (size / 6.0) ** 2
