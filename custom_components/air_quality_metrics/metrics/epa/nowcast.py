import logging
from collections.abc import Sequence

from custom_components.air_quality_metrics.metrics.epa.config import AQI_CONFIGS
from custom_components.air_quality_metrics.metrics.epa.types import AQISensorType
from custom_components.air_quality_metrics.metrics.helpers import (
    calculate_aqi,
    estimate_hours_until_valid,
    extract_valid_values,
)

_LOGGER = logging.getLogger(__name__)


def calculate_nowcast(
    sensor_type: AQISensorType,
    hourly_averages: Sequence[float | int | None],
    title: str | None = None,
) -> tuple[int | None, int]:
    """
    Calculate NowCast (aka "real time" AQI)

    NowCast is calculated over the previous 12 hours of readings,
    weighted most heavily toward recent hours.

    See: https://en.wikipedia.org/wiki/NowCast_(air_quality_index)

    Returns:
        A tuple containing the nowcast value (None if not available), and the
        estimated hours until the value will be available (zero if the value is
        available).
    """
    nowcast_hours = hourly_averages[:12]
    latest_3_hours_count = len(extract_valid_values(nowcast_hours[:3]))

    _LOGGER.debug(
        "[%s] NowCast window calculation (%s) -> Data points in latest 3 hours: %s/3",
        title,
        sensor_type,
        latest_3_hours_count,
    )

    if latest_3_hours_count >= 2:
        # Calculate the weight factor
        hours_with_data = extract_valid_values(nowcast_hours)
        data_max = max(hours_with_data)
        data_min = min(hours_with_data)
        data_range = data_max - data_min
        # A zero maximum means all valid concentrations are zero (no variation).
        data_rate = data_range / data_max if data_max != 0 else 0.0
        weight_factor = max(0.5, min(1.0, 1.0 - data_rate))

        # Sum up the hourly readigs multiplied by increasingly smaller weight factors
        # e.g. val1 * w^0 + val2 ^ w^1 + ... (remembering that w<1 so higher powers are smaller)
        data_sum = 0.0
        weight_sum = 0.0
        for i, val in enumerate(nowcast_hours):
            if val is not None and val >= 0:
                powered_weight = weight_factor**i
                data_sum += val * powered_weight
                weight_sum += powered_weight

        weighted_value = (data_sum / weight_sum) if weight_sum > 0 else 0
        nowcast_aqi = calculate_aqi(weighted_value, AQI_CONFIGS.get(sensor_type))
        nowcast_hours_remaining = 0
    else:
        nowcast_aqi = None
        nowcast_hours_remaining = estimate_hours_until_valid(
            window_size=3, require_valid=2, hourly_data=hourly_averages
        )

    return (nowcast_aqi, nowcast_hours_remaining)
