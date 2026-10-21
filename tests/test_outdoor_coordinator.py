"""Tests for the Air Quality Data Coordinator calculations."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
from homeassistant.util import dt as dt_util

from custom_components.air_quality_metrics.const import CONF_SENSORS
from custom_components.air_quality_metrics.sensors.outdoor.coordinator import (
    OutdoorDataCoordinator,
)


@dataclass
class MockState:
    """Mock Home Assistant entity state object for recorder history."""

    state: str
    last_updated: datetime


@pytest.fixture
def mock_hass():
    """Fixture to provide a mocked HomeAssistant instance with State Engine support."""
    hass = MagicMock()
    mock_state_obj = MagicMock()
    mock_state_obj.attributes = {
        "unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
    }
    hass.states.get.return_value = mock_state_obj
    return hass


@pytest.fixture
def mock_config_entry():
    """Fixture to provide a mocked Home Assistant ConfigEntry using the unified sensor config."""
    entry = MagicMock()
    entry.title = "Test Location"
    entry.data = {
        CONF_SENSORS: ["sensor.home_pm25", "sensor.home_pm10", "sensor.home_so2"],
        "scan_interval": 5,
    }
    entry.options = {}
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Fixture to provide an initialized outdoor data coordinator instance."""
    # Ensure we patch the correct initialization hook inside the targeted outdoor submodule path
    with patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.DataUpdateCoordinator.__init__"
    ):
        coord = OutdoorDataCoordinator(mock_hass, mock_config_entry)
        coord.hass = mock_hass
        coord.entry = mock_config_entry
        return coord


class TestOutdoorCoordinator:
    """Container for testing calculation rules in the Outdoor Air Quality Data Coordinator."""

    @pytest.mark.parametrize(
        "sensor_type", [SensorDeviceClass.PM25, SensorDeviceClass.PM10]
    )
    @pytest.mark.parametrize(
        ("states", "expected_aqi", "expected_hours"),
        [
            pytest.param(["0.0"] * 12, 0, 0, id="valid-zero-history"),
            pytest.param(["unknown"] * 12, None, 2, id="unknown-history"),
            pytest.param(["unavailable"] * 12, None, 2, id="unavailable-history"),
            pytest.param(["-1.0"] * 12, None, 2, id="negative-history"),
            pytest.param(
                ["0.0", "unknown", "unavailable"], None, 1, id="one-valid-hour"
            ),
        ],
    )
    def test_zero_and_invalid_history(
        self, coordinator, sensor_type, states, expected_aqi, expected_hours
    ):
        """Exercise history parsing and the real NowCast calculation together."""
        now = dt_util.utcnow()
        history = {
            "sensor.test_particles": [
                MockState(
                    state=state, last_updated=now - timedelta(hours=hour, minutes=30)
                )
                for hour, state in enumerate(states)
            ]
        }
        metrics = coordinator._process_pollutant_metrics(
            ["sensor.test_particles"], history, sensor_type
        )
        assert metrics.nowcast_aqi == expected_aqi
        assert metrics.nowcast_hours_remaining == expected_hours

    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_nowcast"
    )
    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_aqi"
    )
    def test_process_pollutant_metrics_perfect_data(
        self, mock_calc_aqi, mock_calc_nowcast, coordinator: OutdoorDataCoordinator
    ):
        """24 full hours of perfect static clean data."""
        mock_calc_aqi.return_value = 50
        mock_calc_nowcast.return_value = (50, 0)

        now = dt_util.utcnow()
        mock_history = []
        for hour in range(24):
            update_time = now - timedelta(hours=hour, minutes=30)
            mock_history.append(MockState(state="12.0", last_updated=update_time))

        history_dict = {"sensor.home_pm25": mock_history}

        metrics = coordinator._process_pollutant_metrics(
            ["sensor.home_pm25"], history_dict, SensorDeviceClass.PM25
        )

        assert metrics.daily_aqi == 50
        assert metrics.daily_hours_remaining == 0
        assert metrics.nowcast_aqi == 50
        assert metrics.nowcast_hours_remaining == 0

    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_nowcast"
    )
    def test_process_pollutant_metrics_no_sensors(
        self, mock_estimate_nowcast, coordinator
    ):
        """Edge case where sensor list array parameter is completely empty."""
        mock_estimate_nowcast.return_value = (None, 2)
        metrics = coordinator._process_pollutant_metrics([], {}, SensorDeviceClass.PM25)

        assert metrics.daily_aqi is None
        assert metrics.daily_hours_remaining == 18
        assert metrics.nowcast_aqi is None
        assert metrics.nowcast_hours_remaining == 2

    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_nowcast"
    )
    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_aqi"
    )
    def test_process_pollutant_metrics_insufficient_24h_data(
        self, mock_calc_aqi, mock_calc_nowcast, coordinator
    ):
        """We have enough data points for NowCast, but not enough for the 24h Daily metric (needs 18)."""
        mock_calc_aqi.return_value = 45
        mock_calc_nowcast.return_value = (45, 0)
        now = dt_util.utcnow()

        mock_history = []
        for hour in range(5):
            update_time = now - timedelta(hours=hour, minutes=30)
            mock_history.append(MockState(state="10.5", last_updated=update_time))

        history_dict = {"sensor.home_pm25": mock_history}

        metrics = coordinator._process_pollutant_metrics(
            ["sensor.home_pm25"], history_dict, SensorDeviceClass.PM25
        )

        assert metrics.daily_aqi is None
        assert metrics.daily_hours_remaining > 0
        assert metrics.nowcast_aqi == 45
        assert metrics.nowcast_hours_remaining == 0

    @patch(
        "custom_components.air_quality_metrics.sensors.outdoor.coordinator.calculate_nowcast"
    )
    def test_process_pollutant_metrics_failed_nowcast_missing_recent(
        self, mock_calc_nowcast, coordinator
    ):
        """Plenty of old data, but nothing within the last 3 hours (NowCast fails)."""
        mock_calc_nowcast.return_value = (None, 2)
        now = dt_util.utcnow()

        mock_history = []
        for hour in range(4, 22):
            update_time = now - timedelta(hours=hour, minutes=30)
            mock_history.append(MockState(state="15.0", last_updated=update_time))

        history_dict = {"sensor.home_pm25": mock_history}

        metrics = coordinator._process_pollutant_metrics(
            ["sensor.home_pm25"], history_dict, SensorDeviceClass.PM25
        )

        assert metrics.nowcast_aqi is None
        assert metrics.nowcast_hours_remaining == 2
