"""Linear-algebra helpers for weighted one-dimensional layout problems."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class AxisConstraint:
    start: int
    end: int
    delta: float
    weight: float = 1.0


def solve_weighted_positions(
    anchors: np.ndarray,
    *,
    anchor_weights: np.ndarray | None = None,
    constraints: list[AxisConstraint] | None = None,
    pin_index: int = 0,
    pin_weight: float = 0.0,
) -> np.ndarray:
    """Solve a weighted least-squares chain with pairwise offset constraints."""

    count = len(anchors)
    if count <= 1:
        return anchors.copy()

    weights = (
        np.asarray(anchor_weights, dtype=float)
        if anchor_weights is not None
        else np.ones(count, dtype=float)
    )
    pair_constraints = constraints or []

    matrix = np.zeros((count, count), dtype=float)
    rhs = np.zeros(count, dtype=float)

    for index, anchor in enumerate(np.asarray(anchors, dtype=float)):
        weight = float(weights[index])
        if weight <= 0:
            continue
        matrix[index, index] += weight
        rhs[index] += weight * float(anchor)

    for constraint in pair_constraints:
        weight = max(float(constraint.weight), 0.0)
        if weight <= 0 or constraint.start == constraint.end:
            continue
        matrix[constraint.start, constraint.start] += weight
        matrix[constraint.end, constraint.end] += weight
        matrix[constraint.start, constraint.end] -= weight
        matrix[constraint.end, constraint.start] -= weight
        rhs[constraint.start] += -weight * float(constraint.delta)
        rhs[constraint.end] += weight * float(constraint.delta)

    effective_pin_weight = float(pin_weight)
    if effective_pin_weight <= 0 and not np.any(np.diag(matrix)):
        effective_pin_weight = 1.0
    if effective_pin_weight > 0:
        matrix[pin_index, pin_index] += effective_pin_weight
        rhs[pin_index] += effective_pin_weight * float(anchors[pin_index])

    return np.linalg.solve(matrix, rhs)
