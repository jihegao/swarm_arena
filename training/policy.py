from __future__ import annotations

import math
import random
from dataclasses import dataclass

from creature import Action, Creature, Perception


ACTION_NAMES = (
    "FLEE_THREAT",
    "CHASE_PREY",
    "SEEK_FOOD",
    "REPRODUCE",
    "WANDER",
    "REST",
)


@dataclass(frozen=True)
class SceneFeatures:
    energy_pct: float
    nearest_food_dist: float
    nearest_food_angle: float
    best_food_score: float
    nearest_threat_dist: float
    nearest_threat_angle: float
    nearest_prey_dist: float
    nearest_prey_angle: float
    prey_count: int
    threat_count: int
    edge_pressure_x: float
    edge_pressure_y: float
    vision_radius: float

    def as_dict(self) -> dict[str, float]:
        return {
            "energy_pct": self.energy_pct,
            "nearest_food_dist": self.nearest_food_dist,
            "nearest_food_angle": self.nearest_food_angle,
            "best_food_score": self.best_food_score,
            "nearest_threat_dist": self.nearest_threat_dist,
            "nearest_threat_angle": self.nearest_threat_angle,
            "nearest_prey_dist": self.nearest_prey_dist,
            "nearest_prey_angle": self.nearest_prey_angle,
            "prey_count": float(self.prey_count),
            "threat_count": float(self.threat_count),
            "edge_pressure_x": self.edge_pressure_x,
            "edge_pressure_y": self.edge_pressure_y,
        }


def angle_to(px: float, py: float, tx: float, ty: float) -> float:
    return math.atan2(ty - py, tx - px)


def distance(px: float, py: float, tx: float, ty: float) -> float:
    return math.hypot(tx - px, ty - py)


def normalize_relative_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += 2 * math.pi
    while angle > math.pi:
        angle -= 2 * math.pi
    return angle / math.pi


def encode_features(perception: Perception) -> SceneFeatures:
    vision_radius = max(1.0, max(
        [distance(perception.self_x, perception.self_y, f.x, f.y) for f in perception.nearby_food]
        + [distance(perception.self_x, perception.self_y, c.x, c.y) for c in perception.nearby_creatures]
        + [1.0]
    ))
    energy_pct = perception.self_energy / perception.self_max_energy if perception.self_max_energy > 0 else 0.0

    nearest_food_dist = 1.0
    nearest_food_angle = 0.0
    best_food_score = 0.0
    if perception.nearby_food:
        nearest_food = min(
            perception.nearby_food,
            key=lambda f: distance(perception.self_x, perception.self_y, f.x, f.y),
        )
        food_dist = distance(perception.self_x, perception.self_y, nearest_food.x, nearest_food.y)
        nearest_food_dist = min(1.0, food_dist / vision_radius)
        nearest_food_angle = normalize_relative_angle(
            angle_to(perception.self_x, perception.self_y, nearest_food.x, nearest_food.y)
            - perception.self_angle
        )
        best_food_score = max(
            f.amount / (distance(perception.self_x, perception.self_y, f.x, f.y) + 10.0)
            for f in perception.nearby_food
        )

    threats = [c for c in perception.nearby_creatures if c.size >= perception.self_size]
    prey = [c for c in perception.nearby_creatures if c.size < perception.self_size]

    nearest_threat_dist = 1.0
    nearest_threat_angle = 0.0
    if threats:
        nearest_threat = min(
            threats,
            key=lambda c: distance(perception.self_x, perception.self_y, c.x, c.y),
        )
        threat_dist = distance(perception.self_x, perception.self_y, nearest_threat.x, nearest_threat.y)
        nearest_threat_dist = min(1.0, threat_dist / vision_radius)
        nearest_threat_angle = normalize_relative_angle(
            angle_to(perception.self_x, perception.self_y, nearest_threat.x, nearest_threat.y)
            - perception.self_angle
        )

    nearest_prey_dist = 1.0
    nearest_prey_angle = 0.0
    if prey:
        nearest_prey = min(
            prey,
            key=lambda c: distance(perception.self_x, perception.self_y, c.x, c.y),
        )
        prey_dist = distance(perception.self_x, perception.self_y, nearest_prey.x, nearest_prey.y)
        nearest_prey_dist = min(1.0, prey_dist / vision_radius)
        nearest_prey_angle = normalize_relative_angle(
            angle_to(perception.self_x, perception.self_y, nearest_prey.x, nearest_prey.y)
            - perception.self_angle
        )

    margin = max(40.0, perception.self_size * 6.0)
    edge_pressure_x = 0.0
    edge_pressure_y = 0.0
    if perception.self_x < margin:
        edge_pressure_x = 1.0
    elif perception.self_x > perception.world_width - margin:
        edge_pressure_x = -1.0
    if perception.self_y < margin:
        edge_pressure_y = 1.0
    elif perception.self_y > perception.world_height - margin:
        edge_pressure_y = -1.0

    return SceneFeatures(
        energy_pct=energy_pct,
        nearest_food_dist=nearest_food_dist,
        nearest_food_angle=nearest_food_angle,
        best_food_score=best_food_score,
        nearest_threat_dist=nearest_threat_dist,
        nearest_threat_angle=nearest_threat_angle,
        nearest_prey_dist=nearest_prey_dist,
        nearest_prey_angle=nearest_prey_angle,
        prey_count=len(prey),
        threat_count=len(threats),
        edge_pressure_x=edge_pressure_x,
        edge_pressure_y=edge_pressure_y,
        vision_radius=vision_radius,
    )


