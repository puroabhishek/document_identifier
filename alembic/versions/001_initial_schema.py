"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_types",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("class_label", sa.String(200), unique=True, nullable=False),
        sa.Column(
            "subject_type",
            sa.Enum("business", "individual", name="subject_type_enum"),
            nullable=False,
        ),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("issuing_agency", sa.String(300), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_document_types_name", "document_types", ["name"])
    op.create_index("ix_document_types_class_label", "document_types", ["class_label"])

    op.create_table(
        "training_documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "document_type_id",
            sa.Integer,
            sa.ForeignKey("document_types.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("gcs_uri", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_training_documents_document_type_id", "training_documents", ["document_type_id"])

    op.create_table(
        "classification_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_content_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=True),
        sa.Column("classification_method", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "matched_type_id",
            sa.Integer,
            sa.ForeignKey("document_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("matched_type_name", sa.String(200), nullable=True),
        sa.Column("subject_type", sa.String(50), nullable=True),
        sa.Column("doc_ai_raw_response", sa.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_classification_logs_created_at", "classification_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("classification_logs")
    op.drop_table("training_documents")
    op.drop_index("ix_document_types_class_label", "document_types")
    op.drop_index("ix_document_types_name", "document_types")
    op.drop_table("document_types")
