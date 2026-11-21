"""Create KiLedger's MySQL tables. Does not add or remove records."""
from sqlalchemy import text

from .config import get_settings
from .database import create_database, init_database


def main() -> None:
    settings = get_settings()
    engine, _factory = create_database(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        init_database(engine)
        print("MySQL is reachable and KiLedger tables are ready.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
