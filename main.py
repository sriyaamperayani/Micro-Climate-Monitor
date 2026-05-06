import asyncio
import json
import logging
import os
import random
from collections import deque
from contextlib import suppress
from statistics import mean, pstdev
from typing import Deque, List
from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import datetime
from python_loki_logger import LokiLogger

app = FastAPI(title="Micro Climate Monitor")


class LokiPythonHandler(logging.Handler):
    def __init__(self, base_url: str, labels: dict[str, str]) -> None:
        super().__init__()
        self.client = LokiLogger(baseUrl=base_url, labels=labels)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            standard_keys = {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
            }
            custom_fields = {
                key: value for key, value in record.__dict__.items() if key not in standard_keys
            }
            extras = {
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            extras.update(custom_fields)
            if record.levelno >= logging.ERROR:
                self.client.error(message, extras=extras)
            elif record.levelno >= logging.WARNING:
                self.client.warn(message, extras=extras)
            elif record.levelno >= logging.INFO:
                self.client.info(message, extras=extras)
            else:
                self.client.debug(message, extras=extras)
        except Exception:
            # Never let logging delivery failures crash app execution.
            self.handleError(record)


def configure_logger() -> logging.Logger:
    logger = logging.getLogger("micro_climate_monitor")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(stream_handler)

    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    loki_handler = LokiPythonHandler(
        base_url=loki_url,
        labels={"app": "micro-climate-monitor", "service": "api"},
    )
    loki_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(loki_handler)
    return logger


logger = configure_logger()

class SensorReading(BaseModel):
    temperature: float = Field(..., description="Temperature in °C")
    humidity: float = Field(..., description="Relative humidity in %")
    pressure: float = Field(..., description="Pressure in hPa")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# In-memory store: automatically drops oldest entry past 1000 items.
readings: Deque[SensorReading] = deque(maxlen=1000)


def log_sensor_event(event: str, reading: SensorReading) -> None:
    payload = {
        "event": event,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "pressure": reading.pressure,
        "timestamp": reading.timestamp.isoformat(),
    }
    logger.info(
        json.dumps(payload),
        extra=payload,
    )


async def simulate_sensor_readings() -> None:
    while True:
        try:
            reading = SensorReading(
                temperature=round(random.uniform(18.0, 30.0), 2),
                humidity=round(random.uniform(35.0, 70.0), 2),
                pressure=round(random.uniform(995.0, 1025.0), 2),
            )
            readings.append(reading)
            log_sensor_event("simulated_reading", reading)
        except Exception:
            logger.exception("Sensor simulator iteration failed")
        await asyncio.sleep(5)


@app.on_event("startup")
async def start_background_simulator() -> None:
    app.state.simulator_task = asyncio.create_task(simulate_sensor_readings())
    logger.info("Sensor simulator started", extra={"interval_seconds": 5})


@app.on_event("shutdown")
async def stop_background_simulator() -> None:
    simulator_task = getattr(app.state, "simulator_task", None)
    if simulator_task:
        simulator_task.cancel()
        with suppress(asyncio.CancelledError):
            await simulator_task
    logger.info("Sensor simulator stopped")


@app.post("/readings", response_model=SensorReading)
def add_reading(reading: SensorReading):
    readings.append(reading)
    log_sensor_event("sensor_reading_accepted", reading)
    return reading

@app.get("/readings", response_model=List[SensorReading])
def list_readings():
    logger.info("Sensor readings listed", extra={"count": len(readings)})
    return list(readings)


@app.get("/anomalies")
def list_anomalies():
    readings_list = list(readings)
    if len(readings_list) < 2:
        return []

    temperatures = [reading.temperature for reading in readings_list]
    humidities = [reading.humidity for reading in readings_list]
    pressures = [reading.pressure for reading in readings_list]

    metric_stats = {
        "temperature": (mean(temperatures), pstdev(temperatures)),
        "humidity": (mean(humidities), pstdev(humidities)),
        "pressure": (mean(pressures), pstdev(pressures)),
    }

    anomalies = []
    for reading in readings_list:
        anomalous_fields = []
        for field_name in ("temperature", "humidity", "pressure"):
            value = getattr(reading, field_name)
            field_mean, field_std = metric_stats[field_name]
            if field_std == 0:
                continue
            if abs(value - field_mean) > 2 * field_std:
                anomalous_fields.append(field_name)

        if anomalous_fields:
            anomaly = reading.model_dump()
            anomaly["reason"] = ", ".join(anomalous_fields)
            anomalies.append(anomaly)

    logger.info("Anomalies computed", extra={"count": len(anomalies)})
    return anomalies