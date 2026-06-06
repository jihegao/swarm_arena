from __future__ import annotations

import contextlib
import io
import random
from dataclasses import dataclass

from config import GAME_OVER_TICK, SCREEN_HEIGHT, SCREEN_WIDTH
from creature import Creature
from creature_loader import load_creatures
from food import Food
from world import World


@dataclass
class EvaluationResult:
    fitness: float
    survival_ticks: float
    survivor_count: float
    total_energy: float
    wins: float


def reset_entity_ids():
    Creature._next_id = 0
    Food._next_id = 0


def load_default_opponents(quiet: bool = True) -> list[type[Creature]]:
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            return load_creatures()
    return load_creatures()


def run_episode(
    target_cls: type[Creature],
    opponent_classes: list[type[Creature]] | None = None,
    width: int = SCREEN_WIDTH,
    height: int = SCREEN_HEIGHT,
    seed: int | None = None,
    quiet_opponent_warnings: bool = True,
) -> EvaluationResult:
    if seed is not None:
        random.seed(seed)
    reset_entity_ids()

    if opponent_classes is None:
        opponent_classes = load_default_opponents(quiet=quiet_opponent_warnings)

    classes: list[type[Creature]] = [target_cls]
    classes.extend(cls for cls in opponent_classes if cls.__name__ != target_cls.__name__)

    world = World(width, height)
    world.spawn_creatures(classes)
    for creature in world.creatures:
        world._class_map[creature.creature_type] = type(creature)

    last_alive_tick = 0
    while not world.game_over:
        target_alive = [c for c in world.creatures if c.is_alive and isinstance(c, target_cls)]
        if target_alive:
            last_alive_tick = world.tick
        world.update()

    survivors = [c for c in world.creatures if c.is_alive and isinstance(c, target_cls)]
    total_energy = sum(c.energy for c in survivors)
    wins = 1.0 if world.winner is not None and isinstance(world.winner, target_cls) else 0.0
    if not survivors:
        fitness = last_alive_tick / GAME_OVER_TICK
    else:
        fitness = len(survivors) * 10 + total_energy / 100 + wins * 20

    return EvaluationResult(
        fitness=fitness,
        survival_ticks=float(last_alive_tick),
        survivor_count=float(len(survivors)),
        total_energy=total_energy,
        wins=wins,
    )


def average_results(results: list[EvaluationResult]) -> EvaluationResult:
    if not results:
        return EvaluationResult(0.0, 0.0, 0.0, 0.0, 0.0)
    count = len(results)
    return EvaluationResult(
        fitness=sum(r.fitness for r in results) / count,
        survival_ticks=sum(r.survival_ticks for r in results) / count,
        survivor_count=sum(r.survivor_count for r in results) / count,
        total_energy=sum(r.total_energy for r in results) / count,
        wins=sum(r.wins for r in results) / count,
    )

