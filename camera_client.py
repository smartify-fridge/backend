import os
import requests

# Each esp32 serves (see firmware/Projects/ESP32-Cam/driver/driver.ino):
#   GET {camera url}/image          -> 200 image/jpeg, the latest frame (retaken every 15s)
#   GET {camera url}/sensor/latest  -> 200 {"temperature": 4.1, "pressure": 1013.2, "humidity": 40.5, "gas": 12.3}
# The camera url defaults to its mDNS name, override CAMERA_URL to point at e.g. a local mock.
CAMERA_URL = os.environ.get("CAMERA_URL", "http://{camera}.local")
CAMERA_TIMEOUT = float(os.environ.get("CAMERA_TIMEOUT", "2.5"))


class CameraUnavailable(Exception):
    pass


def url(camera):
    return CAMERA_URL.format(camera=camera)


def get_image(camera):
    try:
        response = requests.get(f"{url(camera)}/image", timeout=CAMERA_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        raise CameraUnavailable(f"could not get image from {camera}: {e}") from e
    return response.content


def get_sensors(camera):
    # sensor data is optional, so a missing sensor shouldn't drop the capture
    try:
        response = requests.get(f"{url(camera)}/sensor/latest", timeout=CAMERA_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return {}
