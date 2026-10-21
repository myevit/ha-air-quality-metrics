"""Native Canadian smoke component, not a renamed US AQI."""

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.core import State

from custom_components.air_quality_metrics.metrics import canadian as module

END = datetime(2026, 10, 20, 12, tzinfo=UTC)
START = END - timedelta(hours=1)
ATTRS = {"device_class": "pm25", "unit_of_measurement": "μg/m³"}


def state(value, minute, attrs=ATTRS):
    return State(
        "sensor.test_pm25",
        str(value),
        attrs,
        last_updated=START + timedelta(minutes=minute),
    )


@pytest.mark.parametrize(
    ("states", "expected", "coverage"),
    [
        ([state(0, -10)], 0, 1),
        ([state(10, -5), state(70, 50)], 20, 1),
        ([state(100, -5), state(0, 0)], 0, 1),
        ([state(20, 10)], None, 5 / 6),
        ([state(20, -1), state("unknown", 30)], None, 0.5),
        ([state(20, -1), state("unavailable", 20), state(40, 40)], None, 2 / 3),
        ([state(-1, -1)], None, 0),
        ([state("nan", -1)], None, 0),
        ([state(20, -1, {**ATTRS, "unit_of_measurement": "ppm"})], None, 0),
        ([state(20, -1, {**ATTRS, "device_class": "pm10"})], None, 0),
        ([], None, 0),
    ],
)
def test_time_weighted_complete_hour(states, expected, coverage):
    assert hasattr(module, "hour_mean")
    mean, fraction = module.hour_mean(states, START, END)
    assert mean == expected
    assert fraction == pytest.approx(coverage)


@pytest.mark.parametrize(
    ("pm", "expected", "category"),
    [
        (0, 1, "low"),
        (10, 1, "low"),
        (10.01, 2, "low"),
        (30, 3, "low"),
        (30.01, 4, "moderate"),
        (51, 6, "moderate"),  # Yao et al. Table 2 worked example
        (60, 6, "moderate"),
        (60.01, 7, "high"),
        (100, 10, "high"),
        (100.01, 11, "very_high"),
        (1000, 11, "very_high"),
        (-1, None, None),
        (float("nan"), None, None),
        (float("inf"), None, None),
        (None, None, None),
    ],
)
def test_bccdc_smoke_component(pm, expected, category):
    assert module.smoke_index(pm) == expected
    assert module.smoke_category(expected) == category
