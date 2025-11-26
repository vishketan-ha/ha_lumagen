"""The Lumagen integration."""
from __future__ import annotations

import logging

from lumagen.device_manager import DeviceManager

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_IP,
    CONNECTION_TYPE_SERIAL,
    DEFAULT_BAUDRATE,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import LumagenCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT, Platform.SWITCH, Platform.REMOTE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Lumagen from a config entry."""
    _LOGGER.info("Setting up Lumagen integration for entry %s", entry.entry_id)
    
    # Initialize device manager
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_IP)
    device_manager = DeviceManager(connection_type=connection_type, reconnect=True)
    
    # Open connection based on type
    try:
        if connection_type == CONNECTION_TYPE_IP:
            host = entry.data[CONF_HOST]
            port = entry.data.get(CONF_PORT, DEFAULT_PORT)
            _LOGGER.debug("Opening IP connection to %s:%s", host, port)
            await device_manager.open(host=host, port=port)
        else:  # serial
            port = entry.data[CONF_PORT]
            baudrate = entry.data.get("baudrate", DEFAULT_BAUDRATE)
            _LOGGER.debug("Opening serial connection to %s at %s baud", port, baudrate)
            await device_manager.open(port=port, baudrate=baudrate)
        
        # Wait for connection to be established
        import asyncio
        await asyncio.sleep(2)
        
        if not device_manager.is_connected:
            _LOGGER.error("Device connection not established after initial setup")
            raise ConfigEntryNotReady("Device connection not established")
        
        _LOGGER.info("Successfully connected to Lumagen device")
            
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.error("Failed to connect to Lumagen device: %s", err, exc_info=True)
        raise ConfigEntryNotReady(f"Failed to connect: {err}") from err
    
    # Create coordinator
    _LOGGER.debug("Creating data coordinator")
    coordinator = LumagenCoordinator(hass, entry, device_manager)
    
    # Fetch initial data
    _LOGGER.debug("Fetching initial device data")
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Forward setup to platforms
    _LOGGER.debug("Setting up platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("Lumagen integration setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Lumagen integration for entry %s", entry.entry_id)
    
    # Unload platforms
    _LOGGER.debug("Unloading platforms: %s", PLATFORMS)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Shutdown coordinator and close connection
        coordinator: LumagenCoordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.debug("Shutting down coordinator and closing device connection")
        await coordinator.async_shutdown()
        
        # Remove from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Lumagen integration unloaded successfully")
    else:
        _LOGGER.error("Failed to unload Lumagen integration platforms")
    
    return unload_ok
