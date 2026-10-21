import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from custom_components.air_quality_metrics.const import (
    CONF_PROFILE,
    CONF_PROFILE_CANADIAN,
    CONF_PROFILE_INDOOR,
    CONF_PROFILE_OUTDOOR,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INDOOR_DEVICE_TYPES,
    OUTDOOR_DEVICE_TYPES,
)


def _valid_canadian_source(hass, entities):
    """One local PM2.5 source in canonical mass units, never relative NOx."""
    if len(entities) != 1:
        return False
    state = hass.states.get(entities[0])
    return (
        state is not None
        and state.attributes.get("device_class") == "pm25"
        and state.attributes.get("unit_of_measurement") in ("μg/m³", "\u00b5g/m³")
    )


# Reusable selector that forces a numeric box layout labeled with "minutes"
SCAN_INTERVAL_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=1,
        max=60,
        step=1,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="minutes",
    )
)


class AirQualityMetricsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multi-Profile AQI."""

    def __init__(self):
        """Initialize the flow."""
        self.profile_type = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Link the options flow setup to this config entry."""
        return AirQualityMetricsOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Step 1: Ask the user which type of metrics they want to set up."""
        if user_input is not None:
            self.profile_type = user_input.get(CONF_PROFILE)
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_PROFILE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            CONF_PROFILE_INDOOR,
                            CONF_PROFILE_OUTDOOR,
                            CONF_PROFILE_CANADIAN,
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key=CONF_PROFILE,
                    )
                )
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_sensors(self, user_input=None):
        """Dynamic UI capturing sensors based on the selected profile."""
        errors = {}

        if user_input is not None:
            sensor_selection = user_input.get(CONF_SENSORS, [])

            if not sensor_selection:
                errors["base"] = "no_sensors_selected"
            elif (
                self.profile_type == CONF_PROFILE_CANADIAN
                and not _valid_canadian_source(self.hass, sensor_selection)
            ):
                errors["base"] = "canadian_pm25_source"
            else:
                user_input[CONF_PROFILE] = self.profile_type
                # TODO: figure out how to make this title translatable
                title = (
                    "Indoor Air Quality"
                    if self.profile_type == CONF_PROFILE_INDOOR
                    else "Outdoor Air Quality"
                )
                if self.profile_type == CONF_PROFILE_CANADIAN:
                    title = "Canadian AQHI smoke / PM2.5"
                return self.async_create_entry(title=title, data=user_input)

        # Dynamically determine the device class filter list
        if self.profile_type == CONF_PROFILE_INDOOR:
            device_class_filter = INDOOR_DEVICE_TYPES
        elif self.profile_type == CONF_PROFILE_CANADIAN:
            device_class_filter = ["pm25"]
        else:
            device_class_filter = OUTDOOR_DEVICE_TYPES

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): SCAN_INTERVAL_SELECTOR,
                vol.Required(CONF_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor",
                        multiple=True,
                        filter=selector.EntityFilterSelectorConfig(
                            device_class=device_class_filter
                        ),
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="sensors", data_schema=schema, errors=errors
        )


class AirQualityMetricsOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the user reconfiguring this integration post-setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        profile = self.config_entry.data.get(CONF_PROFILE)

        if user_input is not None:
            sensor_selection = user_input.get(CONF_SENSORS, [])

            if not sensor_selection:
                errors["base"] = "no_sensors_selected"

            if profile == CONF_PROFILE_CANADIAN and not _valid_canadian_source(
                self.hass, sensor_selection
            ):
                errors["base"] = "canadian_pm25_source"
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Dynamic filter assignment based on profile type
        if profile == CONF_PROFILE_INDOOR:
            device_class_filter = INDOOR_DEVICE_TYPES
        elif profile == CONF_PROFILE_CANADIAN:
            device_class_filter = ["pm25"]
        else:
            device_class_filter = OUTDOOR_DEVICE_TYPES

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_sensors = self.config_entry.options.get(
            CONF_SENSORS, self.config_entry.data.get(CONF_SENSORS, [])
        )

        schema_dict = {
            vol.Required(
                CONF_SCAN_INTERVAL, default=current_interval
            ): SCAN_INTERVAL_SELECTOR,
            vol.Required(
                CONF_SENSORS, default=current_sensors
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    multiple=True,
                    filter=selector.EntityFilterSelectorConfig(
                        device_class=device_class_filter
                    ),
                )
            ),
        }

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema_dict), errors=errors
        )
