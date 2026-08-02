"""add video_url to jobs

Revision ID: b4e8c1a92f03
Revises: 8612ca46536f
Create Date: 2026-08-02 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8c1a92f03"
down_revision: Union[str, Sequence[str], None] = "8612ca46536f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("video_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "video_url")
