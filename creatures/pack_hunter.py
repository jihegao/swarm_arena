from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class PackHunter(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "PackHunter", (50, 50, 220))

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= 2.0 and len(perception.nearby_creatures) < 5:
            return Action(perception.self_angle, 0, reproduce=True)

        allies = [c for c in perception.nearby_creatures if c.creature_type == "PackHunter"]
        enemies = [c for c in perception.nearby_creatures if c.creature_type != "PackHunter" and c.size < perception.self_size]

        if len(allies) >= 2 and enemies:
            target = min(
                enemies,
                key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
            )
            angle = math.atan2(
                target.y - perception.self_y,
                target.x - perception.self_x,
            )
            return Action(angle, self.max_speed, attack_target_id=target.creature_id)

        if allies:
            ally = min(
                allies,
                key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
            )
            angle = math.atan2(
                ally.y - perception.self_y,
                ally.x - perception.self_x,
            )
            return Action(angle, self.max_speed * 0.8)

        if enemies:
            nearest = min(
                enemies,
                key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
            )
            dist = math.hypot(
                nearest.x - perception.self_x,
                nearest.y - perception.self_y,
            )
            if dist < 40:
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
            return Action(angle, self.max_speed * 0.6)

        angle = perception.self_angle + math.sin(perception.self_y * 0.015) * 0.25
        return Action(angle, self.max_speed * 0.5)
