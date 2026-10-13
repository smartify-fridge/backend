import os
import requests

# Contract with the cv service:
#   POST {CV_URL}/analyze   multipart: image=<jpeg>
#   -> 200 {"items": [{"name": "milk", "confidence": 0.93, "category": "Dairy"}, ...]}  # category optional
CV_URL = os.environ.get("CV_URL")
CV_TIMEOUT = float(os.environ.get("CV_TIMEOUT", "30"))


class CVUnavailable(Exception):
    pass


def analyze(image_path):
    if not CV_URL:
        raise CVUnavailable("CV_URL is not set")

    try:
        with open(image_path, "rb") as f:
            response = requests.post(
                f"{CV_URL}/analyze",
                files={"image": (os.path.basename(image_path), f, "image/jpeg")},
                timeout=CV_TIMEOUT,
            )
    except requests.ConnectionError as e:
        raise CVUnavailable(f"could not reach cv service at {CV_URL}") from e

    response.raise_for_status()
    return response.json()["items"]
