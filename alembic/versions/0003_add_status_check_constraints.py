"""add status check constraints

Revision ID: 0003_add_status_check_constraints
Revises: 0002_add_user_updated_at
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_add_status_check_constraints"
down_revision: str | None = "0002_add_user_updated_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE users SET status = lower(status)")
    op.execute("UPDATE subscriptions SET status = lower(status)")
    op.execute("UPDATE devices SET status = lower(status)")
    op.execute("UPDATE payments SET status = lower(status)")
    op.execute("UPDATE vpn_servers SET status = lower(status)")

    op.create_check_constraint(
        "ck_users_status",
        "users",
        "status IN ('active', 'blocked')",
    )
    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status IN ('trial', 'active', 'expired', 'cancelled')",
    )
    op.create_check_constraint(
        "ck_devices_status",
        "devices",
        "status IN ('active', 'revoked')",
    )
    op.create_check_constraint(
        "ck_payments_status",
        "payments",
        "status IN ('pending', 'paid', 'failed', 'refunded')",
    )
    op.create_check_constraint(
        "ck_vpn_servers_status",
        "vpn_servers",
        "status IN ('active', 'maintenance', 'disabled')",
    )
    op.create_check_constraint(
        "ck_vpn_servers_load_non_negative",
        "vpn_servers",
        "load >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_vpn_servers_load_non_negative", "vpn_servers", type_="check")
    op.drop_constraint("ck_vpn_servers_status", "vpn_servers", type_="check")
    op.drop_constraint("ck_payments_status", "payments", type_="check")
    op.drop_constraint("ck_devices_status", "devices", type_="check")
    op.drop_constraint("ck_subscriptions_status", "subscriptions", type_="check")
    op.drop_constraint("ck_users_status", "users", type_="check")
