import time
import os
import subprocess
import socket
import threading
from prometheus_client import start_http_server, Gauge
import tinytuya

DEVICE_ID = os.environ["TUYA_DEVICE_ID"]
DEVICE_IP = os.environ["TUYA_DEVICE_IP"]
LOCAL_KEY = os.environ["TUYA_LOCAL_KEY"]
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))
PROXY_PORT = 16668  # local port that proxies to device via tailscale

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


def tcp_proxy_handler(client_sock, target_ip, target_port):
    """Proxy a TCP connection through tailscale nc."""
    try:
        proc = subprocess.Popen(
            ["tailscale", "nc", target_ip, str(target_port)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def forward(src, dst):
            try:
                while True:
                    data = src.read(4096)
                    if not data:
                        break
                    dst.write(data)
                    dst.flush()
            except Exception:
                pass

        def sock_to_proc():
            try:
                while True:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    proc.stdin.write(data)
                    proc.stdin.flush()
            except Exception:
                pass
            finally:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

        def proc_to_sock():
            try:
                while True:
                    data = proc.stdout.read(4096)
                    if not data:
                        break
                    client_sock.sendall(data)
            except Exception:
                pass
            finally:
                client_sock.close()

        t1 = threading.Thread(target=sock_to_proc, daemon=True)
        t2 = threading.Thread(target=proc_to_sock, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)
        proc.terminate()
    except Exception as e:
        print(f"Proxy error: {e}")
        client_sock.close()


def start_tcp_proxy(listen_port, target_ip, target_port):
    """Start a TCP proxy that forwards connections through tailscale nc."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", listen_port))
    server.listen(5)
    print(f"TCP proxy listening on 127.0.0.1:{listen_port} -> {target_ip}:{target_port} via tailscale")

    while True:
        client_sock, addr = server.accept()
        t = threading.Thread(
            target=tcp_proxy_handler,
            args=(client_sock, target_ip, target_port),
            daemon=True,
        )
        t.start()


def poll_device():
    d = tinytuya.OutletDevice(
        dev_id=DEVICE_ID,
        address="127.0.0.1",
        local_key=LOCAL_KEY,
        version=3.5,
    )
    d.port = PROXY_PORT
    d.set_socketPersistent(False)
    d.set_socketTimeout(15)
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

    # Start TCP proxy in background thread
    proxy_thread = threading.Thread(
        target=start_tcp_proxy,
        args=(PROXY_PORT, DEVICE_IP, 6668),
        daemon=True,
    )
    proxy_thread.start()

    # Give proxy a moment to start
    time.sleep(1)

    start_http_server(port)
    print(f"Exporter running on :{port}, polling every {POLL_INTERVAL}s via tailscale proxy")

    while True:
        try:
            data = poll_device()
            update_metrics(data)
            total_w = data.get("dps", {}).get("132", "?")
            print(f"Poll OK: {total_w}W total")
        except Exception as e:
            print(f"Poll error: {e}")
        time.sleep(POLL_INTERVAL)
