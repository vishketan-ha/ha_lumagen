"""Remote platform for Lumagen integration."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable
import logging
from typing import Any

from lumagen.constants import DeviceStatus

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LumagenCoordinator

_LOGGER = logging.getLogger(__name__)

# Command mapping for remote control
COMMAND_MAP = {
    # Navigation commands
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    # Menu control commands
    "menu": "menu",
    "enter": "enter",
    "exit": "exit",
    "back": "back",
    "home": "home",
    "ok": "ok",
    # Utility commands
    "info": "info",
    "alt": "alt",
    "clear": "clear",
    # Number pad commands
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumagen remote based on a config entry."""
    coordinator: LumagenCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    _LOGGER.debug("Setting up Lumagen remote")
    
    async_add_entities([LumagenRemoteEntity(coordinator)])


class LumagenRemoteEntity(CoordinatorEntity[LumagenCoordinator], RemoteEntity):
    """Remote entity for Lumagen device menu navigation."""

    _attr_has_entity_name = True
    _attr_name = "Remote"
    _attr_icon = "mdi:remote"

    def __init__(self, coordinator: LumagenCoordinator) -> None:
        """Initialize the remote entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_remote"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information about this Lumagen device."""
        device_info = self.coordinator.data.device_info
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry.entry_id)},
            "name": f"Lumagen {device_info.model_name if device_info else 'RadiancePro'}",
            "manufacturer": "Lumagen",
            "model": device_info.model_name if device_info else "RadiancePro",
            "sw_version": device_info.software_revision if device_info else None,
            "serial_number": device_info.serial_number if device_info else None,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Remote only available when device is active
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.is_connected
            and self.coordinator.data.device_status == DeviceStatus.ACTIVE
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        try:
            _LOGGER.info("Turning on Lumagen device via remote")
            await self.coordinator.device_manager.executor.power_on()
            _LOGGER.debug("Power on command sent successfully")
        except Exception as err:
            _LOGGER.error("Failed to turn on device: %s", err, exc_info=True)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off (standby)."""
        try:
            _LOGGER.info("Turning off Lumagen device (standby) via remote")
            await self.coordinator.device_manager.executor.standby()
            _LOGGER.debug("Standby command sent successfully")
        except Exception as err:
            _LOGGER.error("Failed to turn off device: %s", err, exc_info=True)
            raise

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to the device."""
        # Check if device is in standby mode
        if self.coordinator.data.device_status != DeviceStatus.ACTIVE:
            _LOGGER.warning(
                "Cannot send remote commands while device is in standby mode. "
                "Device must be powered on first."
            )
            return

        try:
            command_list = list(command)
            _LOGGER.debug("Sending %d remote command(s): %s", len(command_list), command_list)
            
            for cmd in command_list:
                cmd_lower = cmd.lower()
                if cmd_lower in COMMAND_MAP:
                    method_name = COMMAND_MAP[cmd_lower]
                    method = getattr(
                        self.coordinator.device_manager.executor, method_name
                    )
                    _LOGGER.debug("Executing remote command: %s", cmd_lower)
                    await method()
                    # Small delay between commands
                    await asyncio.sleep(0.1)
                else:
                    _LOGGER.warning("Unknown remote command: %s (ignored)", cmd)
            
            _LOGGER.info("Successfully sent %d remote command(s)", len(command_list))

        except Exception as err:
            _LOGGER.error("Failed to send remote command: %s", err, exc_info=True)
            raise

