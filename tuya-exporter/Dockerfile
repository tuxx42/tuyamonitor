FROM python:3.12-slim

# Install Tailscale
RUN apt-get update && apt-get install -y curl iptables \
    && curl -fsSL https://tailscale.com/install.sh | sh \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY tuya-exporter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tuya-exporter/exporter.py .
COPY tuya-exporter/start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]
