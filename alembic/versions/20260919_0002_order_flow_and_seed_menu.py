"""Remove phone, add branch, and seed the demo menu."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260919_0002"
down_revision = "20260829_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Keep this migration compatible with databases created from the initial
    # revision as well as local databases that may already contain orders.
    op.add_column("orders", sa.Column("branch", sa.String(length=120), nullable=True))
    op.execute("UPDATE orders SET branch = 'Ермошкина' WHERE branch IS NULL")
    op.alter_column("orders", "branch", nullable=False)
    op.drop_index("ix_orders_phone", table_name="orders")
    op.drop_column("orders", "phone")

    op.execute(
        """
        INSERT INTO dishes (id, name, description, price_minor, is_available)
        VALUES
          ('00000000-0000-0000-0000-000000000101', 'Острый гирос', 'Гирос с острым соусом', 45000, true),
          ('00000000-0000-0000-0000-000000000102', 'Классический гирос', 'Гирос с дзадзики', 42000, true),
          ('00000000-0000-0000-0000-000000000103', 'Картофель фри', 'Порция картофеля фри', 18000, true),
          ('00000000-0000-0000-0000-000000000104', 'Цезарь', 'Салат Цезарь с курицей', 38000, false)
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO drinks (id, name, volume_ml, price_minor, is_available)
        VALUES
          ('00000000-0000-0000-0000-000000000201', 'Кола', 500, 15000, true),
          ('00000000-0000-0000-0000-000000000202', 'Вода', 500, 10000, true),
          ('00000000-0000-0000-0000-000000000203', 'Апельсиновый сок', 500, 20000, false)
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.add_column("orders", sa.Column("phone", sa.String(length=32), nullable=True))
    op.execute("UPDATE orders SET phone = '' WHERE phone IS NULL")
    op.alter_column("orders", "phone", nullable=False)
    op.create_index("ix_orders_phone", "orders", ["phone"])
    op.drop_column("orders", "branch")
