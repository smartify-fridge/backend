# backend
Flask backend + db for smartify fridge

## Running
```
uv sync
CV_URL=http://localhost:8000 uv run backend.py
```
Runs on port 5000. If `CV_URL` is unset or unreachable, captures are still saved with
status `cv_unavailable`; re-run them later with `POST /capture/<id>/process`.
Flutter web on localhost is allowed to call the API. For a web frontend hosted
elsewhere, set `FRONTEND_ORIGIN` to its exact origin (for example,
`http://192.168.1.10:8080`). This only configures browser access; item data and
freshness responses are unchanged.

## Image pipeline
The pi uploads to `POST /capture` (multipart: `camera`, `image`, optional `sensors` JSON).
The capture is mapped to a shelf via `Shelf.camera`, sent to the cv service, and the
detected items are diffed against the shelf's current items.

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
- `POST /item/<id>/remove` marks an item as no longer in inventory by setting
  `removed_at`. `POST /item/<id>/restore` clears it for undo. Both return the
  item and are safe to repeat. Neither records a reason for removal.
