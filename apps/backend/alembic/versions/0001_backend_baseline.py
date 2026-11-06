"""Create the complete application schema from the SQLAlchemy models."""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op
from app.db.models import Base

revision: str = "0001_backend_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create extensions and all tables registered in ``Base.metadata``."""
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    """Drop application tables in dependency-safe order."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, checkfirst=True)
