# Lumagen Radiance Pro Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Home Assistant integration for Lumagen Radiance Pro video processors. Control and monitor your Lumagen device directly from Home Assistant.

## Features

- **Power Control** - Turn your Lumagen on/off or put it in standby mode
- **Input Selection** - Switch between configured input sources
- **Aspect Ratio Control** - Change source aspect ratio settings
- **Input Configuration** - Recall saved input configurations
- **Remote Control** - Send menu navigation commands
- **Status Monitoring** - View current input, output resolution, and device information
- **Automatic Reconnection** - Handles connection loss and recovery gracefully
- **Standby Mode Support** - Proper handling of device standby state

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ha_lumagen` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

- Lumagen Radiance Pro device
- Network connection (IP) or Serial connection to the device
- [pylumagen](https://github.com/johncarey70/pylumagen) library (automatically installed)

### Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Lumagen"
4. Select your connection type:
   - **IP Connection**: Enter hostname/IP and port (default: 4999)
   - **Serial Connection**: Enter serial port path and baud rate (default: 9600)
5. Click **Submit**

The integration will automatically discover and create all entities for your device.

## Entities

### Switch
- **Power** - Turn the device on/off (standby mode)

### Select
- **Input Source** - Select from configured input sources
- **Source Aspect Ratio** - Choose aspect ratio (4:3, 16:9, 1.85, 1.90, 2.00, 2.20, 2.35, 2.40, Letterbox)
- **Input Configuration** - Recall input configurations (0-7)

### Sensors

#### Status Sensors
- **Logical Input** - Current logical input number
- **Physical Input** - Current physical input
- **Output Resolution** - Current output resolution and refresh rate
- **Source Aspect Ratio** - Current source aspect ratio
- **Source Dynamic Range** - HDR/SDR status
- **Input Configuration** - Active input configuration number
- **Output CMS** - Active color management system
- **Output Style** - Active output style

#### Diagnostic Sensors
- **Model Name** - Device model name
- **Software Revision** - Firmware version
- **Model Number** - Device model number
- **Serial Number** - Device serial number

### Remote
- **Remote** - Send navigation and control commands

## Usage

### Power Control

Use the power switch to turn the device on or put it in standby:

```yaml
service: switch.turn_on
target:
  entity_id: switch.lumagen_radiancepro_power
```

### Input Selection

Change the input source:

```yaml
service: select.select_option
target:
  entity_id: select.lumagen_radiancepro_input_source
data:
  option: "HDMI 1"
```

### Aspect Ratio Control

Change the aspect ratio:

```yaml
service: select.select_option
target:
  entity_id: select.lumagen_radiancepro_source_aspect_ratio
data:
  option: "2.35"
```

### Remote Commands

Send menu navigation commands:

```yaml
service: remote.send_command
target:
  entity_id: remote.lumagen_radiancepro_remote
data:
  command:
    - menu
    - down
    - enter
```

Available commands:
- **Navigation**: `up`, `down`, `left`, `right`
- **Menu Control**: `menu`, `enter`, `exit`, `back`, `home`, `ok`
- **Utility**: `info`, `alt`, `clear`
- **Number Pad**: `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`

### Automations

Example automation to switch input when a media player starts:

```yaml
automation:
  - alias: "Switch to Apple TV Input"
    trigger:
      - platform: state
        entity_id: media_player.apple_tv
        to: "playing"
    action:
      - service: select.select_option
        target:
          entity_id: select.lumagen_radiancepro_input_source
        data:
          option: "HDMI 2"
```

## Troubleshooting

### Connection Issues

- Verify the device is powered on and connected to the network
- Check firewall settings allow connections on the configured port
- For serial connections, ensure the correct port and baud rate
- Check Home Assistant logs for detailed error messages

### Entity Availability

- Status sensors are only available when the device is active (not in standby)
- Diagnostic sensors remain available even in standby mode
- Power switch is always available when connected
- Remote commands are blocked when the device is in standby

### Input Source Dropdown Empty

If the input source dropdown is empty:
1. Ensure the device is powered on and active
2. Wait for the device to fully initialize (may take 30-60 seconds)
3. Reload the integration
4. Check that input sources are configured on the device

### UI Lag When Switching Power

The device takes approximately 15 seconds to change power states. The integration uses optimistic state updates to provide immediate UI feedback while the device transitions.

## Development

This integration is built using:
- [pylumagen](https://github.com/johncarey70/pylumagen) - Python library for Lumagen control
- Home Assistant's DataUpdateCoordinator for efficient polling
- Proper entity availability handling for standby mode

## Support

For issues, feature requests, or questions:
- Open an issue on [GitHub](https://github.com/vishketan-ha/ha-lumagen)
- Check the [Home Assistant Community Forum](https://community.home-assistant.io/)

## Credits

- Integration developed for Home Assistant
- Uses the [pylumagen](https://github.com/johncarey70/pylumagen) library
- Lumagen Radiance Pro is a product of Lumagen, Inc.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
