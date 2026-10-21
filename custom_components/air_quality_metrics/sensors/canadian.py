"""Local Canadian AQHI smoke component; not complete regional AQHI/AQHI-Plus."""

import logging
from datetime import timedelta
from functools import partial
from typing import cast

from homeassistant.components.recorder import get_instance, history
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import State
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from ..const import CONF_SCAN_INTERVAL, CONF_SENSORS, DEFAULT_SCAN_INTERVAL, DOMAIN
from ..metrics.canadian import hour_mean, pm25_value, smoke_category, smoke_index

_LOGGER = logging.getLogger(__name__)


class CanadianDataCoordinator(DataUpdateCoordinator):
    """Read complete held-state hours without dropping invalid intervals."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name="Canadian AQHI smoke / PM2.5",
            config_entry=entry,
            update_interval=timedelta(
                minutes=entry.options.get(
                    CONF_SCAN_INTERVAL,
                    entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                )
            ),
        )
        self.source = entry.options.get(CONF_SENSORS, entry.data.get(CONF_SENSORS, []))

    async def _async_update_data(self):
        now = dt_util.utcnow()
        end = now.replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=1)
        result = {
            "index": None,
            "category": None,
            "pm25_mean": None,
            "coverage": 0.0,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "status": "source_invalid",
            # Explicit frontend contract: unchanged reports are not transported
            # as last_reported by HA's normal websocket entity subscription.
            "evaluated_at": now.isoformat(),
            "source_last_reported": None,
        }
        if len(self.source) != 1:
            return result
        current = self.hass.states.get(self.source[0])
        if current is not None:
            result["source_last_reported"] = current.last_reported.isoformat()
        if current is None or pm25_value(current) is None:
            return result
        age = now - current.last_reported
        if age < timedelta(0) or age > timedelta(minutes=15):
            result["status"] = "source_stale"
            return result
        try:
            records = await get_instance(self.hass).async_add_executor_job(
                partial(
                    history.get_significant_states,
                    self.hass,
                    # Recorder excludes transitions exactly at its query start.
                    # Seed just before it; hour_mean still clamps to [start, end).
                    start - timedelta(microseconds=1),
                    end,
                    self.source,
                    include_start_time_state=True,
                    significant_changes_only=False,
                    minimal_response=False,
                    no_attributes=False,
                )
            )
        except Exception:
            # Do not retain a prior low (or high) value after a failed read.
            _LOGGER.warning("Canadian AQHI smoke history unavailable")
            result["status"] = "history_unavailable"
            return result
        mean, coverage = hour_mean(
            cast(list[State], records.get(self.source[0], [])), start, end
        )
        index = smoke_index(mean)
        result.update(
            index=index,
            category=smoke_category(index),
            # Only the diagnostic attribute is converted for HA serialization;
            # the index above uses the exact weighted mean.
            pm25_mean=float(mean) if mean is not None else None,
            coverage=coverage,
            status="valid" if index is not None else "incomplete_history",
        )
        return result


class CanadianSmokeSensor(CoordinatorEntity[CanadianDataCoordinator], SensorEntity):
    """Dimensionless Canadian PM2.5-only estimate with explicit limitations."""

    _attr_has_entity_name = True
    _attr_translation_key = "aqhi_smoke_pm25"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_translation_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title
        )

    @property
    def native_value(self):
        return self.coordinator.data["index"]

    @property
    def extra_state_attributes(self):
        index = self.coordinator.data["index"]
        return {
            **self.coordinator.data,
            "index_type": "canadian_aqhi_smoke_pm25",
            "scope": "local_pm25_only_estimate",
            "source_entity": self.coordinator.source[0],
            "method": "BCCDC May 2024 PM2.5 component; ceil(hour_mean/10)",
            "averaging": "previous_complete_utc_hour_time_weighted",
            "mean_unit": "μg/m³",
            "coverage_required": 1.0,
            "source_max_age_minutes": 15,
            "display_value": "10+"
            if index == 11
            else str(index)
            if index is not None
            else None,
            "limitations": "Not full three-pollutant or official community AQHI; no safety determination",
        }


class CanadianSmokeCategorySensor(CanadianSmokeSensor):
    """Canadian categories, independent of US AQI classifications."""

    _attr_translation_key = "aqhi_smoke_category"
    _attr_state_class = None
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["low", "moderate", "high", "very_high"]
    _attr_icon = "mdi:label-outline"

    @property
    def native_value(self):
        return self.coordinator.data["category"]
