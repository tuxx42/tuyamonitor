#!/bin/bash
set -e

# Start Tailscale daemon
tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# Wait for tailscaled to be ready
sleep 2

# Authenticate and accept routes (so we can reach the LAN subnet)
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=railway-tuya-exporter --accept-routes

echo "Tailscale is up. Status:"
tailscale status

# Start the exporter
exec python3 exporter.py
