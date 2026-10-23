import hashlib
import os
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, request, send_file
from werkzeug.utils import secure_filename

import camera_client
import categories
import cv_client
from extensions import db
from models.item import Item
from models.shelf import Shelf
from models.capture import Capture

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['UPLOAD_DIR'] = os.path.join(app.instance_path, "captures")
app.config['CAPTURE_INTERVAL'] = float(os.environ.get("CAPTURE_INTERVAL", "15")) # seconds between camera polls
db.init_app(app)


@app.after_request
def allow_flutter_web(response):
    origin = request.headers.get("Origin")
    allowed_origin = os.environ.get("FRONTEND_ORIGIN")
    if origin and (urlparse(origin).hostname in {"localhost", "127.0.0.1"} or origin == allowed_origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response

os.makedirs(app.config['UPLOAD_DIR'], exist_ok=True)
with app.app_context():
    db.create_all()


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

# shelf routes

@app.route("/shelves", methods=["GET"])
def shelves():
    shelves = Shelf.query.all()
    return {"shelves": [{shelf.name: shelf.id} for shelf in shelves]}

@app.route("/shelf/<int:id>", methods=["GET", "POST"])
def shelf(id):
    if (request.method == "POST"):
        data = request.get_json()
        shelf = Shelf.query.get_or_404(id)
        shelf.name = data.get("name", shelf.name)
        shelf.description = data.get("description", shelf.description)
        shelf.camera = data.get("camera", shelf.camera)
        db.session.commit()
        return {"message": "Shelf updated successfully."}, 200
    elif (request.method == "GET"):
        shelf = Shelf.query.get_or_404(id)
        return {
            "shelf": shelf.name,
            "description": shelf.description,
            "camera": shelf.camera,
            "items": [item.name for item in shelf.items if item.removed_at is None],
        }

@app.route("/shelf", methods=["POST"])
def create_shelf():
    data = request.get_json()
    new_shelf = Shelf(
        name=data["name"],
        description=data.get("description", ""),
        camera=data.get("camera"),
    )
    db.session.add(new_shelf)
    db.session.commit()
    return {"message": "Shelf created successfully.", "shelf_id": new_shelf.id}, 201

@app.route("/shelf/<int:id>", methods=["DELETE"])
def delete_shelf(id):
    shelf = Shelf.query.get_or_404(id)
    db.session.delete(shelf)
    db.session.commit()
    return {"message": "Shelf deleted successfully."}, 200

# item routes

@app.route("/items", methods=["GET"])
def items():
    # ?shelf_id=1 to filter by shelf, ?include_removed=true to include items taken off the shelf
    query = Item.query
    if "shelf_id" in request.args:
        query = query.filter_by(shelf_id=request.args.get("shelf_id", type=int))
    if request.args.get("include_removed", "").lower() != "true":
        query = query.filter_by(removed_at=None)
    return {"items": [item.to_dict() for item in query.all()]}

@app.route("/categories", methods=["GET"])
def categories_list():
    return {"categories": categories.CATEGORIES}

@app.route("/item/<int:id>", methods=["GET", "POST"])
def item(id):
    if (request.method == "POST"):
        data = request.get_json()
        item = Item.query.get_or_404(id)
        item.name = data.get("name", item.name)
        item.image = data.get("image", item.image)
        item.shelf_id = data.get("shelf_id", item.shelf_id)
        item.price = data.get("price", item.price)
        if "category" in data:
            item.category = categories.normalize(data["category"])
        if "expires_at" in data:
            item.expires_at_override = parse_datetime(data["expires_at"])
        db.session.commit()
        return {"message": "Item updated successfully."}, 200
    elif (request.method == "GET"):
        item = Item.query.get_or_404(id)
        return item.to_dict()

@app.route("/item", methods=["POST"])
def create_item():
    data = request.get_json()
    new_item = Item(
        name=data["name"],
        category=categories.normalize(data["category"]) if "category" in data else categories.categorize(data["name"]),
        price=data.get("price"),
        image=data.get("image", ""),
        shelf_id=data["shelf_id"],
        expires_at_override=parse_datetime(data.get("expires_at")),
    )
    db.session.add(new_item)
    db.session.commit()
    return {"message": "Item created successfully.", "item_id": new_item.id}, 201

@app.route("/item/<int:id>", methods=["DELETE"])
def delete_item(id):
    item = Item.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return {"message": "Item deleted successfully."}, 200


@app.route("/item/<int:id>/remove", methods=["POST"])
def remove_item_from_shelf(id):
    item = Item.query.get_or_404(id)
    if item.removed_at is None:
        item.removed_at = datetime.now()
        db.session.commit()
    return item.to_dict(), 200


@app.route("/item/<int:id>/restore", methods=["POST"])
def restore_item_to_shelf(id):
    item = Item.query.get_or_404(id)
    if item.removed_at is not None:
        item.removed_at = None
        db.session.commit()
    return item.to_dict(), 200


def parse_datetime(value):
    return datetime.fromisoformat(value) if value else None


# capture routes

@app.route("/capture", methods=["POST"])
def create_capture():
    # pull from the cameras now instead of waiting for the poller, ?camera=cam1 for just one
    cameras = [request.args["camera"]] if "camera" in request.args else mapped_cameras()
    captures, errors = {}, {}
    for camera in cameras:
        try:
            capture = poll_camera(camera, force=True)
        except camera_client.CameraUnavailable as e:
            errors[camera] = str(e)
            continue
        captures[camera] = capture.id
        start_processing(capture.id)
    return {"captures": captures, "errors": errors}, 202 if captures else 502

@app.route("/capture/<int:id>", methods=["GET"])
def capture(id):
    capture = Capture.query.get_or_404(id)
    return {
        "camera": capture.camera,
        "shelf_id": capture.shelf_id,
        "timestamp": capture.timestamp.isoformat(),
        "status": capture.status,
        "error": capture.error,
        "temperature": capture.temperature,
        "pressure": capture.pressure,
        "humidity": capture.humidity,
        "gas": capture.gas,
    }

@app.route("/capture/<int:id>/image", methods=["GET"])
def capture_image(id):
    capture = Capture.query.get_or_404(id)
    return send_file(capture.image_path, mimetype="image/jpeg")

@app.route("/capture/<int:id>/process", methods=["POST"])
def reprocess_capture(id):
    # re-run cv on a capture, e.g. one saved while the cv service was down
    Capture.query.get_or_404(id)
    process_capture(id)
    return capture(id)


def mapped_cameras():
    return [shelf.camera for shelf in Shelf.query.filter(Shelf.camera.isnot(None))]


# sha256 of the last frame pulled from each camera, the esp32 only retakes
# its frame every 15s so polling can return the same image twice
last_image_hash = {}

def poll_camera(camera, force=False):
    """Pull the latest frame and sensor readings from a camera and save them as a
    Capture. Returns None if the frame hasn't changed since the last poll."""
    image = camera_client.get_image(camera)
    digest = hashlib.sha256(image).hexdigest()
    if not force and last_image_hash.get(camera) == digest:
        return None
    last_image_hash[camera] = digest
    return save_capture(camera, image, camera_client.get_sensors(camera))


def save_capture(camera, image, sensors):
    timestamp = datetime.now()
    filename = secure_filename(f"{camera}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg")
    image_path = os.path.join(app.config['UPLOAD_DIR'], filename)
    with open(image_path, "wb") as f:
        f.write(image)

    shelf = Shelf.query.filter_by(camera=camera).first()
    capture = Capture(
        camera=camera,
        shelf_id=shelf.id if shelf else None,
        image_path=image_path,
        timestamp=timestamp,
        temperature=sensors.get("temperature"),
        pressure=sensors.get("pressure"),
        humidity=sensors.get("humidity"),
        gas=sensors.get("gas"),
    )
    db.session.add(capture)
    db.session.commit()
    return capture


def start_processing(capture_id):
    # cv can be slow, so don't block the poller or the request on it
    threading.Thread(target=process_capture, args=(capture_id,), daemon=True).start()


def poll_cameras_forever():
    while True:
        with app.app_context():
            for camera in mapped_cameras():
                try:
                    capture = poll_camera(camera)
                except camera_client.CameraUnavailable as e:
                    app.logger.warning(str(e))
                    continue
                except Exception:
                    app.logger.exception(f"polling {camera} failed")
                    continue
                if capture:
                    start_processing(capture.id)
        time.sleep(app.config['CAPTURE_INTERVAL'])


def process_capture(capture_id):
    with app.app_context():
        capture = db.session.get(Capture, capture_id)
        if capture.shelf_id is None:
            shelf = Shelf.query.filter_by(camera=capture.camera).first()
            if shelf is None:
                capture.status = "failed"
                capture.error = f"no shelf is mapped to camera {capture.camera}"
                db.session.commit()
                return
            capture.shelf_id = shelf.id

        try:
            detections = cv_client.analyze(capture.image_path)
        except cv_client.CVUnavailable as e:
            capture.status = "cv_unavailable"
            capture.error = str(e)
            db.session.commit()
            return
        except Exception as e:
            capture.status = "failed"
            capture.error = str(e)
            db.session.commit()
            return

        reconcile_shelf(capture, detections)
        capture.status = "done"
        capture.error = None
        db.session.commit()


def reconcile_shelf(capture, detections):
    """Diff the cv detections against the shelf's active items so existing
    items keep their id and stored_at (needed for expiration tracking)."""
    active = Item.query.filter_by(shelf_id=capture.shelf_id, removed_at=None).all()
    unmatched = {}
    for item in active:
        unmatched.setdefault(item.name, []).append(item)

    for detection in detections:
        name = detection["name"]
        if unmatched.get(name):
            # still on the shelf
            item = unmatched[name].pop(0)
        else:
            # newly added to the shelf
            category = detection.get("category")
            item = Item(
                name=name,
                category=categories.normalize(category) if category else categories.categorize(name),
                shelf_id=capture.shelf_id,
                stored_at=capture.timestamp,
            )
            db.session.add(item)
        item.image = capture.image_path
        item.confidence = detection.get("confidence")
        item.capture_id = capture.id
        item.last_seen = capture.timestamp

    # anything not seen in this capture was taken off the shelf
    for items in unmatched.values():
        for item in items:
            item.removed_at = capture.timestamp


if __name__ == "__main__":
    threading.Thread(target=poll_cameras_forever, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
