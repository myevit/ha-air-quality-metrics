"""Canadian config flow is explicit and rejects misleading source mappings."""

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.air_quality_metrics.config_flow import (
    AirQualityMetricsConfigFlow,
    AirQualityMetricsOptionsFlowHandler,
)

PROFILE = "outdoor_canadian_smoke"


async def test_profile_selector(hass):
    flow = AirQualityMetricsConfigFlow()
    flow.hass = hass
    result = await flow.async_step_user()
    selector = next(iter(result["data_schema"].schema.values()))
    assert PROFILE in selector.config["options"]


@pytest.mark.parametrize(
    ("entities", "attrs", "error"),
    [
        (["sensor.pm"], {"device_class": "pm25", "unit_of_measurement": "μg/m³"}, None),
        (
            ["sensor.pm"],
            {"device_class": "pm25", "unit_of_measurement": "\u00b5g/m³"},
            None,
        ),
        (
            ["sensor.pm", "sensor.other"],
            {"device_class": "pm25", "unit_of_measurement": "μg/m³"},
            "canadian_pm25_source",
        ),
        (
            ["sensor.pm"],
            {"device_class": "pm10", "unit_of_measurement": "μg/m³"},
            "canadian_pm25_source",
        ),
        (
            ["sensor.pm"],
            {"device_class": "pm25", "unit_of_measurement": "ppm"},
            "canadian_pm25_source",
        ),
        (["sensor.pm"], {}, "canadian_pm25_source"),
    ],
)
async def test_canadian_source_validation(hass, entities, attrs, error):
    for entity in entities:
        hass.states.async_set(entity, "0", attrs)
    flow = AirQualityMetricsConfigFlow()
    flow.hass = hass
    flow.profile_type = PROFILE
    result = await flow.async_step_sensors({"sensors": entities, "scan_interval": 5})
    if error:
        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": error}
    else:
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["profile"] == PROFILE
        assert "Canadian" in result["title"]


async def test_options_reject_pm10(hass):
    entry = MockConfigEntry(domain="air_quality_metrics", data={"profile": PROFILE})
    entry.add_to_hass(hass)
    flow = AirQualityMetricsOptionsFlowHandler(entry)
    flow.hass = hass
    flow.handler = entry.entry_id
    hass.states.async_set(
        "sensor.pm10", "0", {"device_class": "pm10", "unit_of_measurement": "μg/m³"}
    )
    result = await flow.async_step_init(
        {"sensors": ["sensor.pm10"], "scan_interval": 5}
    )
    assert result["errors"] == {"base": "canadian_pm25_source"}
