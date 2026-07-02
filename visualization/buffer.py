from collections import deque
from dataclasses import dataclass, field
import threading
import time


@dataclass
class SensorState:
    name: str
    threshold: float = 0.5
    enabled: bool = True
    current_value: float = 0.0
    active: bool = False
    timestamps: deque = field(default_factory=lambda: deque(maxlen=1000))
    samples: deque = field(default_factory=lambda: deque(maxlen=1000))


class SignalBuffer:

    def __init__(self, sensors):

        self.lock = threading.Lock()

        self.sensors = {
            name: SensorState(name=name)
            for name in sensors
        }


    def add_sample(self, sensor, value):

        with self.lock:

            s = self.sensors[sensor]

            now = time.time()

            s.timestamps.append(now)

            s.samples.append(value)

            s.current_value = value

            s.active = value >= s.threshold


    def set_threshold(self, sensor, threshold):

        with self.lock:

            self.sensors[sensor].threshold = threshold


    def snapshot(self):

        with self.lock:

            return {
                name: {
                    "time": list(sensor.timestamps),
                    "signal": list(sensor.samples),
                    "threshold": sensor.threshold,
                    "current": sensor.current_value,
                    "active": sensor.active,
                }
                for name, sensor in self.sensors.items()
            }