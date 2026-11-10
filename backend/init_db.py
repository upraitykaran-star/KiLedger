"""Connect safely and create KiLedger indexes. Does not add or remove records."""
from .config import get_settings
from .database import connect


def main() -> None:
    settings = get_settings()
    client, _db = connect(settings.mongodb_uri, settings.database)
    client.close()
    print(f"MongoDB is reachable and indexes are ready for database '{settings.database}'.")


if __name__ == "__main__":
    main()
