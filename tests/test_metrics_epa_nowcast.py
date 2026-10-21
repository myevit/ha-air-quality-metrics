from unittest.mock import patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.air_quality_metrics.metrics.epa.config import AQI_CONFIGS
from custom_components.air_quality_metrics.metrics.epa.nowcast import (
    calculate_nowcast,
)


class TestCalculateNowcast:
    """Container for testing NowCast air quality calculation logic."""

    @pytest.mark.parametrize(
        "sensor_type", [SensorDeviceClass.PM25, SensorDeviceClass.PM10]
    )
    @pytest.mark.parametrize(
        "hourly_data",
        [
            pytest.param([0.0] * 12, id="full-zero-window"),
            pytest.param([0.0, None, 0.0] + [None] * 9, id="missing-hours"),
            pytest.param([0.0, -1.0, 0.0] + [None] * 9, id="negative-excluded"),
        ],
    )
    def test_nowcast_valid_zero_window(self, sensor_type, hourly_data):
        """Enough recent zero readings produce AQI zero, not division by zero."""
        assert calculate_nowcast(sensor_type, hourly_data) == (0, 0)

    @pytest.mark.parametrize(
        "sensor_type", [SensorDeviceClass.PM25, SensorDeviceClass.PM10]
    )
    @pytest.mark.parametrize(
        ("hourly_data", "expected"),
        [
            pytest.param([], (None, 2), id="cold-start"),
            pytest.param([None] * 12, (None, 2), id="all-missing"),
            pytest.param([-1.0] * 12, (None, 2), id="all-negative"),
            pytest.param([float("nan")] * 12, (None, 2), id="not-a-number"),
            pytest.param([0.0] + [None] * 11, (None, 1), id="one-valid-zero"),
            pytest.param([0.0, -1.0, None], (None, 1), id="negative-not-valid"),
            pytest.param([None] * 3 + [0.0] * 9, (None, 2), id="old-zeros-only"),
        ],
    )
    def test_nowcast_insufficient_zero_or_invalid_data(
        self, sensor_type, hourly_data, expected
    ):
        """Missing or invalid hours must not become clean-air readings."""
        assert calculate_nowcast(sensor_type, hourly_data) == expected

    @pytest.mark.parametrize(
        "sensor_type", [SensorDeviceClass.PM25, SensorDeviceClass.PM10]
    )
    def test_nowcast_mixed_zero_positive_and_missing(self, sensor_type):
        """Missing hours retain their age; valid zeros contribute to the denominator."""
        hourly_data = [0.0, None, 100.0, -1.0] + [None] * 8
        with patch(
            "custom_components.air_quality_metrics.metrics.epa.nowcast.calculate_aqi",
            return_value=42,
        ) as mock_calculate_aqi:
            assert calculate_nowcast(sensor_type, hourly_data) == (42, 0)
        # Weight 0.5: (0 * 1 + 100 * 0.25) / (1 + 0.25) = 20.
        mock_calculate_aqi.assert_called_once_with(20.0, AQI_CONFIGS[sensor_type])

    def test_nowcast_insufficient_recent_data(self):
        """Total data is plentiful, but missing in the latest 3-hour window."""
        # Only 1 valid data point in the first 3 elements. Fails NowCast criteria.
        incomplete_data = [12.0, None, None] + ([15.0] * 9)

        with patch(
            "custom_components.air_quality_metrics.metrics.epa.nowcast.estimate_hours_until_valid"
        ) as mock_estimate:
            mock_estimate.return_value = 1
            aqi, hours_remaining = calculate_nowcast(
                SensorDeviceClass.PM25, incomplete_data, "Test Site"
            )

            assert aqi is None
            assert hours_remaining == 1
            mock_estimate.assert_called_once_with(
                window_size=3, require_valid=2, hourly_data=incomplete_data
            )

    @patch("custom_components.air_quality_metrics.metrics.epa.nowcast.calculate_aqi")
    def test_nowcast_stable_data_weighting(self, mock_calculate_aqi):
        """Stable data produces a weight factor of 1.0 (unweighted average)."""
        stable_hourly_data = [10.0] * 12
        mock_calculate_aqi.return_value = 50

        aqi, hours_remaining = calculate_nowcast(
            SensorDeviceClass.PM25, stable_hourly_data, "Test Site"
        )

        assert aqi == 50
        assert hours_remaining == 0
        # With a weight factor of 1.0, the target weighted value passed to calculate_aqi should be exactly 10.0
        mock_calculate_aqi.assert_called_once_with(
            10.0, AQI_CONFIGS.get(SensorDeviceClass.PM25)
        )

    @patch("custom_components.air_quality_metrics.metrics.epa.nowcast.calculate_aqi")
    def test_nowcast_volatile_data_weighting(
        self,
        mock_calculate_aqi,
    ):
        """Volatile data clamps the weight factor to 0.5, heavily favoring the first hour."""
        volatile_hourly_data = [100.0, 10.0, None] + [50.0] * 9
        mock_calculate_aqi.return_value = 85

        aqi, hours_remaining = calculate_nowcast(
            SensorDeviceClass.PM25, volatile_hourly_data, "Test Site"
        )

        assert aqi == 85
        assert hours_remaining == 0

        # Verify the mathematical progression loop manually (notice that None in 3rd place):
        # weight_factor = 0.5
        # data_sum = 100+.5^0 + 10*.5^1 + 0*.5^2 + 50*.5^3 + 50*.5^4 + 50*.5^5 + 50*.5^6 + 50*.5^7 + 50*.5^8 + 50*.5^9 + 50*.5^10 + 50*.5^11 = 118.4755859
        # weight_sum = .5^0 + .5^1 + 0*.5^2 + .5^3 + .5^4 + .5^5 + .5^6 + .5^7 + .5^8 + .5^9 + .5^10 + .5^11 = 1.749511719
        # Expected weighted_value combination resolves near ~67.72
        args, _ = mock_calculate_aqi.call_args
        assert pytest.approx(args[0], 0.01) == 67.72

    @patch("custom_components.air_quality_metrics.metrics.epa.nowcast.calculate_aqi")
    def test_nowcast_skips_invalid_and_negative_values(self, mock_calculate_aqi):
        """Ensure None, 0, and negative numbers are ignored during processing loops."""
        # Elements 0 and 2 are truthy and > 0 (latest 3 hours count = 2)
        # Negative numbers and zeros should be dropped by extract_valid_values
        dirty_data = [20.0, None, 10.0, -5.0, 0.0, 15.0] + [None] * 6
        mock_calculate_aqi.return_value = 30

        aqi, hours_remaining = calculate_nowcast(
            SensorDeviceClass.PM25, dirty_data, "Test Site"
        )

        assert aqi == 30
        assert hours_remaining == 0

        # Ensure call was executed using only processed valid values
        assert mock_calculate_aqi.called
