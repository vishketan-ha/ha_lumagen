"""Data coordinator for Lumagen integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from lumagen import DeviceInfo
from lumagen.constants import DeviceStatus
from lumagen.device_manager import DeviceManager

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class LumagenData:
    """Data structure for Lumagen device state."""

    device_info: DeviceInfo
    is_connected: bool
    is_alive: bool
    device_status: DeviceStatus


class LumagenCoordinator(DataUpdateCoordinator[LumagenData]):
    """Coordinator for Lumagen device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        device_manager: DeviceManager,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.device_manager = device_manager
        self.entry = entry

    async def _async_update_data(self) -> LumagenData:
        """Fetch data from device."""
        # Check connection state
        is_connected = self.device_manager.is_connected
        is_alive = self.device_manager.is_alive
        device_status = self.device_manager.device_status
        
        # Log connection state changes
        if not is_connected and hasattr(self, '_last_connected') and self._last_connected:
            _LOGGER.warning("Device connection lost")
        elif is_connected and hasattr(self, '_last_connected') and not self._last_connected:
            _LOGGER.info("Device connection restored")
        
        # Store last connection state for change detection
        self._last_connected = is_connected
        
        # Return current state even if not connected (allows reconnection)
        if not is_connected:
            _LOGGER.debug("Device not connected, returning cached state")
            return LumagenData(
                device_info=self.device_manager.device_info,
                is_connected=False,
                is_alive=is_alive,
                device_status=device_status,
            )

        # Log device status changes
        if hasattr(self, '_last_status') and self._last_status != device_status:
            _LOGGER.info("Device status changed from %s to %s", self._last_status, device_status)
        self._last_status = device_status

        # Only refresh data when device is active
        if device_status == DeviceStatus.ACTIVE:
            try:
                _LOGGER.debug("Refreshing device data")
                await self.device_manager.executor.get_all()
            except Exception as err:
                _LOGGER.error("Error fetching device data: %s", err, exc_info=True)
                # Don't raise UpdateFailed, just return current state
                # This allows the integration to stay loaded during temporary issues
        else:
            _LOGGER.debug("Device in standby mode, skipping data refresh")

        return LumagenData(
            device_info=self.device_manager.device_info,
            is_connected=is_connected,
            is_alive=is_alive,
            device_status=device_status,
        )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close device connection."""
        _LOGGER.info("Shutting down Lumagen coordinator")
        if self.device_manager:
            try:
                _LOGGER.debug("Closing device connection")
                await self.device_manager.close()
                _LOGGER.info("Device connection closed successfully")
            except Exception as err:
                _LOGGER.error("Error closing device connection: %s", err, exc_info=True)
