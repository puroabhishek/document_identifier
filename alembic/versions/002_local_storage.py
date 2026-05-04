"""local storage — rename gcs_uri/doc_ai_raw_response, add extracted_text

Revision ID: 002
Revises: 001
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("training_documents") as batch_op:
        batch_op.alter_column("gcs_uri", new_column_name="storage_uri")
        batch_op.add_column(sa.Column("extracted_text", sa.Text, nullable=True))

    with op.batch_alter_table("classification_logs") as batch_op:
        batch_op.alter_column("doc_ai_raw_response", new_column_name="llm_raw_response")


def downgrade() -> None:
    with op.batch_alter_table("training_documents") as batch_op:
        batch_op.drop_column("extracted_text")
        batch_op.alter_column("storage_uri", new_column_name="gcs_uri")

    with op.batch_alter_table("classification_logs") as batch_op:
        batch_op.alter_column("llm_raw_response", new_column_name="doc_ai_raw_response")
