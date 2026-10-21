"""Sensor platform for the Air Quality integration."""

import logging

from homeassistant.core import HomeAssistant

from custom_components.air_quality_metrics.const import (
    CONF_PROFILE_CANADIAN,
    CONF_PROFILE_INDOOR,
    CONF_PROFILE_OUTDOOR,
)
from custom_components.air_quality_metrics.sensors.canadian import (
    CanadianDataCoordinator,
    CanadianSmokeCategorySensor,
    CanadianSmokeSensor,
)
from custom_components.air_quality_metrics.sensors.indoor.coordinator import (
    IndoorDataCoordinator,
)
from custom_components.air_quality_metrics.sensors.indoor.iaqi import (
    IAQICategorySensor,
    IAQIColorSensor,
    IAQIPrimaryPollutantSensor,
    IAQISensor,
)
from custom_components.air_quality_metrics.sensors.outdoor.coordinator import (
    OutdoorDataCoordinator,
)
from custom_components.air_quality_metrics.sensors.outdoor.daily import (
    DailyAQISensor,
    DailyCategorySensor,
    DailyColorAssistSensor,
    DailyColorNameSensor,
    DailyColorSensor,
    DailyPrimaryPollutantSensor,
    DailyStatusSensor,
)
from custom_components.air_quality_metrics.sensors.outdoor.nowcast import (
    NowCastAQISensor,
    NowCastCategorySensor,
    NowCastColorAssistSensor,
    NowCastColorNameSensor,
    NowCastColorSensor,
    NowCastPrimaryPollutantSensor,
    NowCastStatusSensor,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up the sensors based on the selected profile."""
    profile = entry.data.get("profile")
    _LOGGER.debug(
        "[%s] Starting sensor platform setup for profile: %s", entry.title, profile
    )
    entities = []

    if profile == CONF_PROFILE_INDOOR:
        coordinator = IndoorDataCoordinator(hass, entry)
        _LOGGER.debug("[%s] Triggering coordinator initial first refresh", entry.title)
        await coordinator.async_config_entry_first_refresh()
        entities.extend(
            [
                IAQISensor(coordinator, entry),
                IAQIPrimaryPollutantSensor(coordinator, entry),
                IAQICategorySensor(coordinator, entry),
                IAQIColorSensor(coordinator, entry),
            ]
        )

    elif profile == CONF_PROFILE_CANADIAN:
        coordinator = CanadianDataCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        entities.extend(
            [
                CanadianSmokeSensor(coordinator, entry),
                CanadianSmokeCategorySensor(coordinator, entry),
            ]
        )

    elif profile == CONF_PROFILE_OUTDOOR:
        coordinator = OutdoorDataCoordinator(hass, entry)
        _LOGGER.debug("[%s] Triggering coordinator initial first refresh", entry.title)
        await coordinator.async_config_entry_first_refresh()

        entities.extend(
            [
                DailyAQISensor(coordinator, entry),
                DailyPrimaryPollutantSensor(coordinator, entry),
                DailyCategorySensor(coordinator, entry),
                DailyColorSensor(coordinator, entry),
                DailyColorAssistSensor(coordinator, entry),
                DailyColorNameSensor(coordinator, entry),
                DailyStatusSensor(coordinator, entry),
                NowCastAQISensor(coordinator, entry),
                NowCastCategorySensor(coordinator, entry),
                NowCastColorSensor(coordinator, entry),
                NowCastColorAssistSensor(coordinator, entry),
                NowCastColorNameSensor(coordinator, entry),
                NowCastPrimaryPollutantSensor(coordinator, entry),
                NowCastStatusSensor(coordinator, entry),
            ]
        )

    _LOGGER.debug(
        "[%s] Registering %s entities to Home Assistant", entry.title, len(entities)
    )
    async_add_entities(entities, False)
