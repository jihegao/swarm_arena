from __future__ import annotations

import random

from config import CREATURE_LIMITS, DEFAULT_CREATURE_COLOR
from creature import Creature


class EvolvableCreature(Creature):
    """Base class for creatures whose behavior can be tuned by GA genes."""

    gene_defs: dict[str, tuple[float, float]] = {}

    def __init__(
        self,
        x: float,
        y: float,
        genes: dict[str, float] | None = None,
        creature_type: str | None = None,
        color: tuple[int, int, int] | None = None,
    ):
        super().__init__(
            x,
            y,
            creature_type or self.__class__.__name__,
            color or DEFAULT_CREATURE_COLOR,
        )
        self.genes = self.normalize_genes(genes or self.random_genes())
        self.apply_gene_attributes()
        self.clamp()

    @classmethod
    def random_genes(cls) -> dict[str, float]:
        return {
            name: random.uniform(lo, hi)
            for name, (lo, hi) in cls.gene_defs.items()
        }

    @classmethod
    def normalize_genes(cls, genes: dict[str, float]) -> dict[str, float]:
        normalized = cls.random_genes()
        for name, value in genes.items():
            if name not in cls.gene_defs:
                continue
            lo, hi = cls.gene_defs[name]
            normalized[name] = max(lo, min(hi, float(value)))
        return normalized

    def apply_gene_attributes(self):
        for attr in CREATURE_LIMITS:
            if attr in self.genes:
                setattr(self, attr, self.genes[attr])
                if attr == "max_energy":
                    self.energy = self.max_energy
