import time
import os
from prometheus_client import start_http_server, Gauge
import tinytuya

DEVICE_ID = os.environ["TUYA_DEVICE_ID"]
DEVICE_IP = os.environ["TUYA_DEVICE_IP"]
LOCAL_KEY = os.environ["TUYA_LOCAL_KEY"]
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

def poll_device():
    d = tinytuya.OutletDevice(
        dev_id=DEVICE_ID,
        address=DEVICE_IP,
        local_key=LOCAL_KEY,
        version=3.5,
    )
    d.set_socketPersistent(False)
    d.set_socketTimeout(10)
    return d.status()

def update_metrics(data):
    dps = data.get("dps", {})
    if not dps:
        print(f"No dps in response: {data}")
        return

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    start_http_server(port)
    print(f"Exporter running on :{port}, polling every {POLL_INTERVAL}s")

    while True:
        try:
            data = poll_device()
            update_metrics(data)
            print(f"Poll OK: {data.get('dps', {}).get('132', '?')}W total")
        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(POLL_INTERVAL)
