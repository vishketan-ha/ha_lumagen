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
        self._event_listeners = []  # Track registered listeners for cleanup
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """Subscribe to device state change events."""
        dispatcher = self.device_manager.dispatcher
        
        # Subscribe to all relevant state changes
        # Track each listener for cleanup
        # Use dedicated handler for device_status to handle power-on refresh
        power_handler = lambda _, ed: asyncio.create_task(self._handle_power_state_change(_, ed))
        dispatcher.register_listener("device_status", power_handler)
        self._event_listeners.append(("device_status", power_handler))
        
        input_labels_handler = self._create_event_handler("input_labels")
        dispatcher.register_listener("input_labels", input_labels_handler)
        self._event_listeners.append(("input_labels", input_labels_handler))
        
        physical_input_handler = self._create_event_handler("physical_input_selected")
        dispatcher.register_listener("physical_input_selected", physical_input_handler)
        self._event_listeners.append(("physical_input_selected", physical_input_handler))
        
        content_aspect_handler = self._create_event_handler("current_source_content_aspect")
        dispatcher.register_listener("current_source_content_aspect", content_aspect_handler)
        self._event_listeners.append(("current_source_content_aspect", content_aspect_handler))
        
        detected_aspect_handler = self._create_event_handler("detected_source_aspect")
        dispatcher.register_listener("detected_source_aspect", detected_aspect_handler)
        self._event_listeners.append(("detected_source_aspect", detected_aspect_handler))
        
        source_mode_handler = self._create_event_handler("source_mode")
        dispatcher.register_listener("source_mode", source_mode_handler)
        self._event_listeners.append(("source_mode", source_mode_handler))
        
        vertical_rate_handler = self._create_event_handler("source_vertical_rate")
        dispatcher.register_listener("source_vertical_rate", vertical_rate_handler)
        self._event_listeners.append(("source_vertical_rate", vertical_rate_handler))
        
        dynamic_range_handler = self._create_event_handler("source_dynamic_range")
        dispatcher.register_listener("source_dynamic_range", dynamic_range_handler)
        self._event_listeners.append(("source_dynamic_range", dynamic_range_handler))
        
        is_alive_handler = self._create_event_handler("is_alive")
        dispatcher.register_listener("is_alive", is_alive_handler)
        self._event_listeners.append(("is_alive", is_alive_handler))
        
        dispatcher.register_listener(EventType.CONNECTION_STATE, self._handle_connection_state)
        self._event_listeners.append((EventType.CONNECTION_STATE, self._handle_connection_state))
        
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

    async def _handle_power_state_change(self, _, event_data: dict) -> None:
        """Handle power state changes."""
        new_status = event_data.get("value")
        old_status = self.data.device_status if self.data else None
        
        _LOGGER.debug("Power state changed: %s -> %s", old_status, new_status)
        
        # If transitioning from Standby to Active, schedule a full refresh
        if old_status == DeviceStatus.STANDBY and new_status == DeviceStatus.ACTIVE:
            _LOGGER.info("Device powered on, scheduling full refresh in 5 seconds")
            asyncio.create_task(self._delayed_refresh_on_power_on())
        
        # Update coordinator data immediately
        new_data = LumagenData(
            device_info=self.device_manager.device_info,
            is_connected=self.device_manager.is_connected,
            is_alive=self.device_manager.is_alive,
            device_status=new_status,
        )
        self.async_set_updated_data(new_data)

    async def _delayed_refresh_on_power_on(self) -> None:
        """Refresh all sensor states 5 seconds after power on."""
        await asyncio.sleep(5)
        try:
            _LOGGER.debug("Executing full refresh after power on")
            await self.device_manager.executor.get_all()
            # get_all triggers events that will update all sensors
        except Exception as err:
            _LOGGER.error("Failed to refresh after power on: %s", err)

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

    def _cleanup_event_listeners(self) -> None:
        """Unregister all event listeners."""
        if not self.device_manager or not hasattr(self.device_manager, 'dispatcher'):
            return
        
        dispatcher = self.device_manager.dispatcher
        
        # Check if dispatcher has unregister method
        if not hasattr(dispatcher, 'unregister_listener'):
            _LOGGER.debug("Dispatcher does not support unregister_listener, skipping cleanup")
            return
        
        _LOGGER.debug("Unregistering %d event listeners", len(self._event_listeners))
        for event_type, handler in self._event_listeners:
            try:
                dispatcher.unregister_listener(event_type, handler)
            except Exception as err:
                _LOGGER.debug("Error unregistering listener for %s: %s", event_type, err)
        
        self._event_listeners.clear()
        _LOGGER.debug("Event listeners cleanup completed")

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and close device connection."""
        _LOGGER.info("Shutting down Lumagen coordinator")
        
        # Clean up event listeners first
        self._cleanup_event_listeners()
        
        if self.device_manager:
            try:
                _LOGGER.debug("Closing device connection")
                await self.device_manager.close()
                _LOGGER.info("Device connection closed successfully")
            except Exception as err:
                _LOGGER.error("Error closing device connection: %s", err, exc_info=True)
