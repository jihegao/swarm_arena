from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class CautiousGrazer(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "CautiousGrazer", (0, 200, 200))
        self.max_speed = 2.0
        self.max_energy = 100.0
        self.energy = 100.0
        self.vision_radius = 180.0

    def decide(self, perception: Perception) -> Action:
        bigger = [
            c for c in perception.nearby_creatures
            if c.size > perception.self_size
        ]

        if bigger:
            nearest_big = min(
                bigger,
                key=lambda c: math.hypot(
                    c.x - perception.self_x, c.y - perception.self_y
                ),
            )
            flee_angle = math.atan2(
                perception.self_y - nearest_big.y,
                perception.self_x - nearest_big.x,
            )
            return Action(flee_angle, self.max_speed)

        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(
                    f.x - perception.self_x, f.y - perception.self_y
                ),
            )
            angle = math.atan2(
                food.y - perception.self_y, food.x - perception.self_x
            )
            return Action(angle, self.max_speed)

        angle = perception.self_angle + math.sin(perception.self_x * 0.01) * 0.3
        return Action(angle, self.max_speed * 0.5)
