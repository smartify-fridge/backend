from sqlalchemy.orm import Mapped, mapped_column, relationship
from .item import Item
from extensions import db

class Shelf(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    camera: Mapped[str | None] = mapped_column(unique=True) # mDNS name of the esp32 watching this shelf, e.g. "cam1"
    items: Mapped[list[Item]] = relationship(back_populates="shelf", cascade="all, delete-orphan")
