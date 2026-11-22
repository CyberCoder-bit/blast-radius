"""Split a test selection over up to 8 workers, minimising max load + 2 s per worker."""

from __future__ import annotations

WORKER_MS = 2000
MAX_WORKERS = 8


def schedule(numbers: list[int], duration_ms: dict[int, int]) -> list[list[int]]:
    if not numbers:
        return []
    order = sorted(numbers, key=lambda n: (-duration_ms[n], n))
    best_cost, best_bins = None, None
    for k in range(1, min(MAX_WORKERS, len(order)) + 1):
        loads = [0] * k
        bins: list[list[int]] = [[] for _ in range(k)]
        for n in order:
            i = loads.index(min(loads))
            bins[i].append(n)
            loads[i] += duration_ms[n]
        cost = max(loads) + WORKER_MS * k
        if best_cost is None or cost < best_cost:
            best_cost, best_bins = cost, bins
    return best_bins
