"""Securely promote an existing user to admin.

No passwords are created or printed. The account must already exist via the
normal /register flow. Run server-side with database access:

    python scripts/promote_admin.py --user alice
    python scripts/promote_admin.py --email alice@example.com

Requires DATABASE_URL (or POSTGRES_*) to point at the target database.
Never commit credentials; this script takes no password arguments.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func

from app.core.database import Base, SessionLocal, engine
from app.models import User


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Promote an existing user to admin (no passwords handled)."
    )
    parser.add_argument("--user", dest="username", default=None)
    parser.add_argument("--email", dest="email", default=None)
    args = parser.parse_args()

    if not args.username and not args.email:
        print("Provide --user USERNAME or --email EMAIL", file=sys.stderr)
        return 2

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        query = db.query(User)
        if args.username:
            identifier = args.username.strip().lower()
            user = query.filter(
                func.lower(User.username) == identifier
            ).first()
        else:
            identifier = args.email.strip().lower()
            user = query.filter(func.lower(User.email) == identifier).first()
        if not user:
            print(f"No such user: {identifier}", file=sys.stderr)
            return 1
        if user.role == "admin":
            print(f"{user.username} is already admin.")
            return 0
        user.role = "admin"
        db.commit()
        print(f"Promoted {user.username} ({user.email}) to admin.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
