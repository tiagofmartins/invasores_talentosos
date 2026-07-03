import threading
import random
import time

from visualization.buffer import SignalBuffer
from visualization.dashboard import run_dashboard


buffer = SignalBuffer(
    [
        "Sensor 1",
        "Sensor 2",
        "Sensor 3",
    ]
)


def fake_sensor():

    while True:

        buffer.add_sample(
            "Sensor 1",
            random.random()
        )

        buffer.add_sample(
            "Sensor 2",
            random.random()
        )

        buffer.add_sample(
            "Sensor 3",
            random.random()
        )

        time.sleep(0.02)



if __name__ == "__main__":

    threading.Thread(
        target=fake_sensor,
        daemon=True
    ).start()


    run_dashboard(buffer)