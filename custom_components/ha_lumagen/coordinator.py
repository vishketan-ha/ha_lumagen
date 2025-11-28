"""Data coordinator for Lumagen integration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from lumagen import DeviceInfo
from lumagen.constants import DeviceStatus, EventType, ConnectionStatus
from lumagen.device_manager import DeviceManager

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class LumagenData:
    """Data structure for Lumagen device state."""

    device_info: DeviceInfo
    is_connected: bool
    is_alive: bool
    device_status: DeviceStatus


class LumagenCoordinator(DataUpdateCoordinator[LumagenData]):
    """Coordinator for Lumagen device with pure event-driven updates."""

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
            update_interval=None,  # No polling - pure event-driven architecture
        )
        self.device_manager = device_manager
        self.entry = entry
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Subscribe to device state change events."""
        dispatcher = self.device_manager.dispatcher
        
        # Subscribe to all relevant state changes
        dispatcher.register_listener(
            "device_status", 
            self._create_event_handler("device_status")
        )
        dispatcher.register_listener(
            "input_labels",
            self._create_event_handler("input_labels")
        )
        dispatcher.register_listener(
            "physical_input_selected",
            self._create_event_handler("physical_input_selected")
        )
        dispatcher.register_listener(
            "current_source_content_aspect",
            self._create_event_handler("current_source_content_aspect")
        )
        dispatcher.register_listener(
            "detected_source_aspect",
            self._create_event_handler("detected_source_aspect")
        )
        dispatcher.register_listener(
            "source_mode",
            self._create_event_handler("source_mode")
        )
        dispatcher.register_listener(
            "source_vertical_rate",
            self._create_event_handler("source_vertical_rate")
        )
        dispatcher.register_listener(
            "source_dynamic_range",
            self._create_event_handler("source_dynamic_range")
        )
        dispatcher.register_listener(
            "is_alive",
            self._create_event_handler("is_alive")
        )
        dispatcher.register_listener(
            EventType.CONNECTION_STATE,
            self._handle_connection_state
        )
        
        _LOGGER.debug("Event listeners registered for pure event-driven updates")

    def _create_event_handler(self, attr_name: str):
        """Create an event handler for a specific attribute."""
        async def handler(event_data: dict):
            await self._on_device_event(attr_name, event_data)
        return lambda _, ed: asyncio.create_task(handler(ed))

    async def _on_device_event(self, attr_name: str, event_data: dict) -> None:
        """Handle device state change event."""
        value = event_data.get("value")
        _LOGGER.debug("Received event: %s = %s", attr_name, value)
        
        # Update coordinator data immediately
        new_data = LumagenData(
            device_info=self.device_manager.device_info,
            is_connected=self.device_manager.is_connected,
            is_alive=self.device_manager.is_alive,
            device_status=self.device_manager.device_status,
        )
        
        # Notify all entities of the update
        self.async_set_updated_data(new_data)

    async def _handle_connection_state(self, _, event_data: dict) -> None:
        """Handle connection state changes."""
        state = event_data.get("state")
        _LOGGER.info("Connection state changed: %s", state)
        
        if state == ConnectionStatus.CONNECTED:
            # Fetch input labels once after connection
            await asyncio.sleep(1)
            _LOGGER.debug("Fetching labels after connection...")
            try:
                await self.device_manager.executor.get_labels(get_all=False)
                _LOGGER.debug("Labels fetched successfully")
            except Exception as err:
                _LOGGER.error("Error fetching labels: %s", err, exc_info=True)
        
        # Update coordinator data
        new_data = LumagenData(
            device_info=self.device_manager.device_info,
            is_connected=self.device_manager.is_connected,
            is_alive=self.device_manager.is_alive,
            device_status=self.device_manager.device_status,
        )
        self.async_set_updated_data(new_data)

    async def _async_update_data(self) -> LumagenData:
        """
        Return current state without polling.
        
        This method is required by DataUpdateCoordinator but not used
        since update_interval is None. All updates come from events.
        """
        return LumagenData(
            device_info=self.device_manager.device_info,
            is_connected=self.device_manager.is_connected,
            is_alive=self.device_manager.is_alive,
            device_status=self.device_manager.device_status,
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
