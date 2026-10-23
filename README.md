# backend
Flask backend + db for smartify fridge

## Running
```
uv sync
CV_URL=http://localhost:8000 uv run backend.py
```
Runs on port 5000. If `CV_URL` is unset or unreachable, captures are still saved with
status `cv_unavailable`; re-run them later with `POST /capture/<id>/process`.
Data is stored in the local SQLite `instance/project.db` by default. Set
`DATABASE_URL` to use another SQLAlchemy database URL.
Flutter web on localhost is allowed to call the API. For a web frontend hosted
elsewhere, set `FRONTEND_ORIGIN` to its exact origin (for example,
`http://192.168.1.10:8080`). This only configures browser access; item data and
freshness responses are unchanged.

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

## Removing items and Accounting
Updated: 2026-10-23

`POST /item/<id>/remove` marks an item as removed from inventory. The request
body is optional. To record why it was removed, send either
`{"outcome":"consumed","use_first":true}` or `{"outcome":"discarded"}`.
An outcome creates an Accounting event with the item's name, category, price,
and storage time at removal. If the item has no price, the event records `0`.
Removing an item without an outcome creates no Accounting event. An item that
was already removed cannot be assigned an outcome retroactively.

`POST /item/<id>/restore` returns the item to inventory and voids its active
Accounting event. Both remove and restore return the item and can be repeated
without creating duplicate events.

`GET /accounting/events` returns active events for the frontend to group by
week or month. Each event includes `occurred_at`, the removal date and time
in ISO 8601 format with a UTC offset (for example,
`"2026-10-23T18:30:00+00:00"`). Events voided by a restore are excluded.
