import time
import os
from prometheus_client import start_http_server, Gauge
import tinytuya

DEVICE_ID = os.environ["TUYA_DEVICE_ID"]
API_REGION = os.environ.get("TUYA_API_REGION", "eu")
API_KEY = os.environ["TUYA_API_KEY"]
API_SECRET = os.environ["TUYA_API_SECRET"]
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))

# Per-phase gauges
voltage = Gauge("tuya_voltage_volts", "Voltage in volts", ["phase"])
current = Gauge("tuya_current_amps", "Current in amps", ["phase"])
power = Gauge("tuya_power_watts", "Active power in watts", ["phase"])
power_factor = Gauge("tuya_power_factor", "Power factor", ["phase"])
energy = Gauge("tuya_energy_kwh", "Cumulative energy in kWh", ["phase"])

# Totals
total_energy = Gauge("tuya_total_energy_kwh", "Total cumulative energy in kWh")
total_power = Gauge("tuya_total_power_watts", "Total active power in watts")

# DPS mapping for PC321-W-TY 3-phase meter
DPS_MAP = {
    "A": {"voltage": "101", "current": "102", "power": "103", "pf": "104", "energy": "106"},
    "B": {"voltage": "111", "current": "112", "power": "113", "pf": "114", "energy": "116"},
    "C": {"voltage": "121", "current": "122", "power": "123", "pf": "124", "energy": "126"},
}


def create_cloud():
    c = tinytuya.Cloud(
        apiRegion=API_REGION,
        apiKey=API_KEY,
        apiSecret=API_SECRET,
    )
    return c


def poll_device(cloud):
    result = cloud.getstatus(DEVICE_ID)
    return result


def update_metrics(data):
    if "result" not in data:
        print(f"Unexpected response: {data}")
        return

    # Cloud API returns list of {"code": "...", "value": ...}
    # Convert to dps-style dict
    dps = {}
    for item in data["result"]:
        code = item.get("code", "")
        value = item.get("value")
        # Map cloud codes to DPS numbers
        dps[code] = value

    # Try DPS-style first (if cloud returns numeric keys)
    # Otherwise map by code names
    # The cloud API may return different formats, handle both
    if any(k.isdigit() for k in dps):
        _update_from_dps(dps)
    else:
        _update_from_codes(dps)


def _update_from_dps(dps):
    for phase, keys in DPS_MAP.items():
        if keys["voltage"] in dps:
            voltage.labels(phase=phase).set(dps[keys["voltage"]] / 10.0)
        if keys["current"] in dps:
            current.labels(phase=phase).set(dps[keys["current"]] / 1000.0)
        if keys["power"] in dps:
            power.labels(phase=phase).set(dps[keys["power"]])
        if keys["pf"] in dps:
            power_factor.labels(phase=phase).set(dps[keys["pf"]] / 100.0)
        if keys["energy"] in dps:
            energy.labels(phase=phase).set(dps[keys["energy"]] / 100.0)

    if "131" in dps:
        total_energy.set(dps["131"] / 100.0)
    if "132" in dps:
        total_power.set(dps["132"])


def _update_from_codes(dps):
    # Cloud API code mapping for PC321-W-TY
    phase_map = {
        "A": {
            "voltage": "phase_a_voltage",
            "current": "phase_a_current",
            "power": "phase_a_power",
            "pf": "phase_a_power_factor",
            "energy": "phase_a_energy",
        },
        "B": {
            "voltage": "phase_b_voltage",
            "current": "phase_b_current",
            "power": "phase_b_power",
            "pf": "phase_b_power_factor",
            "energy": "phase_b_energy",
        },
        "C": {
            "voltage": "phase_c_voltage",
            "current": "phase_c_current",
            "power": "phase_c_power",
            "pf": "phase_c_power_factor",
            "energy": "phase_c_energy",
        },
    }

    for phase, keys in phase_map.items():
        if keys["voltage"] in dps:
            voltage.labels(phase=phase).set(dps[keys["voltage"]] / 10.0)
        if keys["current"] in dps:
            current.labels(phase=phase).set(dps[keys["current"]] / 1000.0)
        if keys["power"] in dps:
            power.labels(phase=phase).set(dps[keys["power"]])
        if keys["pf"] in dps:
            power_factor.labels(phase=phase).set(dps[keys["pf"]] / 100.0)
        if keys["energy"] in dps:
            energy.labels(phase=phase).set(dps[keys["energy"]] / 100.0)

    if "total_energy" in dps:
        total_energy.set(dps["total_energy"] / 100.0)
    if "total_power" in dps:
        total_power.set(dps["total_power"])


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    start_http_server(port)
    print(f"Exporter running on :{port}, polling cloud API every {POLL_INTERVAL}s")

    cloud = create_cloud()

    while True:
        try:
            data = poll_device(cloud)
            update_metrics(data)
            print(f"Poll OK: {data}")
        except Exception as e:
            print(f"Poll error: {e}")
            # Recreate cloud client on error
            cloud = create_cloud()
        time.sleep(POLL_INTERVAL)
