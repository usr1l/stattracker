"""add historical odds table

Revision ID: 8b1e1c6c1db1
Revises: 541b3fc3c566
Create Date: 2026-03-17 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b1e1c6c1db1"
down_revision = "541b3fc3c566"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "historical_odds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(), nullable=True),
        sa.Column("game_id", sa.String(), nullable=True),
        sa.Column("game_date", sa.String(), nullable=False),
        sa.Column("home_team", sa.String(), nullable=False),
        sa.Column("away_team", sa.String(), nullable=False),
        sa.Column("bookmaker", sa.String(), nullable=False),
        sa.Column("home_open_price", sa.Float(), nullable=True),
        sa.Column("away_open_price", sa.Float(), nullable=True),
        sa.Column("home_close_price", sa.Float(), nullable=True),
        sa.Column("away_close_price", sa.Float(), nullable=True),
        sa.Column("home_open_spread", sa.Float(), nullable=True),
        sa.Column("away_open_spread", sa.Float(), nullable=True),
        sa.Column("home_close_spread", sa.Float(), nullable=True),
        sa.Column("away_close_spread", sa.Float(), nullable=True),
        sa.Column("total_open", sa.Float(), nullable=True),
        sa.Column("total_close", sa.Float(), nullable=True),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historical_odds")),
        sa.UniqueConstraint(
            "game_date",
            "home_team",
            "away_team",
            "bookmaker",
            name=op.f("uq_historical_odds_game_date"),
        ),
    )
    with op.batch_alter_table("historical_odds", schema=None) as batch_op:
        batch_op.create_index(
            "idx_historical_odds_lookup",
            ["game_date", "home_team", "away_team"],
            unique=False,
        )
        batch_op.create_index("idx_historical_odds_season", ["season"], unique=False)


def downgrade():
    with op.batch_alter_table("historical_odds", schema=None) as batch_op:
        batch_op.drop_index("idx_historical_odds_season")
        batch_op.drop_index("idx_historical_odds_lookup")

    op.drop_table("historical_odds")
