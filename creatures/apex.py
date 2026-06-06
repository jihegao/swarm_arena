from __future__ import annotations
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from creature import Perception, Action
from evolvable import EvolvableCreature


class Apex(EvolvableCreature):
    """Adaptive predator: flee threats, hunt prey, reproduce when safe, forage efficiently."""

    gene_defs = {
        "max_speed": (2.0, 3.4),
        "max_energy": (50.0, 110.0),
        "vision_radius": (120.0, 260.0),
        "threat_size_ratio": (1.0, 1.3),
        "flee_size_multiplier": (7.0, 14.0),
        "reproduce_ratio": (1.8, 2.8),
        "danger_size_ratio": (0.65, 1.0),
        "close_chase_distance": (20.0, 50.0),
        "food_speed_ratio": (0.55, 1.0),
        "wander_turn": (0.15, 0.55),
    }

    default_genes = {
        "max_speed": 2.8,
        "max_energy": 70.0,
        "vision_radius": 200.0,
        "threat_size_ratio": 1.05,
        "flee_size_multiplier": 10.0,
        "reproduce_ratio": 2.0,
        "danger_size_ratio": 0.8,
        "close_chase_distance": 30.0,
        "food_speed_ratio": 0.8,
        "wander_turn": 0.35,
    }

    def __init__(self, x: float, y: float, genes=None):
        super().__init__(
            x,
            y,
            genes=genes or self.default_genes,
            creature_type="Apex",
            color=(255, 100, 50),
        )

    def decide(self, perception: Perception) -> Action:
        # ---- Priority 1: Flee bigger threats ----
        bigger = [
            c for c in perception.nearby_creatures
            if c.size > perception.self_size * self.genes["threat_size_ratio"]
        ]
        if bigger:
            nearest_threat = min(bigger, key=lambda c: self._dist(perception, c.x, c.y))
            threat_dist = self._dist(perception, nearest_threat.x, nearest_threat.y)
            # Flee zone proportional to threat proximity
            flee_zone = max(60.0, perception.self_size * self.genes["flee_size_multiplier"])
            if threat_dist < flee_zone:
                flee_angle = self._away_from(perception, nearest_threat.x, nearest_threat.y)
                return Action(flee_angle, self.max_speed)

        # ---- Priority 2: Reproduce when safe ----
        energy_ratio = perception.self_energy / perception.self_max_energy
        if energy_ratio >= self.genes["reproduce_ratio"]:
            # Only reproduce if locally safe (few threats nearby)
            local_danger = sum(
                1 for c in perception.nearby_creatures
                if c.size >= perception.self_size * self.genes["danger_size_ratio"]
            )
            if local_danger <= 2:
                # Move toward best target while reproducing (don't waste the frame)
                target = self._best_nearby_target(perception)
                if target is not None:
                    angle = math.atan2(target[1] - perception.self_y, target[0] - perception.self_x)
                    return Action(angle, self.max_speed * 0.5, reproduce=True)
                return Action(perception.self_angle, 0, reproduce=True)

        # ---- Priority 3: Hunt smaller prey ----
        prey = [
            c for c in perception.nearby_creatures
            if c.size < perception.self_size
        ]
        if prey:
            # Score prey by energy payoff vs chase distance
            best_prey = min(
                prey,
                key=lambda c: self._dist(perception, c.x, c.y) / max(0.3, c.energy_pct),
            )
            angle = math.atan2(best_prey.y - perception.self_y, best_prey.x - perception.self_x)
            dist = self._dist(perception, best_prey.x, best_prey.y)
            # Slow down when close to avoid overshooting
            speed = self.max_speed * 0.85 if dist < self.genes["close_chase_distance"] else self.max_speed
            return Action(angle, speed, attack_target_id=best_prey.creature_id)

        # ---- Priority 4: Forage efficiently (prefer high-value food) ----
        if perception.nearby_food:
            food = max(
                perception.nearby_food,
                key=lambda f: f.amount / (self._dist(perception, f.x, f.y) + 10.0),
            )
            angle = math.atan2(food.y - perception.self_y, food.x - perception.self_x)
            return Action(angle, self.max_speed * self.genes["food_speed_ratio"])

        # ---- Priority 5: Edge avoidance ----
        edge_angle = self._edge_escape_angle(perception)
        if edge_angle is not None:
            return Action(edge_angle, self.max_speed * 0.7)

        # ---- Priority 6: Wander ----
        angle = (
            perception.self_angle
            + math.sin(perception.self_x * 0.013 + perception.self_y * 0.007)
            * self.genes["wander_turn"]
        )
        return Action(angle, self.max_speed * 0.4)

    # -- Helpers --

    def _dist(self, p: Perception, x: float, y: float) -> float:
        return math.hypot(x - p.self_x, y - p.self_y)

    def _away_from(self, p: Perception, x: float, y: float) -> float:
        return math.atan2(p.self_y - y, p.self_x - x)

    def _best_nearby_target(self, p: Perception) -> tuple[float, float] | None:
        """Best prey or food to move toward (for reproduction positioning)."""
        best = None
        best_score = -1.0
        for c in p.nearby_creatures:
            if c.size < p.self_size:
                score = c.energy_pct / (self._dist(p, c.x, c.y) + 10.0)
                if score > best_score:
                    best_score = score
                    best = (c.x, c.y)
        for f in p.nearby_food:
            score = f.amount / (self._dist(p, f.x, f.y) + 10.0)
            if score > best_score:
                best_score = score
                best = (f.x, f.y)
        return best

    def _edge_escape_angle(self, p: Perception) -> float | None:
        """Return angle toward center if near edges, else None."""
        margin = max(50.0, p.self_size * 4.0)
        dx = 0.0
        dy = 0.0
        if p.self_x < margin:
            dx += 1.0
        elif p.self_x > p.world_width - margin:
            dx -= 1.0
        if p.self_y < margin:
            dy += 1.0
        elif p.self_y > p.world_height - margin:
            dy -= 1.0
        if dx == 0.0 and dy == 0.0:
            return None
        return math.atan2(dy, dx)
