from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class Scavenger(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "Scavenger", (220, 220, 50))

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= 3.0:
            return Action(perception.self_angle, 0, reproduce=True)

        if perception.nearby_creatures:
            nearest = min(
                perception.nearby_creatures,
                key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
            )
            dist = math.hypot(
                nearest.x - perception.self_x,
                nearest.y - perception.self_y,
            )
            if dist < 80:
                flee_angle = math.atan2(
                    perception.self_y - nearest.y,
                    perception.self_x - nearest.x,
                )
                return Action(flee_angle, self.max_speed)

        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed)

        angle = perception.self_angle + math.cos(perception.self_x * 0.01) * 0.3
        return Action(angle, self.max_speed * 0.6)
