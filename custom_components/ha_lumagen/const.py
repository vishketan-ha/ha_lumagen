"""Constants for the Lumagen integration."""
from homeassistant.exceptions import HomeAssistantError

DOMAIN = "ha_lumagen"

# Connection defaults
DEFAULT_PORT = 4999
DEFAULT_BAUDRATE = 9600

# Pure event-driven architecture - no polling
# All updates come from pylumagen dispatcher events
# No DEFAULT_SCAN_INTERVAL needed

# Connection types
CONF_CONNECTION_TYPE = "connection_type"
CONNECTION_TYPE_IP = "ip"
CONNECTION_TYPE_SERIAL = "serial"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_CONFIG = "invalid_config"
ERROR_UNKNOWN = "unknown"


# Custom exception classes
class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the device."""


class InvalidConfig(HomeAssistantError):
    """Error to indicate the configuration is invalid."""
