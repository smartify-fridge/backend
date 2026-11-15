"""Import completed CV JSON snapshots into the existing inventory tables."""
import json
import math
from pathlib import Path

from extensions import db
from models.capture import Capture
from models.shelf import Shelf


def read_result(path):
    with Path(path).expanduser().open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("CV result must be a JSON object")
    result_id = data.get("result_id")
    if not isinstance(result_id, str) or not result_id.strip() or len(result_id) > 128:
        raise ValueError("CV result needs a non-empty result_id (up to 128 characters)")
    shelf_id = data.get("shelf_id")
    if type(shelf_id) is not int or shelf_id < 1:
        raise ValueError("CV result needs a positive integer shelf_id")
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("CV result needs an items list")
    image_path = data.get("image_path", "")
    if not isinstance(image_path, str):
        raise ValueError("image_path must be a string")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise ValueError("Each CV item needs a non-empty name")
        item["name"] = item["name"].strip()
        if "category" in item and not isinstance(item["category"], str):
            raise ValueError("Item category must be a string")
        confidence = item.get("confidence")
        if confidence is not None and (
            type(confidence) not in (int, float)
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError("Item confidence must be a number between 0 and 1")
    return data


def import_result_file(path, reconcile_shelf):
    """Import each result_id once, including across backend restarts.

    Call inside the Flask app context. A result is a full shelf snapshot,
    using the same reconciliation rules as the camera/CV HTTP pipeline.
    """
    try:
        data = read_result(path)
    except FileNotFoundError:
        return None  # The model may not have written its first result yet.
    source = f"json:{data['result_id']}"
    existing = Capture.query.filter_by(camera=source, status="done").first()
    if existing is not None:
        return None
    if db.session.get(Shelf, data["shelf_id"]) is None:
        raise ValueError(f"Unknown shelf_id: {data['shelf_id']}; create the shelf first")
    try:
        capture = Capture(
            camera=source,
            shelf_id=data["shelf_id"],
            image_path=data.get("image_path", ""),
            status="pending",
        )
        db.session.add(capture)
        db.session.flush()
        reconcile_shelf(capture, data["items"])
        capture.status = "done"
        db.session.commit()
        return capture.id
    except Exception:
        db.session.rollback()
        raise
