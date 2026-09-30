from sqlalchemy.orm import Mapped, mapped_column
from backend import db

class Item(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] # get from model
    image: Mapped[str] # path to image file