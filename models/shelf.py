from sqlalchemy.orm import Mapped, mapped_column
from item import Item
from backend import db

class Shelf(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str]
    items: Mapped[list[Item]] = mapped_column(default=list)