def discrete_state_key(features: SceneFeatures) -> str:
    energy = "low" if features.energy_pct < 0.8 else "mid" if features.energy_pct < 1.8 else "high"
    food = "none"
    if features.best_food_score > 0:
        food = "near" if features.nearest_food_dist < 0.35 else "far"
    threat = "none"
    if features.threat_count > 0:
        threat = "near" if features.nearest_threat_dist < 0.35 else "far"
    prey = "none"
    if features.prey_count > 0:
        prey = "near" if features.nearest_prey_dist < 0.35 else "far"
    edge = "risky" if features.edge_pressure_x or features.edge_pressure_y else "safe"
    return "|".join((energy, food, threat, prey, edge))


def _nearest_threat(perception: Perception):
    threats = [c for c in perception.nearby_creatures if c.size >= perception.self_size]
    if not threats:
        return None
    return min(threats, key=lambda c: distance(perception.self_x, perception.self_y, c.x, c.y))


def _nearest_prey(perception: Perception):
    prey = [c for c in perception.nearby_creatures if c.size < perception.self_size]
    if not prey:
        return None
    return min(prey, key=lambda c: distance(perception.self_x, perception.self_y, c.x, c.y))


def _best_food(perception: Perception):
    if not perception.nearby_food:
        return None
    return max(
        perception.nearby_food,
        key=lambda f: f.amount / (distance(perception.self_x, perception.self_y, f.x, f.y) + 10.0),
    )


def decode_action(action_name: str, perception: Perception, creature: Creature) -> Action:
    if action_name == "FLEE_THREAT":
        threat = _nearest_threat(perception)
        if threat is not None:
            angle = math.atan2(perception.self_y - threat.y, perception.self_x - threat.x)
            return Action(angle, creature.max_speed)

    if action_name == "CHASE_PREY":
        prey = _nearest_prey(perception)
        if prey is not None:
            angle = angle_to(perception.self_x, perception.self_y, prey.x, prey.y)
            return Action(angle, creature.max_speed, attack_target_id=prey.creature_id)

    if action_name == "SEEK_FOOD":
        food = _best_food(perception)
        if food is not None:
            angle = angle_to(perception.self_x, perception.self_y, food.x, food.y)
            return Action(angle, creature.max_speed * 0.8)

    if action_name == "REPRODUCE":
        food = _best_food(perception)
        if food is not None:
            angle = angle_to(perception.self_x, perception.self_y, food.x, food.y)
            return Action(angle, creature.max_speed * 0.4, reproduce=True)
        return Action(perception.self_angle, 0.0, reproduce=True)

    if action_name == "REST":
        return Action(perception.self_angle, 0.0)

    turn = math.sin(perception.self_x * 0.013 + perception.self_y * 0.007) * 0.45
    if random.random() < 0.05:
        turn += random.uniform(-0.5, 0.5)
    return Action(perception.self_angle + turn, creature.max_speed * 0.45)

