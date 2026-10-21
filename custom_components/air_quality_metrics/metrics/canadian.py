"""Canadian one-hour PM2.5 smoke component; see docs/canadian-aqhi.md."""

from datetime import datetime
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
) -> tuple[float | None, float]:
    """Integrate HA held states; require full valid coverage (local policy)."""
    ordered = sorted(states, key=lambda state: state.last_updated)
    weighted = covered = 0.0
    duration = (end - start).total_seconds()
    for pos, state in enumerate(ordered):
        left = max(start, state.last_updated)
        right = (
            min(end, ordered[pos + 1].last_updated) if pos + 1 < len(ordered) else end
        )
        seconds = max(0.0, (right - left).total_seconds())
        value = pm25_value(state)
        if value is not None:
            weighted += value * seconds
            covered += seconds
    return (weighted / duration if covered == duration else None, covered / duration)


def smoke_index(pm25: float | None) -> int | None:
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
