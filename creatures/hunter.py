from __future__ import annotations
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CREATURE_LIMITS
from creature import Perception, Action
from evolvable import EvolvableCreature


class Hunter(EvolvableCreature):
    gene_defs: dict[str, tuple[float, float]] = {
        "max_speed": CREATURE_LIMITS["max_speed"],
        "max_energy": CREATURE_LIMITS["max_energy"],
        "vision_radius": CREATURE_LIMITS["vision_radius"],
        "reproduce_ratio": (1.5, 3.0),
        "hunger_threshold": (0.1, 0.5),
        "chase_weak_threshold": (0.1, 0.8),
    }

    def __init__(self, x: float, y: float, genes: dict[str, float] | None = None):
        super().__init__(x, y, genes, "Hunter", (220, 50, 50))

    def apply_gene_attributes(self):
        super().apply_gene_attributes()
        self.reproduce_ratio = self.genes.get("reproduce_ratio", 2.0)
        self.hunger_threshold = self.genes.get("hunger_threshold", 0.25)
        self.chase_weak_threshold = self.genes.get("chase_weak_threshold", 0.4)

    def decide(self, perception: Perception) -> Action:
        energy_pct = perception.self_energy / perception.self_max_energy

        if energy_pct >= self.reproduce_ratio:
            if perception.nearby_creatures:
                weakest = min(
                    perception.nearby_creatures,
                    key=lambda c: c.energy_pct,
                )
                angle = math.atan2(
                    weakest.y - perception.self_y,
                    weakest.x - perception.self_x,
                )
                return Action(angle, self.max_speed * 0.3, reproduce=True)
            return Action(perception.self_angle, 0, reproduce=True)

        if energy_pct < self.hunger_threshold and perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed)

        if perception.nearby_creatures:
            smaller = [c for c in perception.nearby_creatures if c.size < perception.self_size]
            if smaller:
                weakest = min(
                    smaller,
                    key=lambda c: c.energy_pct,
                )
                nearest = min(
                    smaller,
                    key=lambda c: math.hypot(c.x - perception.self_x, c.y - perception.self_y),
                )

                target = weakest if weakest.energy_pct < self.chase_weak_threshold else nearest
                angle = math.atan2(
                    target.y - perception.self_y,
                    target.x - perception.self_x,
                )
                return Action(angle, self.max_speed, attack_target_id=target.creature_id)

        if perception.nearby_food:
            food = min(
                perception.nearby_food,
                key=lambda f: math.hypot(f.x - perception.self_x, f.y - perception.self_y),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * 0.6)

        angle = perception.self_angle + math.sin(perception.self_x * 0.01 + perception.self_y * 0.01) * 0.3
        return Action(angle, self.max_speed * 0.5)
