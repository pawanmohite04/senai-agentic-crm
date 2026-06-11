"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("contacts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("name", sa.String(255)), sa.Column("company", sa.String(255)), sa.Column("status", sa.String(30), nullable=False), sa.Column("account_value", sa.Numeric(12, 2), nullable=False), sa.Column("churn_risk_score", sa.Float(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("last_contact_at", sa.DateTime()))
    op.create_index("ix_contacts_email", "contacts", ["email"])
    op.create_table("threads", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("thread_id", sa.String(255), nullable=False, unique=True), sa.Column("subject", sa.String(500)), sa.Column("sender_email", sa.String(320), sa.ForeignKey("contacts.email")), sa.Column("first_seen_at", sa.DateTime(), nullable=False), sa.Column("last_updated_at", sa.DateTime(), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("assigned_to", sa.String(255)))
    op.create_index("ix_threads_sender_email", "threads", ["sender_email"])
    op.create_index("ix_threads_thread_id", "threads", ["thread_id"])
    op.create_table("emails", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("thread_id", sa.Integer(), sa.ForeignKey("threads.id")), sa.Column("message_id", sa.String(255), nullable=False, unique=True), sa.Column("sender", sa.String(320), nullable=False), sa.Column("subject", sa.String(500), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("timestamp", sa.DateTime(), nullable=False), sa.Column("sentiment_score", sa.Float(), nullable=False), sa.Column("category", sa.String(50), nullable=False), sa.Column("urgency", sa.String(20), nullable=False), sa.Column("requires_human", sa.Boolean(), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("priority_score", sa.Float(), nullable=False), sa.Column("raw_entities", sa.JSON(), nullable=False), sa.Column("status", sa.String(30), nullable=False))
    op.create_index("ix_emails_sender_timestamp", "emails", ["sender", "timestamp"])
    op.create_index("ix_emails_category_urgency", "emails", ["category", "urgency"])
    op.create_table("actions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id")), sa.Column("agent_reasoning_log", sa.JSON(), nullable=False), sa.Column("action_type", sa.String(50), nullable=False), sa.Column("proposed_content", sa.Text()), sa.Column("is_approved", sa.Boolean(), nullable=False), sa.Column("approved_by", sa.String(255)), sa.Column("executed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("knowledge_chunks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_doc", sa.String(255), nullable=False), sa.Column("chunk_text", sa.Text(), nullable=False), sa.Column("embedding", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("web_intelligence_cache", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source_url", sa.String(1000), nullable=False), sa.Column("target_entity", sa.String(255), nullable=False), sa.Column("scraped_data", sa.JSON(), nullable=False), sa.Column("scraped_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=False))
    op.create_table("audit_log", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", sa.String(255), nullable=False), sa.Column("action", sa.String(120), nullable=False), sa.Column("performed_by", sa.String(255), nullable=False), sa.Column("timestamp", sa.DateTime(), nullable=False), sa.Column("diff", sa.JSON(), nullable=False))
    op.create_table("processing_jobs", sa.Column("id", sa.String(64), primary_key=True), sa.Column("message_id", sa.String(255), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("result", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))


def downgrade():
    for table in ["processing_jobs", "audit_log", "web_intelligence_cache", "knowledge_chunks", "actions", "emails", "threads", "contacts"]:
        op.drop_table(table)
