import asyncio

from app.database.init_db import init_db
from app.database.seed import seed_source_registry
from app.database.session import SessionLocal
from app.services.live_data import sync_live_data


def main():
    init_db()
    db = SessionLocal()
    try:
        seed_source_registry(db)
        asyncio.run(sync_live_data(db, force=True))
    finally:
        db.close()


if __name__ == '__main__':
    main()
