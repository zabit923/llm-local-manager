"""Create menu and order tables.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


order_status = postgresql.ENUM(
    "pending",
    "confirmed",
    "preparing",
    "ready",
    "delivering",
    "completed",
    "cancelled",
    name="order_status",
    create_type=False,
)
delivery_type = postgresql.ENUM(
    "pickup",
    "delivery",
    name="delivery_type",
    create_type=False,
)
payment_method = postgresql.ENUM(
    "cash",
    "card",
    name="payment_method",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    order_status.create(bind, checkfirst=True)
    delivery_type.create(bind, checkfirst=True)
    payment_method.create(bind, checkfirst=True)

    op.create_table(
        "dishes",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("price_minor >= 0", name=op.f("ck_dishes_price_minor_non_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dishes")),
    )
    op.create_index(op.f("ix_dishes_name"), "dishes", ["name"])
    op.create_index(op.f("ix_dishes_category"), "dishes", ["category"])

    op.create_table(
        "drinks",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("volume_ml", sa.Integer(), nullable=True),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("is_available", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("price_minor >= 0", name=op.f("ck_drinks_price_minor_non_negative")),
        sa.CheckConstraint("volume_ml IS NULL OR volume_ml > 0", name=op.f("ck_drinks_volume_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drinks")),
    )
    op.create_index(op.f("ix_drinks_name"), "drinks", ["name"])

    op.create_table(
        "orders",
        sa.Column("status", order_status, server_default="pending", nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("delivery_type", delivery_type, server_default="delivery", nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("payment_method", payment_method, server_default="cash", nullable=False),
        sa.Column("total_price_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_phone"), "orders", ["phone"])

    op.create_table(
        "order_items",
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dish_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("drink_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_minor", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_order_items_quantity_positive")),
        sa.CheckConstraint("unit_price_minor >= 0", name=op.f("ck_order_items_unit_price_minor_non_negative")),
        sa.CheckConstraint(
            "(dish_id IS NOT NULL AND drink_id IS NULL) OR (dish_id IS NULL AND drink_id IS NOT NULL)",
            name=op.f("ck_order_items_exactly_one_menu_item"),
        ),
        sa.ForeignKeyConstraint(["dish_id"], ["dishes.id"], name=op.f("fk_order_items_dish_id_dishes"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["drink_id"], ["drinks.id"], name=op.f("fk_order_items_drink_id_drinks"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"])
    op.create_index(op.f("ix_order_items_dish_id"), "order_items", ["dish_id"])
    op.create_index(op.f("ix_order_items_drink_id"), "order_items", ["drink_id"])


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("drinks")
    op.drop_table("dishes")

    bind = op.get_bind()
    payment_method.drop(bind, checkfirst=True)
    delivery_type.drop(bind, checkfirst=True)
    order_status.drop(bind, checkfirst=True)
