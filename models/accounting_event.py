from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column
from extensions import db


class AccountingEvent(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str]
    category: Mapped[str]
    stored_at: Mapped[datetime]
    price: Mapped[float]
    outcome: Mapped[str]  # consumed or discarded
    use_first: Mapped[bool] = mapped_column(default=False)
    occurred_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    voided_at: Mapped[datetime | None]

    def to_dict(self):
        occurred_at = self.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        return {
            "id": self.id,
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "stored_at": self.stored_at.isoformat(),
            "price": self.price,
            "outcome": self.outcome,
            "use_first": self.use_first,
            "occurred_at": occurred_at.isoformat(),
        }
