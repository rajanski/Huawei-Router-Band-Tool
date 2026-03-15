#!/usr/bin/env python3
"""
Huawei Router Band Tool - CLI Version
A command-line tool for managing Huawei router band selection and optimization.
"""

import argparse
import json
import sys
import time
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

try:
    from huawei_lte_api.Client import Client
    from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
    from huawei_lte_api.Connection import Connection

    HUAWEI_API_AVAILABLE = True
except ImportError:
    HUAWEI_API_AVAILABLE = False
    print("Error: huawei-lte-api is required. Install with: pip install huawei-lte-api")
    sys.exit(1)

try:
    import speedtest

    SPEEDTEST_AVAILABLE = True
except ImportError:
    SPEEDTEST_AVAILABLE = False

SUPPORTED_4G_BANDS = [
    "B1",
    "B3",
    "B7",
    "B8",
    "B20",
    "B28",
    "B32",
    "B38",
    "B40",
    "B41",
    "B42",
]
SUPPORTED_5G_BANDS = ["n1", "n3", "n28", "n41", "n78", "n79"]

BAND_MAP = {
    1: 0x1,
    3: 0x4,
    7: 0x40,
    8: 0x80,
    20: 0x80000,
    28: 0x8000000,
    32: 0x80000000,
    38: 0x40000000000,
    40: 0x100000000000,
    41: 0x200000000000,
    42: 0x400000000000,
}

NR_BAND_MAP = {
    1: 0x1,
    2: 0x2,
    3: 0x4,
    5: 0x10,
    7: 0x40,
    8: 0x80,
    20: 0x80000,
    28: 0x8000000,
    38: 0x2000000000,
    41: 0x10000000000,
    66: 0x200000000000000,
    71: 0x4000000000000000,
    77: 0x100000000000000000,
    78: 0x200000000000000000,
    79: 0x400000000000000000,
}

THEORETICAL_SPEEDS = {
    "4G": {
        "B1": (150, 50),
        "B3": (300, 75),
        "B7": (300, 75),
        "B8": (100, 35),
        "B20": (150, 50),
        "B28": (150, 50),
        "B32": (100, 50),
        "B38": (200, 50),
        "B40": (200, 50),
        "B41": (200, 50),
        "B42": (200, 50),
    },
    "4G+": {
        "B1": (300, 75),
        "B3": (450, 100),
        "B7": (450, 100),
        "B8": (150, 50),
        "B20": (300, 75),
        "B28": (300, 75),
        "B32": (150, 75),
        "B38": (300, 75),
        "B40": (300, 75),
        "B41": (300, 75),
        "B42": (300, 75),
    },
    "5G": {
        "B1": (900, 150),
        "B3": (1000, 200),
        "B7": (1000, 200),
        "B28": (800, 150),
        "B41": (2000, 300),
        "B42": (2000, 300),
    },
}

SIGNAL_QUALITY_FACTORS = {
    (-80, 0): 1.0,
    (-90, -80): 0.9,
    (-100, -90): 0.7,
    (-110, -100): 0.5,
    (-120, -110): 0.3,
    (-999, -120): 0.1,
}

CONFIG_FILE = "config.json"
REPORTS_DIR = "reports"


