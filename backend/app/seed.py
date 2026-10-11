"""Seed command:  python -m app.seed [--demo-athlete]

Loads FICTIONAL competitions, SYNTHETIC historical results and UNREVIEWED sample exercise templates.
--demo-athlete also adds a fictional athlete for the fixed demo identity (demo mode only).
"""
import sys

from app.config import DEMO_OWNER_ID, get_settings
from app.data.fixtures import seed_competitions, seed_demo_athlete, seed_templates
from app.db import SessionLocal


def main(argv: list[str]) -> int:
    settings = get_settings()
    with SessionLocal() as db:
        seed_templates(db)
        created = seed_competitions(db)
        print("Competitions: " + ("seeded fictional fixtures." if created else "already present, skipped."))
        if "--demo-athlete" in argv:
            if not settings.is_demo:
                print("Refusing to seed a demo athlete outside APP_MODE=demo.")
                return 1
            print("Demo athlete: " + ("created." if seed_demo_athlete(db, DEMO_OWNER_ID) else "already exists, skipped."))
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
