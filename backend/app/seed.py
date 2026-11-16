from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from .config import settings
from .db import SessionLocal
from .models import Asset


def seed() -> None:
    if not settings.dev_mode:
        raise RuntimeError("Demo data can only be seeded in development")
    samples = [
        {
            "code": "WONIT-001",
            "name": "현장 실사용 노트북",
            "department": "operations",
            "location": "본관 2층",
            "qr_token": UUID("f2504440-4e8a-4a1c-bf39-e464e4ad42a0"),
        },
        {
            "code": "WONIT-002",
            "name": "자산관리용 태블릿",
            "department": "operations",
            "location": "본관 1층",
            "qr_token": UUID("7cbf341f-724d-4142-ae4c-d1e921721d8c"),
        },
    ]
    with SessionLocal.begin() as session:
        session.execute(insert(Asset).values(samples).on_conflict_do_nothing(index_elements=["code"]))


if __name__ == "__main__":
    seed()
