"""Select platform for Lumagen integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from lumagen.constants import DeviceStatus

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LumagenCoordinator, LumagenData

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LumagenSelectEntityDescription(SelectEntityDescription):
    """Describes Lumagen select entity."""

    current_option_fn: Callable[[LumagenData], str | None]
    select_option_fn: Callable[[LumagenCoordinator, str], Any]
    options_fn: Callable[[LumagenCoordinator], list[str]] | None = None
    static_options: list[str] | None = None


# Aspect ratio mapping to pylumagen methods
ASPECT_RATIO_MAP = {
    "4:3": "source_aspect_4x3",
    "16:9": "source_aspect_16x9",
    "1.85": "source_aspect_1_85",
    "1.90": "source_aspect_1_90",
    "2.00": "source_aspect_2_00",
    "2.20": "source_aspect_2_20",
    "2.35": "source_aspect_2_35",
    "2.40": "source_aspect_2_40",
    "Letterbox": "source_aspect_lbox",
    "NLS": "nls",
}


async def _select_input_source(coordinator: LumagenCoordinator, option: str) -> None:
    """Select input source."""
    # Get source list and find the input number for the selected label
    source_list = coordinator.device_manager.source_list
    
    # Find the input number (index) that matches the label
    try:
        # source_list is 0-indexed, but Lumagen expects 1-indexed inputs
        input_index = source_list.index(option) + 1
        _LOGGER.debug("Selecting input %d (%s)", input_index, option)
    except ValueError:
        _LOGGER.error("Could not find input number for label: %s", option)
        return
    
    # Send input selection command
    await coordinator.device_manager.executor.input(input_index)


async def _select_aspect_ratio(coordinator: LumagenCoordinator, option: str) -> None:
    """Select source aspect ratio."""
    method_name = ASPECT_RATIO_MAP.get(option)
    if method_name is None:
        _LOGGER.error("Unknown aspect ratio: %s", option)
        return
    
    _LOGGER.debug("Setting aspect ratio to %s using method %s", option, method_name)
    # Get the method directly from executor and call it
    method = getattr(coordinator.device_manager.executor, method_name)
    await method()


async def _select_input_config(coordinator: LumagenCoordinator, option: str) -> None:
    """Select memory bank (A, B, C, D)."""
    # Map option to memory bank method
    memory_methods = {
        "A": coordinator.device_manager.executor.mema,
        "B": coordinator.device_manager.executor.memb,
        "C": coordinator.device_manager.executor.memc,
        "D": coordinator.device_manager.executor.memd,
    }
    
    method = memory_methods.get(option)
    if method is None:
        _LOGGER.error("Unknown memory bank: %s", option)
        return
    
    _LOGGER.debug("Recalling memory bank %s", option)
    await method()


def _get_input_source_options(coordinator: LumagenCoordinator) -> list[str]:
    """Get input source options from device."""
    try:
        source_list = coordinator.device_manager.source_list
        # Ensure we have a valid list
        if source_list and isinstance(source_list, list) and len(source_list) > 0:
            return source_list
        # Return default input numbers if source list not available
        return [f"Input {i}" for i in range(8)]
    except Exception as err:
        _LOGGER.error("Error getting source list: %s", err)
        # Return default input numbers as fallback
        return [f"Input {i}" for i in range(8)]


def _get_current_input_source(data: LumagenData) -> str | None:
    """Get current input source label."""
    # The device_info contains the logical_input number
    # We need to map it back to the label
    # This will be handled by the entity's current_option property
    return None  # Will be overridden in entity


# Select entity descriptions
SELECT_ENTITIES: tuple[LumagenSelectEntityDescription, ...] = (
    LumagenSelectEntityDescription(
        key="input_source",
        name="Input Source",
        icon="mdi:video-input-hdmi",
        current_option_fn=_get_current_input_source,
        select_option_fn=_select_input_source,
        options_fn=_get_input_source_options,
    ),
    LumagenSelectEntityDescription(
        key="source_aspect_ratio",
        name="Source Aspect Ratio",
        icon="mdi:aspect-ratio",
        current_option_fn=lambda data: data.device_info.current_source_content_aspect,
        select_option_fn=_select_aspect_ratio,
        static_options=["4:3", "16:9", "1.85", "1.90", "2.00", "2.20", "2.35", "2.40", "Letterbox", "NLS"],
    ),
    LumagenSelectEntityDescription(
        key="memory_bank",
        name="Memory Bank",
        icon="mdi:memory",
        current_option_fn=lambda data: data.device_info.input_memory if data.device_info else None,
        select_option_fn=_select_input_config,
        static_options=["A", "B", "C", "D"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumagen select based on a config entry."""
    coordinator: LumagenCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    _LOGGER.debug("Setting up Lumagen select entities")
    
    # Create select entities
    entities = [
        LumagenSelectEntity(coordinator, description)
        for description in SELECT_ENTITIES
    ]
    
    async_add_entities(entities)


class LumagenSelectEntity(CoordinatorEntity[LumagenCoordinator], SelectEntity):
    """Base class for Lumagen select entities."""

    entity_description: LumagenSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LumagenCoordinator,
        description: LumagenSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

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
    def options(self) -> list[str]:
        """Return the list of available options."""
        # Use static options if defined
        if self.entity_description.static_options:
            return self.entity_description.static_options
        # Otherwise get dynamic options from the options function
        elif self.entity_description.options_fn:
            return self.entity_description.options_fn(self.coordinator)
        return []

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        # Select entities only available when device is active
        return (
            self.coordinator.data.is_connected
            and self.coordinator.data.device_status == DeviceStatus.ACTIVE
        )

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        # Special handling for input source
        if self.entity_description.key == "input_source":
            logical_input = self.coordinator.data.device_info.logical_input
            source_list = self.coordinator.device_manager.source_list
            if (
                logical_input is not None
                and isinstance(source_list, list)
                and 0 <= logical_input < len(source_list)
            ):
                return source_list[logical_input]
            return None
        
        # For other entities, use the value function
        return self.entity_description.current_option_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            _LOGGER.debug("Setting %s to %s", self.entity_description.key, option)
            await self.entity_description.select_option_fn(self.coordinator, option)
            _LOGGER.info("Successfully set %s to %s", self.entity_description.key, option)
        
        except Exception as err:
            _LOGGER.error("Failed to set %s to %s: %s", self.name, option, err, exc_info=True)
            raise
