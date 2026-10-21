"""Constants for the Air Quality Metrics integration."""

from typing import Final

from homeassistant.components.sensor import SensorDeviceClass

DOMAIN: Final = "air_quality_metrics"

# Component platforms
PLATFORMS: Final = ["sensor"]

# Configuration defaults
DEFAULT_SCAN_INTERVAL: Final = 5

# Device types allowed for the two types of metrics
# See https://www.home-assistant.io/integrations/sensor/
INDOOR_DEVICE_TYPES: Final = [
    SensorDeviceClass.CO.value,
    SensorDeviceClass.CO2.value,
    SensorDeviceClass.PM1.value,
    SensorDeviceClass.PM10.value,
    SensorDeviceClass.PM25.value,
    SensorDeviceClass.OZONE.value,
]
OUTDOOR_DEVICE_TYPES: Final = [
    SensorDeviceClass.CO.value,
    # TODO: SensorDeviceClass.OZONE.value,
    SensorDeviceClass.NITROGEN_DIOXIDE.value,
    SensorDeviceClass.PM10.value,
    SensorDeviceClass.PM25.value,
    SensorDeviceClass.SULPHUR_DIOXIDE.value,
]

# Configuration entry keys
CONF_PROFILE: Final = "profile"
CONF_PROFILE_INDOOR: Final = "indoor"
CONF_PROFILE_OUTDOOR: Final = "outdoor"
CONF_PROFILE_CANADIAN: Final = "outdoor_canadian_smoke"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_SENSORS: Final = "sensors"
