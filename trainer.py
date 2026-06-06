from __future__ import annotations

import contextlib
import io
import random
from dataclasses import dataclass
from typing import Callable

from config import GAME_OVER_TICK, SCREEN_HEIGHT, SCREEN_WIDTH
from creature import Creature
from creature_loader import load_creatures
from evolvable import EvolvableCreature
from world import World


FitnessFn = Callable[[dict[str, float]], float]
ProgressFn = Callable[[str], None]


@dataclass(frozen=True)
class GAConfig:
    population_size: int = 30
    generations: int = 50
    mutation_rate: float = 0.15
    elite_count: int = 2
    tournament_size: int = 5
    width: int = SCREEN_WIDTH
    height: int = SCREEN_HEIGHT
    seed: int | None = None
    quiet_opponent_warnings: bool = True

    def __post_init__(self):
        if self.population_size < 1:
            raise ValueError("population_size must be at least 1")
        if self.generations < 1:
            raise ValueError("generations must be at least 1")
        if not 0 <= self.mutation_rate <= 1:
            raise ValueError("mutation_rate must be between 0 and 1")
        if self.elite_count < 0:
            raise ValueError("elite_count must be at least 0")
        if self.elite_count > self.population_size:
            raise ValueError("elite_count cannot exceed population_size")
        if self.tournament_size < 1:
            raise ValueError("tournament_size must be at least 1")
        if self.width < 1 or self.height < 1:
            raise ValueError("width and height must be positive")


@dataclass
class GenerationStats:
    generation: int
    best_fitness: float
    average_fitness: float
    best_genes: dict[str, float]


@dataclass
class TrainingResult:
    best_genes: dict[str, float]
    best_fitness: float
    history: list[GenerationStats]


def make_fixed_gene_class(
    creature_cls: type[EvolvableCreature],
    genes: dict[str, float],
) -> type[EvolvableCreature]:
    fixed_genes = creature_cls.normalize_genes(genes)

    class FixedGeneCreature(creature_cls):
        def __init__(self, x: float, y: float):
            super().__init__(x, y, genes=fixed_genes.copy())

    FixedGeneCreature.__name__ = creature_cls.__name__
    FixedGeneCreature.__qualname__ = creature_cls.__qualname__
    FixedGeneCreature.__module__ = creature_cls.__module__
    return FixedGeneCreature


def evaluate_genes(
    creature_cls: type[EvolvableCreature],
    genes: dict[str, float],
    opponent_classes: list[type[Creature]] | None = None,
    width: int = SCREEN_WIDTH,
    height: int = SCREEN_HEIGHT,
    quiet_opponent_warnings: bool = True,
) -> float:
    fixed_cls = make_fixed_gene_class(creature_cls, genes)
    if opponent_classes is None:
        if quiet_opponent_warnings:
            with contextlib.redirect_stdout(io.StringIO()):
                opponent_classes = load_creatures()
        else:
            opponent_classes = load_creatures()

    classes: list[type[Creature]] = [fixed_cls]
    classes.extend(
        cls for cls in opponent_classes
        if cls.__name__ != creature_cls.__name__
    )

    world = World(width, height)
    world.spawn_creatures(classes)
    for creature in world.creatures:
        world._class_map[creature.creature_type] = type(creature)

    last_alive_tick = 0

    while not world.game_over:
        target_alive = [
            c for c in world.creatures
            if c.is_alive and isinstance(c, fixed_cls)
        ]
        if target_alive:
            last_alive_tick = world.tick
        world.update()

    survivors = [
        c for c in world.creatures
        if c.is_alive and isinstance(c, fixed_cls)
    ]
    if not survivors:
        return last_alive_tick / GAME_OVER_TICK

    total_energy = sum(c.energy for c in survivors)
    return len(survivors) * 10 + total_energy / 100


