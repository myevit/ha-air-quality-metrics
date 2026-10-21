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
