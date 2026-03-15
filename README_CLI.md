# Huawei Router Band Tool - CLI Version

A command-line interface tool for managing Huawei router band selection, signal monitoring, and network optimization.

## Features

- **Connection Management**: Connect/disconnect from your Huawei router
- **Signal Monitoring**: Real-time signal metrics (RSRP, RSRQ, SINR)
- **Band Selection**: View and apply band configurations for 4G and 5G
- **Band Optimization**: Automatically test and recommend optimal bands
- **Speed Testing**: Built-in speed test functionality
- **Network Mode Control**: Switch between 2G/3G/4G/5G modes
- **Device Information**: View router details and statistics
- **Traffic Monitoring**: Monitor current and total data usage
- **Report Generation**: Save optimization results to file

## Installation

1. Ensure Python 3.7+ is installed
2. Install required dependencies:
   
   **Using uv (recommended):**
   ```bash
   uv venv && source .venv/bin/activate && uv pip install huawei-lte-api speedtest-cli
   ```
   
   **Using pip:**
   ```bash
   pip install huawei-lte-api speedtest-cli
   ```

## Usage

### Basic Syntax

```bash
python huawei_cli.py <command> [options]
```

### Commands

#### Connection

**Connect to router:**
```bash
python huawei_cli.py connect <ip> <username> <password>
```
Example:
```bash
python huawei_cli.py connect 192.168.8.1 admin admin
```

**Disconnect from router:**
```bash
python huawei_cli.py disconnect
```

#### Signal Information

**Display current signal:**
```bash
python huawei_cli.py signal
```
Shows:
- RSRP (Reference Signal Received Power)
- RSRQ (Reference Signal Received Quality)
- SINR (Signal to Interference plus Noise Ratio)
- Network Type (4G, 5G NSA, 5G SA, etc.)
- Active LTE and 5G NR Bands
- Carrier Name

**Monitor signal continuously:**
```bash
python huawei_cli.py monitor [options]
```
Options:
- `--interval N` - Update every N seconds (default: 5)
- `--count N` - Stop after N updates (default: infinite)

Examples:
```bash
# Monitor every 10 seconds
python huawei_cli.py monitor --interval 10

# Monitor 20 times with 3-second intervals
python huawei_cli.py monitor --interval 3 --count 20
```

#### Band Management

**List available bands:**
```bash
python huawei_cli.py bands
```

**Apply band selection:**
```bash
python huawei_cli.py apply-bands <band1> <band2> ... [--nr-bands <nr_band1> ...]
```

Examples:
```bash
# Apply 4G bands only
python huawei_cli.py apply-bands B1 B3 B7

# Apply 4G and 5G bands
python huawei_cli.py apply-bands B1 B3 B7 --nr-bands n78 n79

# Apply single band
python huawei_cli.py apply-bands B20
```

**Set network mode:**
```bash
python huawei_cli.py set-mode <mode>
```
Available modes:
- `2g` - 2G only
- `3g` - 3G only
- `4g` - 4G only
- `4g+5g` - 4G and 5G
- `5g` - 5G only
- `auto` / `all` - All modes

Examples:
```bash
python huawei_cli.py set-mode 4g
python huawei_cli.py set-mode 4g+5g
python huawei_cli.py set-mode auto
```

#### Optimization

**Basic band optimization:**
Tests each band and recommends the best based on signal quality metrics.
```bash
python huawei_cli.py optimise [--bands <band1> <band2> ...]
```

**Enhanced optimization:**
Includes actual speed tests for each band (takes longer but more accurate).
```bash
python huawei_cli.py optimise --enhanced [--bands <band1> <band2> ...]
```

Examples:
```bash
# Test all available bands
python huawei_cli.py optimise

# Test specific bands
python huawei_cli.py optimise --bands B1 B3 B7 B20

# Enhanced optimization with speed tests
python huawei_cli.py optimise --enhanced

# Enhanced optimization for specific bands
python huawei_cli.py optimise --enhanced --bands B1 B3 B7
```

The optimization process:
1. Tests each band individually
2. Measures signal quality (RSRP, SINR)
3. (Enhanced mode) Runs speed test for each band
4. Calculates overall score
5. Recommends best bands
6. Generates a detailed report file

#### Speed Testing

**Run a speed test:**
```bash
python huawei_cli.py speedtest
```
Displays:
- Download speed (Mbps)
- Upload speed (Mbps)
- Ping (ms)
- Server name

#### Device Information

**Show device info:**
```bash
python huawei_cli.py device
```
Displays:
- Device Name
- Serial Number
- IMEI
- Hardware Version
- Software Version
- Firmware Version
- MAC Address

**Show traffic statistics:**
```bash
python huawei_cli.py traffic
```
Displays:
- Current Download/Upload Rate
- Total Download/Upload
- Connection Time