class GeneticTrainer:
    def __init__(
        self,
        creature_cls: type[EvolvableCreature],
        config: GAConfig | None = None,
        opponent_classes: list[type[Creature]] | None = None,
        fitness_fn: FitnessFn | None = None,
    ):
        if not issubclass(creature_cls, EvolvableCreature):
            raise TypeError("creature_cls must inherit from EvolvableCreature")
        if not creature_cls.gene_defs:
            raise ValueError("creature_cls.gene_defs must define at least one gene")

        self.creature_cls = creature_cls
        self.config = config or GAConfig()
        self.opponent_classes = opponent_classes
        self.fitness_fn = fitness_fn or self._evaluate
        if self.config.seed is not None:
            random.seed(self.config.seed)

    def train(self, progress_callback: ProgressFn | None = None) -> TrainingResult:
        population = [
            self.creature_cls.random_genes()
            for _ in range(self.config.population_size)
        ]
        best_genes: dict[str, float] | None = None
        best_fitness = float("-inf")
        history: list[GenerationStats] = []

        for generation in range(1, self.config.generations + 1):
            if progress_callback is not None:
                progress_callback(
                    f"Evaluating generation {generation:03d}/{self.config.generations:03d} "
                    f"({len(population)} genomes)"
                )

            scored = [(genes, self.fitness_fn(genes)) for genes in population]
            scored.sort(key=lambda item: item[1], reverse=True)

            generation_best, generation_best_fitness = scored[0]
            if generation_best_fitness > best_fitness:
                best_fitness = generation_best_fitness
                best_genes = generation_best.copy()

            average = sum(score for _, score in scored) / len(scored)
            stats = GenerationStats(
                generation=generation,
                best_fitness=generation_best_fitness,
                average_fitness=average,
                best_genes=generation_best.copy(),
            )
            history.append(stats)

            if progress_callback is not None:
                progress_callback(
                    f"Generation {generation:03d}/{self.config.generations:03d}: "
                    f"best={stats.best_fitness:.3f} avg={stats.average_fitness:.3f} "
                    f"overall_best={best_fitness:.3f}"
                )

            if generation < self.config.generations:
                population = self._next_generation(scored)

        if best_genes is None:
            best_genes = {}
        return TrainingResult(best_genes, best_fitness, history)

    def _evaluate(self, genes: dict[str, float]) -> float:
        return evaluate_genes(
            self.creature_cls,
            genes,
            opponent_classes=self.opponent_classes,
            width=self.config.width,
            height=self.config.height,
            quiet_opponent_warnings=self.config.quiet_opponent_warnings,
        )

    def _next_generation(
        self,
        scored: list[tuple[dict[str, float], float]],
    ) -> list[dict[str, float]]:
        population: list[dict[str, float]] = [
            genes.copy()
            for genes, _ in scored[:self.config.elite_count]
        ]

        while len(population) < self.config.population_size:
            parent_a = self._tournament_select(scored)
            parent_b = self._tournament_select(scored)
            child = self._crossover(parent_a, parent_b)
            population.append(self._mutate(child))

        return population

    def _tournament_select(
        self,
        scored: list[tuple[dict[str, float], float]],
    ) -> dict[str, float]:
        size = min(self.config.tournament_size, len(scored))
        contenders = random.sample(scored, size)
        return max(contenders, key=lambda item: item[1])[0]

    def _crossover(
        self,
        parent_a: dict[str, float],
        parent_b: dict[str, float],
    ) -> dict[str, float]:
        names = list(self.creature_cls.gene_defs)
        if len(names) < 2:
            return random.choice([parent_a, parent_b]).copy()

        left = random.randrange(len(names))
        right = random.randrange(left, len(names))
        child = {}
        for index, name in enumerate(names):
            child[name] = parent_b[name] if left <= index <= right else parent_a[name]
        return child

    def _mutate(self, genes: dict[str, float]) -> dict[str, float]:
        mutated = genes.copy()
        for name, (lo, hi) in self.creature_cls.gene_defs.items():
            if random.random() >= self.config.mutation_rate:
                continue
            span = hi - lo
            mutated[name] = max(lo, min(hi, mutated[name] + random.gauss(0, span * 0.1)))
        return self.creature_cls.normalize_genes(mutated)
