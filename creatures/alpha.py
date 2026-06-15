from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Creature, Perception, Action


class Alpha(Creature):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, "Alpha", (255, 0, 180))
        self.max_speed = 3.0
        self.max_energy = 90.0
        self.vision_radius = 180.0

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy
        my_size = perception.self_size

        prey = [c for c in perception.nearby_creatures if c.size < my_size]
        threats = [c for c in perception.nearby_creatures if c.size > my_size]
        same_size = [c for c in perception.nearby_creatures if c.size == my_size]

        nearest_threat_dist = min(
            (math.hypot(t.x - perception.self_x, t.y - perception.self_y) for t in threats),
            default=float('inf')
        )

        safe = nearest_threat_dist > 150

        if energy_pct >= 2.0 and safe:
            return Action(perception.self_angle, 0.0, reproduce=True)

        if energy_pct >= 2.0:
            smaller_safe = [c for c in prey if c.size < my_size * 0.7]
            if smaller_safe:
                target = min(smaller_safe, key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y))
                angle = math.atan2(target.y - perception.self_y, target.x - perception.self_x)
                return Action(angle, self.max_speed, attack_target_id=target.creature_id)
            return Action(perception.self_angle, 0.0, reproduce=True)

        if threats:
            nearest = min(threats, key=lambda t: math.hypot(t.x - perception.self_x, t.y - perception.self_y))
            dist = math.hypot(nearest.x - perception.self_x, nearest.y - perception.self_y)
            escape_dist = my_size * 5
            if dist < escape_dist:
                angle = math.atan2(perception.self_y - nearest.y, perception.self_x - nearest.x)
                return Action(angle, self.max_speed)

        if prey:
            small_prey = [c for c in prey if c.size < my_size * 0.85]
            if small_prey:
                target = min(small_prey, key=lambda c: c.energy_pct)
            else:
                target = min(prey, key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y))
            angle = math.atan2(target.y - perception.self_y, target.x - perception.self_x)
            return Action(angle, self.max_speed, attack_target_id=target.creature_id)

        if same_size and energy_pct > 1.5:
            target = min(same_size, key=lambda c: c.energy_pct)
            angle = math.atan2(target.y - perception.self_y, target.x - perception.self_x)
            return Action(angle, self.max_speed)

        if perception.nearby_food:
            food = min(perception.nearby_food, key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y))
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed)

        angle = perception.self_angle + math.sin(perception.self_x * 0.015 + perception.self_y * 0.015) * 0.3
        return Action(angle, self.max_speed * 0.5)
