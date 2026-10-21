"""Canadian one-hour PM2.5 smoke component; see docs/canadian-aqhi.md."""

from datetime import datetime, timedelta
from fractions import Fraction
from math import ceil, isfinite

from homeassistant.core import State


def pm25_value(state: State | None) -> float | None:
    """Reject invalid concentrations and unverified units rather than guessing."""
    if state is None or state.attributes.get("device_class") != "pm25":
        return None
    if state.attributes.get("unit_of_measurement") not in ("μg/m³", "\u00b5g/m³"):
        return None
    try:
        value = float(state.state)
    except TypeError, ValueError:
        return None
    return value if isfinite(value) and value >= 0 else None


def hour_mean(
    states: list[State], start: datetime, end: datetime
) -> tuple[Fraction | None, float]:
    """Integrate HA held states; require full valid coverage (local policy)."""
    ordered = sorted(states, key=lambda state: state.last_updated)
    weighted = Fraction(0)
    covered = 0
    # HA timestamps have microsecond resolution: never relax full coverage
    # with an epsilon, which could admit a real invalid interval.
    tick = timedelta(microseconds=1)
    duration = (end - start) // tick
    for pos, state in enumerate(ordered):
        left = max(start, state.last_updated)
        right = (
            min(end, ordered[pos + 1].last_updated) if pos + 1 < len(ordered) else end
        )
        microseconds = max(0, (right - left) // tick)
        value = pm25_value(state)
        if value is not None:
            # Preserve the recorded decimal exactly through index derivation.
            # Float accumulation can turn a constant 100 hour into 10+.
            weighted += Fraction(state.state) * microseconds
            covered += microseconds
    return (weighted / duration if covered == duration else None, covered / duration)


def smoke_index(pm25: float | Fraction | None) -> int | None:
    """BCCDC bands; Yao et al. 2019/2020 ceiling rule, 11 represents 10+."""
    if pm25 is None or not isfinite(pm25) or pm25 < 0:
        return None
    return min(11, max(1, ceil(pm25 / 10)))


def smoke_category(index: int | None) -> str | None:
    """Canadian risk categories, not US AQI categories."""
    if index is None:
        return None
    if index <= 3:
        return "low"
    if index <= 6:
        return "moderate"
    if index <= 10:
        return "high"
    return "very_high"
