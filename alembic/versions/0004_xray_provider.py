"""add xray provider schema

Revision ID: 0004_xray_provider
Revises: 0003_status_checks
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_xray_provider"
down_revision: str | None = "0003_status_checks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vpn_servers", sa.Column("port", sa.Integer(), nullable=True))
    op.add_column(
        "vpn_servers",
        sa.Column("protocol", sa.String(length=16), server_default="vless", nullable=False),
    )
    op.add_column(
        "vpn_servers",
        sa.Column("transport", sa.String(length=16), server_default="tcp", nullable=False),
    )
    op.add_column(
        "vpn_servers",
        sa.Column("security", sa.String(length=16), server_default="reality", nullable=False),
    )
    op.add_column("vpn_servers", sa.Column("public_key", sa.String(length=128), nullable=True))
    op.add_column("vpn_servers", sa.Column("server_name", sa.String(length=255), nullable=True))
    op.add_column("vpn_servers", sa.Column("short_id", sa.String(length=32), nullable=True))
    op.add_column(
        "vpn_servers",
        sa.Column("fingerprint", sa.String(length=32), server_default="chrome", nullable=False),
    )
    op.add_column(
        "vpn_servers",
        sa.Column("flow", sa.String(length=64), server_default="xtls-rprx-vision", nullable=True),
    )
    op.add_column(
        "vpn_servers",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_vpn_servers_port",
        "vpn_servers",
        "port IS NULL OR (port > 0 AND port <= 65535)",
    )

    op.create_table(
        "vpn_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("vpn_servers.id"), nullable=False),
        sa.Column("credential_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'revoked')", name="ck_vpn_credentials_status"),
    )
    op.create_index("ix_vpn_credentials_user_id", "vpn_credentials", ["user_id"], unique=False)
    op.create_index("ix_vpn_credentials_server_id", "vpn_credentials", ["server_id"], unique=False)
    op.create_index(
        "ix_vpn_credentials_credential_id",
        "vpn_credentials",
        ["credential_id"],
        unique=True,
    )
    op.create_index(
        "ix_vpn_credentials_user_server_status",
        "vpn_credentials",
        ["user_id", "server_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_vpn_credentials_user_server_status", table_name="vpn_credentials")
    op.drop_index("ix_vpn_credentials_credential_id", table_name="vpn_credentials")
    op.drop_index("ix_vpn_credentials_server_id", table_name="vpn_credentials")
    op.drop_index("ix_vpn_credentials_user_id", table_name="vpn_credentials")
    op.drop_table("vpn_credentials")

    op.drop_constraint("ck_vpn_servers_port", "vpn_servers", type_="check")
    op.drop_column("vpn_servers", "updated_at")
    op.drop_column("vpn_servers", "flow")
    op.drop_column("vpn_servers", "fingerprint")
    op.drop_column("vpn_servers", "short_id")
    op.drop_column("vpn_servers", "server_name")
    op.drop_column("vpn_servers", "public_key")
    op.drop_column("vpn_servers", "security")
    op.drop_column("vpn_servers", "transport")
    op.drop_column("vpn_servers", "protocol")
    op.drop_column("vpn_servers", "port")
