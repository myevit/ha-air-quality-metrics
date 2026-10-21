"""Canadian native sensor setup and recorder contract."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.air_quality_metrics import sensor as platform

NOW = datetime(2026, 10, 20, 12, 20, tzinfo=UTC)
ATTRS = {"device_class": "pm25", "unit_of_measurement": "μg/m³"}


@pytest.mark.parametrize(
    ("value", "age", "expected"),
    [
        ("0", 0, 1),
        ("70", 0, 7),
        ("101", 0, 11),
        ("unknown", 0, None),
        ("-1", 0, None),
        ("nan", 0, None),
        ("0", 15, 1),
        ("0", 16, None),
        ("0", -1, None),
        ("unavailable", 0, None),
    ],
)
async def test_canadian_native_setup(hass, value, age, expected):
    assert hasattr(platform, "CanadianDataCoordinator")
    entry = MockConfigEntry(
        domain="air_quality_metrics",
        title="Canadian outdoor",
        data={"profile": "outdoor_canadian_smoke", "sensors": ["sensor.test_pm25"]},
    )
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.SETUP_IN_PROGRESS)
    current = State(
        "sensor.test_pm25", value, ATTRS, last_reported=NOW - timedelta(minutes=age)
    )
    history = State(
        "sensor.test_pm25", value, ATTRS, last_updated=NOW.replace(hour=10, minute=0)
    )
    entities = []
    with (
        patch.object(type(hass.states), "get", return_value=current),
        patch(
            "custom_components.air_quality_metrics.sensors.canadian.dt_util.utcnow",
            return_value=NOW,
        ),
        patch(
            "custom_components.air_quality_metrics.sensors.canadian.history.get_significant_states",
            return_value={"sensor.test_pm25": [history]},
        ) as fetch,
        patch(
            "custom_components.air_quality_metrics.sensors.canadian.get_instance"
        ) as recorder,
    ):
        recorder.return_value.async_add_executor_job = AsyncMock(
            side_effect=lambda fn: fn()
        )
        await platform.async_setup_entry(
            hass, entry, lambda added, _: entities.extend(added)
        )
    assert len(entities) == 2
    numeric, category = entities
    assert numeric.native_value == expected
    assert numeric.device_class is None
    assert numeric.native_unit_of_measurement is None
    assert numeric.extra_state_attributes["index_type"] == "canadian_aqhi_smoke_pm25"
    assert numeric.extra_state_attributes["coverage_required"] == 1.0
    assert "mean_unit" in numeric.extra_state_attributes
    assert numeric.extra_state_attributes["mean_unit"] == "μg/m³"
    assert numeric.extra_state_attributes["scope"] == "local_pm25_only_estimate"
    assert numeric.extra_state_attributes["display_value"] == (
        "10+" if expected == 11 else str(expected) if expected else None
    )
    assert category.native_value == (
        "very_high"
        if expected == 11
        else "high"
        if expected == 7
        else "low"
        if expected == 1
        else None
    )
    if expected is not None:
        kwargs = fetch.call_args.kwargs
        assert kwargs["include_start_time_state"] is True
        assert kwargs["significant_changes_only"] is False
        assert kwargs["minimal_response"] is False
        assert kwargs["no_attributes"] is False
        assert fetch.call_args.args[1:3] == (
            NOW.replace(hour=11, minute=0),
            NOW.replace(minute=0),
        )


@pytest.mark.parametrize("failure", ["missing", "incomplete", "recorder_error"])
async def test_never_retain_prior_result(hass, failure):
    entry = MockConfigEntry(
        domain="air_quality_metrics", data={"sensors": ["sensor.test_pm25"]}
    )
    coord = platform.CanadianDataCoordinator(hass, entry)
    coord.async_set_updated_data({"index": 1, "category": "low"})
    current = State("sensor.test_pm25", "0", ATTRS, last_reported=NOW)
    with (
        patch.object(
            type(hass.states),
            "get",
            return_value=None if failure == "missing" else current,
        ),
        patch(
            "custom_components.air_quality_metrics.sensors.canadian.dt_util.utcnow",
            return_value=NOW,
        ),
        patch(
            "custom_components.air_quality_metrics.sensors.canadian.get_instance"
        ) as recorder,
    ):
        recorder.return_value.async_add_executor_job = AsyncMock(
            return_value={} if failure == "incomplete" else None,
            side_effect=RuntimeError("recorder unavailable")
            if failure == "recorder_error"
            else None,
        )
        result = await coord._async_update_data()
    assert result["index"] is None
    assert result["category"] is None
    assert (
        result["status"]
        == {
            "missing": "source_invalid",
            "incomplete": "incomplete_history",
            "recorder_error": "history_unavailable",
        }[failure]
    )
