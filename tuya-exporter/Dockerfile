FROM python:3.12-slim

COPY tuya-exporter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tuya-exporter/exporter.py .

CMD ["python3", "exporter.py"]
