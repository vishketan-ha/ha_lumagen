"""Switch platform for Lumagen integration."""
from __future__ import annotations

import logging
from typing import Any

from lumagen.constants import DeviceStatus

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LumagenCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumagen switch based on a config entry."""
    coordinator: LumagenCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    _LOGGER.debug("Setting up Lumagen power switch")
    
    async_add_entities([LumagenPowerSwitch(coordinator)])


class LumagenPowerSwitch(CoordinatorEntity[LumagenCoordinator], SwitchEntity):
    """Representation of a Lumagen power switch."""

    _attr_has_entity_name = True
    _attr_name = "Power"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: LumagenCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_power"
        self._optimistic_state: bool | None = None

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
        # Power switch available when connected (even in standby)
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.is_connected
        )

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""
        # Use optimistic state if set, otherwise use actual state
        if self._optimistic_state is not None:
            return self._optimistic_state
        return self.coordinator.data.device_status == DeviceStatus.ACTIVE
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear optimistic state once we get an update
        self._optimistic_state = None
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        try:
            _LOGGER.info("Turning on Lumagen device")
            await self.coordinator.device_manager.executor.power_on()
            # Set optimistic state
            self._optimistic_state = True
            self.async_write_ha_state()
            _LOGGER.debug("Power on command sent successfully")
        except Exception as err:
            self._optimistic_state = None
            _LOGGER.error("Failed to turn on device: %s", err, exc_info=True)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off (standby)."""
        try:
            _LOGGER.info("Turning off Lumagen device (standby)")
            await self.coordinator.device_manager.executor.standby()
            # Set optimistic state
            self._optimistic_state = False
            self.async_write_ha_state()
            _LOGGER.debug("Standby command sent successfully")
        except Exception as err:
            self._optimistic_state = None
            _LOGGER.error("Failed to turn off device: %s", err, exc_info=True)
            raise

