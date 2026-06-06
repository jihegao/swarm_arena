from __future__ import annotations
from dataclasses import dataclass
from creature import Creature
from config import EAT_OVERLAP_RATIO


@dataclass
class CombatResult:
    eater_id: int
    eaten_id: int
    energy_gained: float


def try_eat(eater: Creature, target: Creature) -> bool:
    if target.id == eater.id:
        return False
    if not target.is_alive:
        return False
    if eater.size <= target.size:
        return False

    dist = eater.distance_to(target.x, target.y)
    eat_range = (eater.size + target.size) * EAT_OVERLAP_RATIO
    if dist > eat_range:
        return False

    if eater.cooldown > 0:
        return False

    eater.energy += target.energy
    target.energy = 0
    eater.cooldown = 10
    return True
