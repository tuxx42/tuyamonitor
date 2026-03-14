#!/bin/bash
set -e

# Start Tailscale daemon in userspace networking mode (no TUN/iptables needed)
tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# Wait for tailscaled to be ready
sleep 3

# Authenticate and accept routes so we can reach the LAN subnet via locco
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=railway-tuya-exporter --accept-routes

echo "Tailscale is up. Status:"
tailscale status

# Start the exporter (uses tailscale nc internally for TCP proxy)
exec python3 exporter.py
