"""Sensor platform for Lumagen integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from lumagen.constants import DeviceStatus

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LumagenCoordinator, LumagenData

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class LumagenSensorEntityDescription(SensorEntityDescription):
    """Describes Lumagen sensor entity."""

    value_fn: Callable[[LumagenData], Any]


def _format_output_resolution(data: LumagenData) -> str | None:
    """Format output resolution as a string."""
    device_info = data.device_info
    if device_info is None:
        return None
    return (
        f"{device_info.output_horizontal_resolution}x"
        f"{device_info.output_vertical_resolution}@"
        f"{device_info.output_vertical_rate}Hz"
    )


# Status sensor descriptions
STATUS_SENSORS: tuple[LumagenSensorEntityDescription, ...] = (
    LumagenSensorEntityDescription(
        key="logical_input",
        name="Logical Input",
        icon="mdi:video-input-hdmi",
        value_fn=lambda data: data.device_info.logical_input if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="physical_input",
        name="Physical Input",
        icon="mdi:video-input-component",
        value_fn=lambda data: data.device_info.physical_input if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="output_resolution",
        name="Output Resolution",
        icon="mdi:monitor",
        value_fn=_format_output_resolution,
    ),
    LumagenSensorEntityDescription(
        key="source_aspect_ratio",
        name="Source Aspect Ratio",
        icon="mdi:aspect-ratio",
        value_fn=lambda data: data.device_info.current_source_content_aspect if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="source_dynamic_range",
        name="Source Dynamic Range",
        icon="mdi:brightness-7",
        value_fn=lambda data: data.device_info.source_dynamic_range if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="input_configuration",
        name="Input Configuration",
        icon="mdi:cog",
        value_fn=lambda data: data.device_info.active_input_config_number if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="output_cms",
        name="Output CMS",
        icon="mdi:palette",
        value_fn=lambda data: data.device_info.active_output_cms if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="output_style",
        name="Output Style",
        icon="mdi:image-filter-hdr",
        value_fn=lambda data: data.device_info.active_output_style if data.device_info else None,
    ),
)

# Diagnostic sensor descriptions
DIAGNOSTIC_SENSORS: tuple[LumagenSensorEntityDescription, ...] = (
    LumagenSensorEntityDescription(
        key="model_name",
        name="Model Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.model_name if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="software_revision",
        name="Software Revision",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.software_revision if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="model_number",
        name="Model Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.model_number if data.device_info else None,
    ),
    LumagenSensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.serial_number if data.device_info else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumagen sensor based on a config entry."""
    coordinator: LumagenCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    _LOGGER.debug("Setting up Lumagen sensors")
    
    # Create status sensor entities
    entities = [
        LumagenSensorEntity(coordinator, description)
        for description in STATUS_SENSORS
    ]
    
    # Create diagnostic sensor entities
    entities.extend([
        LumagenSensorEntity(coordinator, description)
        for description in DIAGNOSTIC_SENSORS
    ])
    
    async_add_entities(entities)


class LumagenSensorEntity(CoordinatorEntity[LumagenCoordinator], SensorEntity):
    """Base class for Lumagen sensor entities."""

    entity_description: LumagenSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LumagenCoordinator,
        description: LumagenSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False
        
        # Diagnostic sensors always available if connected
        if self.entity_description.entity_category == EntityCategory.DIAGNOSTIC:
            return self.coordinator.data.is_connected
        
        # Status sensors only available when device is active
        return (
            self.coordinator.data.is_connected
            and self.coordinator.data.device_status == DeviceStatus.ACTIVE
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
