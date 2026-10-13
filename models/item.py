from datetime import datetime, timedelta
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from extensions import db
from categories import SHELF_LIFE_DAYS

# status is "expiring_soon" once an item is this close to expires_at
EXPIRING_SOON = timedelta(days=1)

class Item(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] # get from model
    category: Mapped[str] = mapped_column(default="Other") # one of categories.CATEGORIES
    price: Mapped[float | None] # set by the frontend
    image: Mapped[str] = mapped_column(default="") # path to image file
    shelf_id: Mapped[int] = mapped_column(ForeignKey("shelf.id"))
    shelf: Mapped["Shelf"] = relationship(back_populates="items")

    # set by the cv model; None for items added by hand
    confidence: Mapped[float | None]
    capture_id: Mapped[int | None] = mapped_column(ForeignKey("capture.id"))
    capture: Mapped["Capture"] = relationship()

    # expiration tracking: stored_at is when the item first appeared,
    # removed_at is set once a capture no longer sees it
    stored_at: Mapped[datetime] = mapped_column(default=datetime.now)
    last_seen: Mapped[datetime] = mapped_column(default=datetime.now)
    removed_at: Mapped[datetime | None]
    expires_at_override: Mapped[datetime | None] # set by the frontend, wins over the category default

    @property
    def expires_at(self):
        if self.expires_at_override:
            return self.expires_at_override
        days = SHELF_LIFE_DAYS.get(self.category)
        return self.stored_at + timedelta(days=days) if days is not None else None

    @property
    def status(self):
        """safe, expiring_soon, expired, or unknown (no shelf life for the category)"""
        expires_at = self.expires_at
        if expires_at is None:
            return "unknown"
        now = datetime.now()
        if now >= expires_at:
            return "expired"
        if now >= expires_at - EXPIRING_SOON:
            return "expiring_soon"
        return "safe"

    def to_dict(self):
        iso = lambda d: d.isoformat() if d else None
        return {
            "id": self.id,
            "name": self.name,
            "stored_at": iso(self.stored_at),
            "status": self.status,
            "price": self.price,
            "category": self.category,
            "expires_at": iso(self.expires_at),
            "shelf_id": self.shelf_id,
            "image": self.image,
            "confidence": self.confidence,
            "last_seen": iso(self.last_seen),
            "removed_at": iso(self.removed_at),
        }
