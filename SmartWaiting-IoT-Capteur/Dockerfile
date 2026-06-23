FROM python:3.11-slim

WORKDIR /app

COPY sensor_simulator.py .

RUN mkdir -p data

ENV BACKEND_URL=http://backend:8000/api/occupancy/
ENV INTERVAL=30

CMD ["sh", "-c", "while true; do python sensor_simulator.py; sleep ${INTERVAL}; done"]
