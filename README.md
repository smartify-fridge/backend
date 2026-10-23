# backend
Flask backend + db for smartify fridge

## Running
```
uv sync
CV_URL=http://localhost:8000 uv run backend.py
```
Runs on port 5000. If `CV_URL` is unset or unreachable, captures are still saved with
status `cv_unavailable`; re-run them later with `POST /capture/<id>/process`.

## Image pipeline
The backend polls the esp32 of every shelf with a `camera` set every `CAPTURE_INTERVAL`
seconds (default 15), hitting `GET http://<camera>.local/image` and `/sensor/latest`.
Frames identical to the last one from that camera are skipped. Each new capture is sent to
the cv service, and the detected items are diffed against the shelf's current items.

`POST /capture` (optional `?camera=cam1`) pulls from the cameras immediately.
Set `CAMERA_URL` (default `http://{camera}.local`) to point at something other than mDNS,
and `CAMERA_TIMEOUT` (default 2.5s) to change the request timeout.

CV service contract:
```
POST {CV_URL}/analyze   multipart: image=<jpeg>
-> 200 {"items": [{"name": "milk", "confidence": 0.93, "category": "Dairy"}, ...]}  # category optional
```

## Items (for the frontend)
`GET /items` (optional `?shelf_id=1`, `?include_removed=true`) and `GET /item/<id>` return:
```
{"id": 1, "name": "milk", "stored_at": "2026-10-13T14:08:45", "status": "safe",
 "price": null, "category": "Dairy", "expires_at": "2026-10-20T14:08:45", ...}
```
- `status`: `safe`, `expiring_soon` (within 1 day), `expired`, or `unknown` (category `Other`, no expires_at)
- `category`: one of `GET /categories`
- `POST /item/<id>` accepts `price`, `category`, and `expires_at` (ISO datetime, overrides the category default)
