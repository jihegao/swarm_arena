from __future__ import annotations
import random
from config import FOOD_AMOUNT_MIN, FOOD_AMOUNT_MAX, FOOD_COLOR


class Food:
    __slots__ = ('id', 'x', 'y', 'amount', 'size', 'color')

    _next_id = 0

    def __init__(self, x: float, y: float, amount: float | None = None):
        self.id = Food._next_id
        Food._next_id += 1
        self.x = x
        self.y = y
        self.amount = amount if amount is not None else random.uniform(
            FOOD_AMOUNT_MIN, FOOD_AMOUNT_MAX
        )
        self.size = random.uniform(1.0, 10.0)
        self.color = FOOD_COLOR

    @property
    def depleted(self) -> bool:
        return self.amount <= 0
