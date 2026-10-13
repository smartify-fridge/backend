from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db

class Capture(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    camera: Mapped[str]
    shelf_id: Mapped[int | None] = mapped_column(ForeignKey("shelf.id", ondelete="SET NULL"))
    image_path: Mapped[str]
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)
    status: Mapped[str] = mapped_column(default="pending") # pending, done, failed, cv_unavailable
    error: Mapped[str | None]

    # sensor readings from the esp32's /sensor/latest, if the pi sent them
    temperature: Mapped[float | None]
    pressure: Mapped[float | None]
    humidity: Mapped[float | None]
    gas: Mapped[float | None]