class HuaweiCLI:
    def __init__(self):
        self.client: Optional[Client] = None
        self.config = self.load_config()

    def load_config(self) -> Dict:
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "router_ip": "192.168.8.1",
                "username": "admin",
                "password": "",
                "selected_bands": [],
            }

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def connect(self, ip: str, username: str, password: str) -> bool:
        if not HUAWEI_API_AVAILABLE:
            print("Error: huawei-lte-api library not available")
            return False

        try:
            url = f"http://{username}:{password}@{ip}/"
            self.client = Client(AuthorizedConnection(url))
            device_info = self.client.device.information()
            print(f"Connected successfully!")
            print(f"Device: {device_info.get('devicename', 'Unknown')}")
            print(f"Hardware Version: {device_info.get('HardwareVersion', 'Unknown')}")
            print(f"Firmware: {device_info.get('firmwareversion', 'Unknown')}")

            self.config["router_ip"] = ip
            self.config["username"] = username
            self.config["password"] = password
            self.save_config()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.client:
            try:
                self.client = None
            except:
                pass
            print("Disconnected from router")
        else:
            print("Not connected")

    def get_signal_info(self) -> Optional[Dict]:
        if not self.client:
            print("Error: Not connected to router")
            return None

        try:
            signal_data = {}

            signal_info = self.client.device.signal()
            if isinstance(signal_info, dict):
                signal_data["rsrp"] = signal_info.get("rsrp", "--")
                signal_data["rsrq"] = signal_info.get("rsrq", "--")
                signal_data["sinr"] = signal_info.get("sinr", "--")

                if "cell_id" in signal_info:
                    for cell in signal_info["cell_id"]:
                        if (
                            isinstance(cell, dict)
                            and cell.get("rsrp")
                            and cell.get("rsrp") != "--"
                        ):
                            signal_data["rsrp"] = cell.get("rsrp", "--")
                            signal_data["rsrq"] = cell.get("rsrq", "--")
                            signal_data["sinr"] = cell.get("sinr", "--")
                            break
            else:
                signal_data["rsrp"] = "--"
                signal_data["rsrq"] = "--"
                signal_data["sinr"] = "--"

            try:
                status_info = self.client.monitoring.status()
                if isinstance(status_info, dict):
                    network_type_code = status_info.get("CurrentNetworkType", "--")
                else:
                    network_type_code = "--"
                network_types = {
                    "0": "No Service",
                    "1": "GSM",
                    "2": "GPRS",
                    "3": "EDGE",
                    "4": "WCDMA",
                    "5": "HSDPA",
                    "6": "HSUPA",
                    "7": "4G",
                    "8": "TD-SCDMA",
                    "9": "HSPA+",
                    "19": "LTE",
                    "20": "LTE-CA (4G+)",
                    "21": "5G NSA",
                    "22": "5G SA",
                    "23": "5G",
                    "101": "5G NSA",
                    "102": "5G SA",
                    "103": "5G",
                }
                signal_data["network_type"] = network_types.get(
                    network_type_code, f"Unknown ({network_type_code})"
                )
            except:
                signal_data["network_type"] = "Unknown"

            try:
                net_mode_info = self.client.net.net_mode()
                if isinstance(net_mode_info, dict):
                    if "LTEBand" in net_mode_info:
                        lte_band_hex = net_mode_info.get("LTEBand", "--")
                        if lte_band_hex != "--" and lte_band_hex != "0":
                            try:
                                active_bands = []
                                lte_band_int = int(lte_band_hex, 16)
                                for band_num, band_hex in BAND_MAP.items():
                                    if lte_band_int & band_hex:
                                        active_bands.append(f"B{band_num}")
                                signal_data["lte_bands"] = (
                                    ", ".join(active_bands) if active_bands else "--"
                                )
                            except:
                                signal_data["lte_bands"] = "--"
                        else:
                            signal_data["lte_bands"] = "--"

                    if "NrBand" in net_mode_info:
                        nr_band_hex = net_mode_info.get("NrBand", "--")
                        if nr_band_hex != "--" and nr_band_hex != "0":
                            try:
                                active_bands = []
                                nr_band_int = int(nr_band_hex, 16)
                                for band_num, band_hex in NR_BAND_MAP.items():
                                    if nr_band_int & band_hex:
                                        active_bands.append(f"n{band_num}")
                                signal_data["nr_bands"] = (
                                    ", ".join(active_bands) if active_bands else "--"
                                )
                            except:
                                signal_data["nr_bands"] = "--"
                        else:
                            signal_data["nr_bands"] = "--"
                else:
                    signal_data["lte_bands"] = "--"
                    signal_data["nr_bands"] = "--"
            except:
                pass

            try:
                plmn_info = self.client.net.current_plmn()
                if isinstance(plmn_info, dict):
                    signal_data["carrier"] = plmn_info.get(
                        "FullName", plmn_info.get("ShortName", "--")
                    )
                else:
                    signal_data["carrier"] = "--"
            except:
                signal_data["carrier"] = "--"

            return signal_data
        except Exception as e:
            print(f"Error getting signal info: {e}")
            return None

    def display_signal(self):
        signal = self.get_signal_info()
        if signal:
            print("\n" + "=" * 50)
            print("SIGNAL INFORMATION")
            print("=" * 50)
            print(f"RSRP:           {signal.get('rsrp', '--')} dBm")
            print(f"RSRQ:           {signal.get('rsrq', '--')} dB")
            print(f"SINR:           {signal.get('sinr', '--')} dB")
            print(f"Network Type:   {signal.get('network_type', '--')}")
            print(f"LTE Bands:      {signal.get('lte_bands', '--')}")
            print(f"5G NR Bands:    {signal.get('nr_bands', '--')}")
            print(f"Carrier:        {signal.get('carrier', '--')}")
            print("=" * 50 + "\n")

    def get_available_bands(self) -> Dict[str, List[str]]:
        if not self.client:
            print("Error: Not connected to router")
            return {"4G": [], "5G": []}

        try:
            bands = {"4G": SUPPORTED_4G_BANDS.copy(), "5G": SUPPORTED_5G_BANDS.copy()}

            try:
                net_mode_info = self.client.net.net_mode()
                if "LTEBand" in net_mode_info:
                    lte_band_hex = net_mode_info.get("LTEBand", "--")
                    if lte_band_hex != "--" and lte_band_hex != "0":
                        active_bands = []
                        lte_band_int = int(lte_band_hex, 16)
                        for band_num, band_hex in BAND_MAP.items():
                            if lte_band_int & band_hex:
                                active_bands.append(f"B{band_num}")
                        if active_bands:
                            bands["4G"] = active_bands
            except:
                pass

            return bands
        except Exception as e:
            print(f"Error getting available bands: {e}")
            return {"4G": SUPPORTED_4G_BANDS.copy(), "5G": SUPPORTED_5G_BANDS.copy()}

    def list_bands(self):
        if not self.client:
            print("Error: Not connected to router")
            return

        bands = self.get_available_bands()
        print("\n" + "=" * 50)
        print("AVAILABLE BANDS")
        print("=" * 50)
        print("\n4G Bands:")
        for band in bands["4G"]:
            print(f"  - {band}")
        print("\n5G Bands:")
        for band in bands["5G"]:
            print(f"  - {band}")
        print("=" * 50 + "\n")

    def apply_bands(self, bands: List[str], nr_bands: Optional[List[str]] = None):
        if not self.client:
            print("Error: Not connected to router")
            return False

        try:
            current_mode = self.client.net.net_mode()

            band_numbers = []
            for band in bands:
                if band.startswith("B"):
                    band_numbers.append(int(band[1:]))
                elif band.isdigit():
                    band_numbers.append(int(band))

            band_hex = sum(BAND_MAP.get(num, 0) for num in band_numbers) or 0x3FFFFFFF
            band_hex_str = format(band_hex, "X")

            nr_band_hex_str = None
            if nr_bands:
                nr_band_numbers = []
                for band in nr_bands:
                    if band.startswith("n"):
                        nr_band_numbers.append(int(band[1:]))
                    elif band.isdigit():
                        nr_band_numbers.append(int(band))
                nr_band_hex = (
                    sum(NR_BAND_MAP.get(num, 0) for num in nr_band_numbers)
                    or 0x7FFFFFFFFFFFFFFF
                )
                nr_band_hex_str = format(nr_band_hex, "X")

            try:
                if nr_band_hex_str:
                    try:
                        response = self.client.net.set_net_mode(
                            lteband=band_hex_str,
                            networkband=current_mode.get("NetworkBand", "3FFFFFFF"),
                            networkmode=current_mode.get("NetworkMode", "03"),
                            **{"nrband": nr_band_hex_str},
                        )
                    except (TypeError, Exception):
                        response = self.client.net.set_net_mode(
                            lteband=band_hex_str,
                            networkband=current_mode.get("NetworkBand", "3FFFFFFF"),
                            networkmode=current_mode.get("NetworkMode", "03"),
                        )
                else:
                    response = self.client.net.set_net_mode(
                        lteband=band_hex_str,
                        networkband=current_mode.get("NetworkBand", "3FFFFFFF"),
                        networkmode=current_mode.get("NetworkMode", "03"),
                    )

                if response == "OK" or (
                    isinstance(response, dict) and response.get("result") == "success"
                ):
                    print(f"Successfully applied bands: {', '.join(bands)}")
                    if nr_bands:
                        print(f"5G NR Bands: {', '.join(nr_bands)}")
                    return True
                else:
                    print(f"Unexpected response: {response}")
                    return False
            except Exception as e:
                if "112003" in str(e):
                    print("Error: One or more bands are not supported by this device")
                else:
                    print(f"Error applying bands: {e}")
                return False

        except Exception as e:
            print(f"Error applying bands: {e}")
            return False

    def apply_network_mode(self, mode: str):
        if not self.client:
            print("Error: Not connected to router")
            return False

        mode_map = {
            "2g": "01",
            "3g": "02",
            "4g": "03",
            "4g+5g": "03",
            "5g": "05",
            "auto": "00",
            "all": "00",
        }

        mode_lower = mode.lower().replace(" ", "").replace("+", "")
        network_mode = mode_map.get(mode_lower, "03")

        try:
            current_mode = self.client.net.net_mode()
            response = self.client.net.set_net_mode(
                lteband=current_mode.get("LTEBand", "3FFFFFFF"),
                networkband=current_mode.get("NetworkBand", "3FFFFFFF"),
                networkmode=network_mode,
            )

            if response == "OK" or (
                isinstance(response, dict) and response.get("result") == "success"
            ):
                print(f"Successfully set network mode to: {mode}")
                return True
            else:
                print(f"Unexpected response: {response}")
                return False
        except Exception as e:
            print(f"Error setting network mode: {e}")
            return False

    def run_speedtest(self) -> Optional[Dict]:
        if not SPEEDTEST_AVAILABLE:
            print(
                "Error: speedtest-cli not available. Install with: pip install speedtest-cli"
            )
            return None

        print("Running speed test...")
        try:
            import speedtest as st

            s = st.Speedtest()
            s.get_best_server()
            print("Testing download speed...")
            s.download()
            print("Testing upload speed...")
            s.upload()

            results = s.results.dict()
            speed_results = {
                "download": results["download"] / 1_000_000,
                "upload": results["upload"] / 1_000_000,
                "ping": results["ping"],
                "server": results.get("server", {}).get("name", "Unknown"),
            }

            print("\n" + "=" * 50)
            print("SPEED TEST RESULTS")
            print("=" * 50)
            print(f"Download:  {speed_results['download']:.2f} Mbps")
            print(f"Upload:    {speed_results['upload']:.2f} Mbps")
            print(f"Ping:      {speed_results['ping']:.1f} ms")
            print(f"Server:    {speed_results['server']}")
            print("=" * 50 + "\n")

            return speed_results
        except Exception as e:
            print(f"Speed test failed: {e}")
            return None

    def estimate_max_speed(
        self, band: str, network_type: str, rsrp: float, sinr: float
    ) -> Tuple[float, float]:
        default_speeds = {
            "2G": (0.3, 0.1),
            "3G": (7, 2),
            "4G": (150, 50),
            "4G+": (300, 75),
            "5G": (1000, 200),
        }

        normalized_type = network_type
        if "LTE-CA" in network_type or "4G+" in network_type:
            normalized_type = "4G+"
        elif "5G" in network_type:
            normalized_type = "5G"
        elif "LTE" in network_type or "4G" in network_type:
            normalized_type = "4G"

        first_band = band.split(",")[0].strip() if "," in band else band.strip()
        band_key = first_band if first_band.startswith("B") else f"B{first_band}"

        if (
            normalized_type in THEORETICAL_SPEEDS
            and band_key in THEORETICAL_SPEEDS[normalized_type]
        ):
            max_dl, max_ul = THEORETICAL_SPEEDS[normalized_type][band_key]
        else:
            max_dl, max_ul = default_speeds.get(normalized_type, default_speeds["4G"])

        try:
            signal_factor = 0.5
            for (min_val, max_val), factor in SIGNAL_QUALITY_FACTORS.items():
                if min_val <= rsrp < max_val:
                    signal_factor = factor
                    break

            sinr_factor = 0.5
            if sinr > 20:
                sinr_factor = 1.0
            elif sinr > 13:
                sinr_factor = 0.9
            elif sinr > 10:
                sinr_factor = 0.8
            elif sinr > 5:
                sinr_factor = 0.6

            combined_factor = (signal_factor * 0.7) + (sinr_factor * 0.3)
            return max_dl * combined_factor, max_ul * combined_factor
        except:
            return max_dl, max_ul

    def calculate_signal_score(self, rsrp: float, sinr: float) -> float:
        rsrp_score = 0
        if rsrp >= -80:
            rsrp_score = 100
        elif rsrp >= -90:
            rsrp_score = 80
        elif rsrp >= -100:
            rsrp_score = 60
        elif rsrp >= -110:
            rsrp_score = 40
        else:
            rsrp_score = 20

        sinr_score = 0
        if sinr >= 20:
            sinr_score = 100
        elif sinr >= 13:
            sinr_score = 80
        elif sinr >= 10:
            sinr_score = 60
        elif sinr >= 5:
            sinr_score = 40
        else:
            sinr_score = 20

        return (rsrp_score * 0.6) + (sinr_score * 0.4)

    def parse_rsrp(self, rsrp_str: str) -> float:
        try:
            if isinstance(rsrp_str, str):
                return float(rsrp_str.replace("dBm", "").strip())
            return float(rsrp_str)
        except:
            return -110

    def parse_sinr(self, sinr_str: str) -> float:
        try:
            if isinstance(sinr_str, str):
                return float(sinr_str.replace("dB", "").strip())
            return float(sinr_str)
        except:
            return 0

    def optimise_bands(self, bands: Optional[List[str]] = None, enhanced: bool = False):
        if not self.client:
            print("Error: Not connected to router")
            return

        test_bands = bands if bands else SUPPORTED_4G_BANDS
        results = {}

        print(
            f"\nStarting band optimisation ({'enhanced' if enhanced else 'basic'})..."
        )
        print(f"Testing bands: {', '.join(test_bands)}\n")

        original_mode = self.client.net.net_mode()

        for band in test_bands:
            band_num = int(band[1:]) if band.startswith("B") else int(band)
            print(f"Testing band {band}...", end=" ", flush=True)

            try:
                band_hex = format(BAND_MAP.get(band_num, 0), "X")

                response = self.client.net.set_net_mode(
                    lteband=band_hex,
                    networkband=original_mode.get("NetworkBand", "3FFFFFFF"),
                    networkmode=original_mode.get("NetworkMode", "03"),
                )

                if response != "OK" and not (
                    isinstance(response, dict) and response.get("result") == "success"
                ):
                    print("SKIPPED (not supported)")
                    continue

                time.sleep(3)

                signal = self.get_signal_info()
                if signal:
                    rsrp = self.parse_rsrp(signal.get("rsrp", "-110"))
                    sinr = self.parse_sinr(signal.get("sinr", "0"))
                    network_type = signal.get("network_type", "4G")

                    result = {
                        "rsrp": rsrp,
                        "rsrq": signal.get("rsrq", "--"),
                        "sinr": sinr,
                        "network_type": network_type,
                    }

                    theoretical_dl, theoretical_ul = self.estimate_max_speed(
                        band, network_type, rsrp, sinr
                    )
                    result["theoretical_dl_mbps"] = theoretical_dl
                    result["theoretical_ul_mbps"] = theoretical_ul

                    if enhanced and SPEEDTEST_AVAILABLE:
                        print("Running speed test...", end=" ", flush=True)
                        speed = self.run_speedtest()
                        if speed:
                            result["download_mbps"] = speed["download"]
                            result["upload_mbps"] = speed["upload"]
                            result["ping_ms"] = speed["ping"]

                            if theoretical_dl > 0:
                                result["dl_efficiency"] = (
                                    speed["download"] / theoretical_dl
                                ) * 100
                            if theoretical_ul > 0:
                                result["ul_efficiency"] = (
                                    speed["upload"] / theoretical_ul
                                ) * 100

                            result["signal_score"] = self.calculate_signal_score(
                                rsrp, sinr
                            )
                            result["speed_score"] = (speed["download"] / 1000) * 10 + (
                                speed["upload"] / 100
                            ) * 5
                            result["score"] = (
                                result["signal_score"] * 0.4
                                + result["speed_score"] * 0.6
                            )
                        else:
                            result["score"] = self.calculate_signal_score(rsrp, sinr)
                    else:
                        result["score"] = self.calculate_signal_score(rsrp, sinr)

                    results[band_num] = result
                    print(
                        f"RSRP: {rsrp} dBm, SINR: {sinr} dB, Score: {result['score']:.1f}"
                    )
                else:
                    print("FAILED (no signal)")

            except Exception as e:
                print(f"ERROR ({e})")

        try:
            original_lte = original_mode.get("LTEBand", "3FFFFFFF")
            self.client.net.set_net_mode(
                lteband=original_lte,
                networkband=original_mode.get("NetworkBand", "3FFFFFFF"),
                networkmode=original_mode.get("NetworkMode", "03"),
            )
        except:
            pass

        if results:
            sorted_results = sorted(
                results.items(), key=lambda x: x[1]["score"], reverse=True
            )

            print("\n" + "=" * 60)
            print("OPTIMISATION RESULTS")
            print("=" * 60)
            print(f"{'Band':<6} {'RSRP':<10} {'SINR':<8} {'Type':<12} {'Score':<8}")
            print("-" * 60)

            for band_num, result in sorted_results:
                print(
                    f"B{band_num:<5} {result['rsrp']:<10} {result['sinr']:<8} {result['network_type']:<12} {result['score']:<8.1f}"
                )

            print("-" * 60)

            best_bands = sorted_results[:3]
            print(f"\nRecommended bands: {', '.join([f'B{b[0]}' for b in best_bands])}")
            print(
                f"Best band: B{best_bands[0][0]} (Score: {best_bands[0][1]['score']:.1f})"
            )

            self.generate_report(results, enhanced)
        else:
            print("\nNo valid results to report")

    def ensure_reports_dir(self):
        if not os.path.exists(REPORTS_DIR):
            os.makedirs(REPORTS_DIR)
        return REPORTS_DIR

    def generate_report(self, results: Dict, enhanced: bool = False):
        self.ensure_reports_dir()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = os.path.join(REPORTS_DIR, f"optimisation_report_{timestamp}.txt")

        with open(report_path, "w") as f:
            f.write("Band Optimisation Report\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Optimisation Type: {'Enhanced' if enhanced else 'Basic'}\n\n")

            sorted_results = sorted(
                results.items(), key=lambda x: x[1]["score"], reverse=True
            )

            f.write("Individual Band Results:\n")
            f.write("-" * 40 + "\n")

            for band_num, result in sorted_results:
                f.write(f"Band: B{band_num}\n")
                f.write(f"  Network Type: {result.get('network_type', 'Unknown')}\n")
                f.write(f"  RSRP: {result['rsrp']} dBm\n")
                f.write(f"  SINR: {result['sinr']} dB\n")

                if "theoretical_dl_mbps" in result:
                    f.write(
                        f"  Theoretical Download: {result['theoretical_dl_mbps']:.2f} Mbps\n"
                    )
                    f.write(
                        f"  Theoretical Upload: {result['theoretical_ul_mbps']:.2f} Mbps\n"
                    )

                if "download_mbps" in result:
                    f.write(
                        f"  Measured Download: {result['download_mbps']:.2f} Mbps\n"
                    )
                    f.write(f"  Measured Upload: {result['upload_mbps']:.2f} Mbps\n")
                    f.write(f"  Ping: {result['ping_ms']:.1f} ms\n")

                    if "dl_efficiency" in result:
                        f.write(
                            f"  Download Efficiency: {result['dl_efficiency']:.1f}%\n"
                        )
                        f.write(
                            f"  Upload Efficiency: {result['ul_efficiency']:.1f}%\n"
                        )
                    f.write(f"  Signal Score: {result.get('signal_score', 'N/A')}\n")
                    f.write(f"  Speed Score: {result.get('speed_score', 'N/A')}\n")

                f.write(f"  Overall Score: {result['score']:.1f}\n\n")

            best_bands = sorted_results[:3]
            f.write("Recommendations:\n")
            f.write("-" * 40 + "\n")
            f.write(
                f"Best band: B{best_bands[0][0]} (Score: {best_bands[0][1]['score']:.1f})\n"
            )
            f.write(
                f"Recommended combination: {', '.join([f'B{b[0]}' for b in best_bands])}\n"
            )

        print(f"\nReport saved to: {report_path}")

    def monitor_signal(self, interval: int = 5, count: Optional[int] = None):
        if not self.client:
            print("Error: Not connected to router")
            return

        print(
            f"Starting signal monitoring (interval: {interval}s{', count: ' + str(count) if count else ''})..."
        )
        print("Press Ctrl+C to stop\n")

        iteration = 0
        try:
            while True:
                if count and iteration >= count:
                    break

                signal = self.get_signal_info()
                if signal:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(
                        f"[{timestamp}] RSRP: {signal.get('rsrp', '--')} dBm | "
                        f"RSRQ: {signal.get('rsrq', '--')} dB | "
                        f"SINR: {signal.get('sinr', '--')} dB | "
                        f"Type: {signal.get('network_type', '--')} | "
                        f"Bands: {signal.get('lte_bands', '--')}"
                    )

                iteration += 1
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")

    def get_device_info(self):
        if not self.client:
            print("Error: Not connected to router")
            return

        try:
            info = self.client.device.information()
            print("\n" + "=" * 50)
            print("DEVICE INFORMATION")
            print("=" * 50)
            print(f"Device Name:     {info.get('devicename', 'Unknown')}")
            print(f"Serial Number:   {info.get('serialnumber', 'Unknown')}")
            print(f"IMEI:            {info.get('imei', 'Unknown')}")
            print(f"Hardware Ver:    {info.get('HardwareVersion', 'Unknown')}")
            print(f"Software Ver:    {info.get('SoftwareVersion', 'Unknown')}")
            print(f"Firmware:        {info.get('firmwareversion', 'Unknown')}")
            print(f"MAC Address:     {info.get('macaddress1', 'Unknown')}")
            print("=" * 50 + "\n")
        except Exception as e:
            print(f"Error getting device info: {e}")

    def get_traffic_stats(self):
        if not self.client:
            print("Error: Not connected to router")
            return

        try:
            stats = self.client.monitoring.traffic_statistics()
            print("\n" + "=" * 50)
            print("TRAFFIC STATISTICS")
            print("=" * 50)
            print(
                f"Current Download: {float(stats.get('CurrentDownloadRate', 0)) / 1024:.2f} KB/s"
            )
            print(
                f"Current Upload:   {float(stats.get('CurrentUploadRate', 0)) / 1024:.2f} KB/s"
            )
            print(
                f"Total Download:   {int(stats.get('TotalDownload', 0)) / (1024 * 1024 * 1024):.2f} GB"
            )
            print(
                f"Total Upload:     {int(stats.get('TotalUpload', 0)) / (1024 * 1024 * 1024):.2f} GB"
            )
            print(
                f"Connected Time:   {int(stats.get('CurrentConnectTime', 0)) / 60:.0f} minutes"
            )
            print("=" * 50 + "\n")
        except Exception as e:
            print(f"Error getting traffic stats: {e}")

    def reboot(self):
        if not self.client:
            print("Error: Not connected to router")
            return False

        try:
            self.client.device.reboot()
            print("Reboot command sent. Router will restart shortly.")
            return True
        except Exception as e:
            print(f"Error rebooting: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Huawei Router Band Tool - CLI Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s connect 192.168.8.1 admin password
  %(prog)s signal
  %(prog)s bands
  %(prog)s apply-bands B1 B3 B7
  %(prog)s optimise
  %(prog)s optimise --enhanced
  %(prog)s monitor --interval 10
  %(prog)s speedtest
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    connect_parser = subparsers.add_parser("connect", help="Connect to router")
    connect_parser.add_argument("ip", help="Router IP address")
    connect_parser.add_argument("username", help="Username")
    connect_parser.add_argument("password", help="Password")

    subparsers.add_parser("disconnect", help="Disconnect from router")
    subparsers.add_parser("signal", help="Show signal information")
    subparsers.add_parser("bands", help="List available bands")
    subparsers.add_parser("device", help="Show device information")
    subparsers.add_parser("traffic", help="Show traffic statistics")
    subparsers.add_parser("speedtest", help="Run a speed test")

    apply_bands_parser = subparsers.add_parser(
        "apply-bands", help="Apply band selection"
    )
    apply_bands_parser.add_argument(
        "bands", nargs="+", help="Bands to apply (e.g., B1 B3 B7)"
    )
    apply_bands_parser.add_argument(
        "--nr-bands", nargs="+", help="5G NR bands to apply (e.g., n78 n79)"
    )

    mode_parser = subparsers.add_parser("set-mode", help="Set network mode")
    mode_parser.add_argument(
        "mode",
        choices=["2g", "3g", "4g", "4g+5g", "5g", "auto", "all"],
        help="Network mode to set",
    )

    optimise_parser = subparsers.add_parser("optimise", help="Optimise band selection")
    optimise_parser.add_argument("--bands", nargs="+", help="Specific bands to test")
    optimise_parser.add_argument(
        "--enhanced", action="store_true", help="Include speed tests"
    )

    monitor_parser = subparsers.add_parser(
        "monitor", help="Monitor signal continuously"
    )
    monitor_parser.add_argument(
        "--interval", type=int, default=5, help="Update interval in seconds"
    )
    monitor_parser.add_argument(
        "--count", type=int, help="Number of updates (default: infinite)"
    )

    subparsers.add_parser("reboot", help="Reboot the router")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cli = HuaweiCLI()

    if args.command == "connect":
        cli.connect(args.ip, args.username, args.password)
    elif args.command == "disconnect":
        cli.disconnect()
    elif args.command == "signal":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.display_signal()
    elif args.command == "bands":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.list_bands()
    elif args.command == "device":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.get_device_info()
    elif args.command == "traffic":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.get_traffic_stats()
    elif args.command == "apply-bands":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.apply_bands(args.bands, args.nr_bands)
    elif args.command == "set-mode":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.apply_network_mode(args.mode)
    elif args.command == "optimise":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.optimise_bands(args.bands, args.enhanced)
    elif args.command == "monitor":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.monitor_signal(args.interval, args.count)
    elif args.command == "speedtest":
        cli.run_speedtest()
    elif args.command == "reboot":
        if not cli.client:
            ip = cli.config.get("router_ip", "")
            username = cli.config.get("username", "")
            password = cli.config.get("password", "")
            if ip and username and password:
                cli.connect(ip, username, password)
        cli.reboot()


if __name__ == "__main__":
    main()
