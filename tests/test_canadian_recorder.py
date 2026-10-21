"""Verify the actual HA recorder carry-forward/invalid-state API contract."""

from datetime import UTC, datetime, timedelta

import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.air_quality_metrics.sensors.canadian import (
    CanadianDataCoordinator,
)

ATTRS = {"device_class": "pm25", "unit_of_measurement": "μg/m³"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Initialize recorder database fixtures before the global hass fixture."""
    yield


@pytest.mark.parametrize(
    ("before", "at_start", "at_end", "mean", "index", "category", "coverage"),
    [
        pytest.param("10", "100", "100", 100, 10, "high", 1, id="rising"),
        pytest.param("100", "10", "10", 10, 1, "low", 1, id="falling"),
        pytest.param("unknown", "100", "100", 100, 10, "high", 1, id="valid-at-start"),
        pytest.param(
            "100", "unknown", "100", None, None, None, 0, id="invalid-at-start"
        ),
        pytest.param("10", "100", "10", 100, 10, "high", 1, id="end-exclusive"),
    ],
)
async def test_real_recorder_exact_hour_boundaries(
    recorder_mock,
    hass,
    freezer,
    before,
    at_start,
    at_end,
    mean,
    index,
    category,
    coverage,
):
    """Include the start transition, not its predecessor or the end transition."""
    start = datetime(2026, 10, 20, 11, tzinfo=UTC)
    end = start + timedelta(hours=1)
    freezer.move_to(start - timedelta(minutes=10))
    assert await async_setup_component(hass, "recorder", {})
    for timestamp, value in (
        (start - timedelta(minutes=10), before),
        (start, at_start),
        (end, at_end),
    ):
        freezer.move_to(timestamp)
        hass.states.async_set("sensor.test_pm25", value, ATTRS)
        await hass.async_block_till_done()
        await async_wait_recording_done(hass)
    entry = MockConfigEntry(
        domain="air_quality_metrics", data={"sensors": ["sensor.test_pm25"]}
    )
    result = await CanadianDataCoordinator(hass, entry)._async_update_data()
    assert result["pm25_mean"] == mean
    assert result["index"] == index
    assert result["category"] == category
    assert result["coverage"] == coverage
    assert result["status"] == ("valid" if index is not None else "incomplete_history")
    assert result["period_start"] == start.isoformat()
    assert result["period_end"] == end.isoformat()


@pytest.mark.parametrize("interrupted", [False, True])
async def test_real_recorder_carryforward(recorder_mock, hass, freezer, interrupted):
    start = datetime(2026, 10, 20, 11, tzinfo=UTC)
    freezer.move_to(start - timedelta(minutes=10))
    assert await async_setup_component(hass, "recorder", {})
    hass.states.async_set("sensor.test_pm25", "10", ATTRS)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    freezer.move_to(start + timedelta(minutes=30))
    if interrupted:
        hass.states.async_set("sensor.test_pm25", "unavailable", ATTRS)
        await hass.async_block_till_done()
        await async_wait_recording_done(hass)
    freezer.move_to(start + timedelta(minutes=50))
    hass.states.async_set("sensor.test_pm25", "70", ATTRS)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)
    freezer.move_to(start + timedelta(hours=1))
    # A fresh unchanged report must not require a changed concentration.
    hass.states.async_set("sensor.test_pm25", "70", ATTRS)
    entry = MockConfigEntry(
        domain="air_quality_metrics", data={"sensors": ["sensor.test_pm25"]}
    )
    coord = CanadianDataCoordinator(hass, entry)
    result = await coord._async_update_data()
    assert result["pm25_mean"] == (None if interrupted else 20)
    assert result["index"] == (None if interrupted else 2)
    assert result["coverage"] == pytest.approx(2 / 3 if interrupted else 1)
    assert result["evaluated_at"] == (start + timedelta(hours=1)).isoformat()
    assert result["source_last_reported"] == result["evaluated_at"]
    freezer.move_to(start + timedelta(hours=1, minutes=1))
    hass.states.async_set("sensor.test_pm25", "70", ATTRS)
    again = await coord._async_update_data()
    assert again["index"] == result["index"]
    assert again["evaluated_at"] != result["evaluated_at"]
    assert again["source_last_reported"] == again["evaluated_at"]
