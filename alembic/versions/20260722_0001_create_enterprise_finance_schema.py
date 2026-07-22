"""create enterprise finance schema

Revision ID: 20260722_0001
Revises:
Create Date: 2026-07-22 00:01:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260722_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "app_users",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_app_users_org_email"),
    )
    op.create_index("ix_app_users_organization_id", "app_users", ["organization_id"], unique=False)

    op.create_table(
        "suppliers",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("supplier_code", sa.String(length=40), nullable=False),
        sa.Column("legal_name", sa.String(length=180), nullable=False),
        sa.Column("tax_id", sa.String(length=30), nullable=False),
        sa.Column("default_category", sa.String(length=80), nullable=False),
        sa.Column("payment_terms_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "supplier_code", name="uq_suppliers_org_code"),
        sa.UniqueConstraint("organization_id", "tax_id", name="uq_suppliers_org_tax_id"),
    )
    op.create_index("ix_suppliers_legal_name", "suppliers", ["legal_name"], unique=False)
    op.create_index("ix_suppliers_organization_id", "suppliers", ["organization_id"], unique=False)

    op.create_table(
        "finance_documents",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=True),
        sa.Column("latest_run_id", sa.Integer(), nullable=True),
        sa.Column("latest_error_message", sa.Text(), nullable=True),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_documents_organization_id", "finance_documents", ["organization_id"], unique=False)
    op.create_index("ix_finance_documents_status", "finance_documents", ["status"], unique=False)

    op.create_table(
        "finance_document_versions",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=400), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("extraction_metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_users.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["finance_documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version_number", name="uq_finance_document_versions_doc_version"),
    )
    op.create_index("ix_finance_document_versions_checksum", "finance_document_versions", ["checksum"], unique=False)
    op.create_index("ix_finance_document_versions_document_id", "finance_document_versions", ["document_id"], unique=False)
    op.create_index("ix_finance_document_versions_organization_id", "finance_document_versions", ["organization_id"], unique=False)
    op.create_index("ix_finance_document_versions_processing_status", "finance_document_versions", ["processing_status"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_id", sa.Integer(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_node", sa.String(length=80), nullable=True),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("final_action", sa.String(length=40), nullable=True),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["finance_documents.id"]),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["app_users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["version_id"], ["finance_document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_document_id", "agent_runs", ["document_id"], unique=False)
    op.create_index("ix_agent_runs_idempotency_key", "agent_runs", ["idempotency_key"], unique=False)
    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"], unique=False)
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"], unique=False)
    op.create_index("ix_agent_runs_thread_id", "agent_runs", ["thread_id"], unique=True)
    op.create_index("ix_agent_runs_version_id", "agent_runs", ["version_id"], unique=False)

    op.create_table(
        "approval_requests",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("request_payload_json", sa.JSON(), nullable=False),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("edited_fields_json", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["app_users.id"]),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["app_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_agent_run_id", "approval_requests", ["agent_run_id"], unique=False)
    op.create_index("ix_approval_requests_organization_id", "approval_requests", ["organization_id"], unique=False)
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"], unique=False)

    op.create_table(
        "draft_pre_entries",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_name", sa.String(length=180), nullable=False),
        sa.Column("document_number", sa.String(length=80), nullable=False),
        sa.Column("issue_date", sa.String(length=20), nullable=True),
        sa.Column("due_date", sa.String(length=20), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_run_id", name="uq_draft_pre_entries_run"),
    )
    op.create_index("ix_draft_pre_entries_agent_run_id", "draft_pre_entries", ["agent_run_id"], unique=False)
    op.create_index("ix_draft_pre_entries_organization_id", "draft_pre_entries", ["organization_id"], unique=False)

    op.create_table(
        "tool_executions",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("agent_run_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("tool_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("arguments_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_executions_agent_run_id", "tool_executions", ["agent_run_id"], unique=False)
    op.create_index("ix_tool_executions_organization_id", "tool_executions", ["organization_id"], unique=False)

    op.create_table(
        "llm_executions",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("agent_run_id", sa.Integer(), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("request_payload_json", sa.JSON(), nullable=False),
        sa.Column("response_payload_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["finance_documents.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["app_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_executions_organization_id", "llm_executions", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_llm_executions_organization_id", table_name="llm_executions")
    op.drop_table("llm_executions")
    op.drop_index("ix_tool_executions_organization_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_agent_run_id", table_name="tool_executions")
    op.drop_table("tool_executions")
    op.drop_index("ix_draft_pre_entries_organization_id", table_name="draft_pre_entries")
    op.drop_index("ix_draft_pre_entries_agent_run_id", table_name="draft_pre_entries")
    op.drop_table("draft_pre_entries")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_organization_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_agent_run_id", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_agent_runs_version_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_thread_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_organization_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_idempotency_key", table_name="agent_runs")
    op.drop_index("ix_agent_runs_document_id", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_finance_document_versions_processing_status", table_name="finance_document_versions")
    op.drop_index("ix_finance_document_versions_organization_id", table_name="finance_document_versions")
    op.drop_index("ix_finance_document_versions_document_id", table_name="finance_document_versions")
    op.drop_index("ix_finance_document_versions_checksum", table_name="finance_document_versions")
    op.drop_table("finance_document_versions")
    op.drop_index("ix_finance_documents_status", table_name="finance_documents")
    op.drop_index("ix_finance_documents_organization_id", table_name="finance_documents")
    op.drop_table("finance_documents")
    op.drop_index("ix_suppliers_organization_id", table_name="suppliers")
    op.drop_index("ix_suppliers_legal_name", table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_app_users_organization_id", table_name="app_users")
    op.drop_table("app_users")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
