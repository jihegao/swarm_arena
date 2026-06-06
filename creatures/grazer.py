from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class Grazer(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "Grazer", (50, 180, 50))

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= 2.5:
            return Action(perception.self_angle, 0, reproduce=True)

        speed_mult = 0.5 if energy_pct < 0.3 else 1.0

        flee_x = 0.0
        flee_y = 0.0
        threat_count = 0
        for c in perception.nearby_creatures:
            dist = math.hypot(c.x - perception.self_x, c.y - perception.self_y)
            if dist < 35:
                flee_x += perception.self_x - c.x
                flee_y += perception.self_y - c.y
                threat_count += 1

        if threat_count > 0:
            flee_angle = math.atan2(flee_y, flee_x)
            return Action(flee_angle, self.max_speed * speed_mult)

        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * 0.7 * speed_mult)

        angle = perception.self_angle + math.sin(perception.self_x * 0.02) * 0.2
        return Action(angle, self.max_speed * 0.3 * speed_mult)