#### Router Management

**Reboot router:**
```bash
python huawei_cli.py reboot
```

## Supported Bands

### 4G LTE Bands
- B1 (2100 MHz)
- B3 (1800 MHz)
- B7 (2600 MHz)
- B8 (900 MHz)
- B20 (800 MHz)
- B28 (700 MHz)
- B32 (1500 MHz)
- B38 (TD 2600 MHz)
- B40 (TD 2300 MHz)
- B41 (TD 2500 MHz)
- B42 (TD 3500 MHz)

### 5G NR Bands
- n1 (2100 MHz)
- n3 (1800 MHz)
- n28 (700 MHz)
- n41 (2500 MHz)
- n78 (3500 MHz)
- n79 (4700 MHz)

## Configuration

The CLI stores connection settings in `config.json` for convenience. After the first successful connection, you can run most commands without reconnecting.

Config file location: `./config.json`

Example config:
```json
{
    "router_ip": "192.168.8.1",
    "username": "admin",
    "password": "your_password",
    "selected_bands": ["B1", "B3", "B7"]
}
```

## Reports

Optimization reports are saved to the `reports/` directory with timestamps.

Report format: `optimisation_report_YYYY-MM-DD_HH-MM-SS.txt`

Reports include:
- Individual band results
- Signal quality metrics
- Theoretical maximum speeds
- (Enhanced mode) Measured speeds and efficiency
- Recommendations

## Signal Quality Reference

### RSRP (dBm) - Signal Strength
| Range | Quality |
|-------|---------|
| -80 to 0 | Excellent |
| -90 to -80 | Good |
| -100 to -90 | Fair |
| -110 to -100 | Poor |
| < -110 | Very Poor |

### SINR (dB) - Signal Quality
| Range | Quality |
|-------|---------|
| > 20 | Excellent |
| 13 to 20 | Good |
| 10 to 13 | Fair |
| 5 to 10 | Poor |
| < 5 | Very Poor |

## Examples

### Quick Start

```bash
# Connect to router
python huawei_cli.py connect 192.168.8.1 admin admin

# Check current signal
python huawei_cli.py signal

# Run basic optimization
python huawei_cli.py optimise

# Apply recommended bands (e.g., B1, B3, B7)
python huawei_cli.py apply-bands B1 B3 B7

# Verify new signal
python huawei_cli.py signal
```

### Full Optimization Workflow

```bash
# Connect
python huawei_cli.py connect 192.168.8.1 admin admin

# Get current status
python huawei_cli.py signal
python huawei_cli.py device

# Run enhanced optimization (with speed tests)
python huawei_cli.py optimise --enhanced

# Apply recommended bands
python huawei_cli.py apply-bands B1 B3 B7

# Run speed test with new configuration
python huawei_cli.py speedtest

# Monitor signal for stability
python huawei_cli.py monitor --interval 10 --count 6
```

### 5G Configuration

```bash
# Connect
python huawei_cli.py connect 192.168.8.1 admin admin

# Set to 4G+5G mode
python huawei_cli.py set-mode 4g+5g

# Apply 4G and 5G bands
python huawei_cli.py apply-bands B1 B3 B7 --nr-bands n78 n79

# Check signal
python huawei_cli.py signal
```

## Troubleshooting

### Connection Issues

1. **Cannot connect to router**
   - Verify IP address is correct
   - Check that you're on the same network
   - Try pinging the router: `ping 192.168.8.1`

2. **Authentication failed**
   - Verify username and password
   - Check if web interface login works
   - Some routers may require you to login via web first

3. **Session timeout**
   - Reconnect using the `connect` command
   - Connection credentials are saved for convenience

### Band Selection Issues

1. **Band not supported error**
   - Not all bands are available on all devices
   - Use `bands` command to see available bands
   - Some bands may be carrier-locked

2. **No signal after band change**
   - The selected band may not be available in your area
   - Try selecting multiple bands or all bands
   - Wait a few moments for the connection to stabilize

3. **Optimization shows poor results**
   - Check physical router placement
   - Consider external antenna
   - Some bands may not be deployed in your area

### Speed Test Issues

1. **Speed test fails**
   - Ensure internet connection is active
   - Try running test again
   - Check if speedtest.net is accessible

## API Notes

This tool uses the `huawei-lte-api` library which communicates with Huawei routers via their web API. Some features may not be available on all router models or firmware versions.

Tested on:
- Huawei CPE Pro 2 (H122-373)
- Huawei B525
- Huawei B535
- Huawei B818

## License

MIT License - see main project LICENSE file.

## Acknowledgements

- [huawei-lte-api](https://github.com/Salamek/huawei-lte-api) - Huawei router API library
- [speedtest-cli](https://github.com/sivel/speedtest-cli) - Speed testing functionality
