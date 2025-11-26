"""Config flow for Lumagen integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from lumagen.device_manager import DeviceManager

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_IP,
    CONNECTION_TYPE_SERIAL,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DOMAIN,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_CONFIG,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

# Subtask 2.1: Connection type selection schema
STEP_CONNECTION_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONNECTION_TYPE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=CONNECTION_TYPE_IP,
                        label="IP Connection (Network)",
                    ),
                    selector.SelectOptionDict(
                        value=CONNECTION_TYPE_SERIAL,
                        label="Serial Connection (RS232)",
                    ),
                ],
                mode=selector.SelectSelectorMode.LIST,
            )
        ),
    }
)

# Subtask 2.2: IP connection configuration schema
STEP_IP_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
)

# Subtask 2.3: Serial connection configuration schema
STEP_SERIAL_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("port"): str,
        vol.Required("baudrate", default=DEFAULT_BAUDRATE): vol.All(
            vol.Coerce(int), vol.In([9600, 19200, 38400, 57600, 115200])
        ),
    }
)


class LumagenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumagen."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._connection_type: str | None = None
        self._config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - connection type selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Store connection type and proceed to appropriate step
            self._connection_type = user_input[CONF_CONNECTION_TYPE]
            
            if self._connection_type == CONNECTION_TYPE_IP:
                return await self.async_step_ip()
            else:
                return await self.async_step_serial()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_CONNECTION_TYPE_SCHEMA,
            errors=errors,
        )

    async def async_step_ip(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle IP connection configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate IP connection
            self._config_data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_IP,
                CONF_HOST: user_input[CONF_HOST],
                CONF_PORT: user_input[CONF_PORT],
            }
            
            # Subtask 2.4: Test connection
            result = await self._test_connection()
            if result is True:
                # Create unique ID based on connection info
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Lumagen ({user_input[CONF_HOST]})",
                    data=self._config_data,
                )
            else:
                errors["base"] = result

        return self.async_show_form(
            step_id="ip",
            data_schema=STEP_IP_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle serial connection configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate serial connection
            self._config_data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_SERIAL,
                "port": user_input["port"],
                "baudrate": user_input["baudrate"],
            }
            
            # Subtask 2.4: Test connection
            result = await self._test_connection()
            if result is True:
                # Create unique ID based on connection info
                await self.async_set_unique_id(
                    f"{user_input['port']}_{user_input['baudrate']}"
                )
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Lumagen ({user_input['port']})",
                    data=self._config_data,
                )
            else:
                errors["base"] = result

        return self.async_show_form(
            step_id="serial",
            data_schema=STEP_SERIAL_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self) -> str | bool:
        """Test connection to Lumagen device.
        
        Returns:
            True if connection successful, error string otherwise.
        """
        device = None
        connection_type = self._config_data[CONF_CONNECTION_TYPE]
        
        try:
            _LOGGER.debug("Testing %s connection to Lumagen device", connection_type)
            
            # Create DeviceManager with reconnect disabled for testing
            device = DeviceManager(
                connection_type=connection_type,
                reconnect=False,
            )
            
            # Attempt to open connection based on type
            if connection_type == CONNECTION_TYPE_IP:
                host = self._config_data[CONF_HOST]
                port = self._config_data[CONF_PORT]
                _LOGGER.debug("Attempting IP connection to %s:%s", host, port)
                await device.open(host=host, port=port)
            else:  # Serial
                port = self._config_data["port"]
                baudrate = self._config_data["baudrate"]
                _LOGGER.debug("Attempting serial connection to %s at %s baud", port, baudrate)
                await device.open(port=port, baudrate=baudrate)
            
            # Wait for device to respond and complete alive check
            # Give extra time for the alive check to complete
            _LOGGER.debug("Waiting for device to respond...")
            await asyncio.sleep(5)
            
            # Check if connection is established and device is alive
            if not device.is_connected:
                _LOGGER.error(
                    "Device connection failed: is_connected=%s, is_alive=%s",
                    device.is_connected,
                    device.is_alive,
                )
                return ERROR_CANNOT_CONNECT
            
            # Log warning if alive check hasn't completed but connection is established
            if not device.is_alive:
                _LOGGER.warning(
                    "Device connected but alive check incomplete: is_connected=%s, is_alive=%s",
                    device.is_connected,
                    device.is_alive,
                )
                # Still allow connection if device is connected
                # The alive check may complete after initial setup
            
            _LOGGER.info("Successfully validated connection to Lumagen device")
            return True
            
        except Exception as err:
            _LOGGER.error("Error testing connection: %s", err, exc_info=True)
            return ERROR_CANNOT_CONNECT
            
        finally:
            # Always close the test connection
            if device is not None:
                try:
                    _LOGGER.debug("Closing test connection")
                    await device.close()
                except Exception as err:
                    _LOGGER.debug("Error closing test connection: %s", err)
