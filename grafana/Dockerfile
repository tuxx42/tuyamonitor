FROM grafana/grafana:latest

COPY datasources.yml /etc/grafana/provisioning/datasources/datasources.yml
COPY dashboards.yml /etc/grafana/provisioning/dashboards/dashboards.yml
COPY power-dashboard.json /var/lib/grafana/dashboards/power-dashboard.json

ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin
ENV GF_SERVER_HTTP_PORT=3000
