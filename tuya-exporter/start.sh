#!/bin/bash
set -e

# Start Tailscale daemon in userspace networking mode (no TUN needed)
tailscaled --tun=userspace-networking --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# Wait for tailscaled to be ready
sleep 3

# Authenticate and accept routes (so we can reach the LAN subnet)
tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname=railway-tuya-exporter --accept-routes

echo "Tailscale is up. Status:"
tailscale status

# In userspace mode, we need to use the SOCKS5 proxy or tsnet
# Set up environment for the exporter to use Tailscale's proxy
export ALL_PROXY=socks5://localhost:1055/
export HTTP_PROXY=socks5://localhost:1055/

# Start the exporter
exec python3 exporter.py
