"""Initial schema with 16 tables and HNSW vector index

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-06 09:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Bật extension pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 1. units
    op.create_table(
        'units',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('office_location', sa.String(255), nullable=True)
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, index=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id'), nullable=True),
        sa.Column('cohort', sa.String(50), nullable=True),
        sa.Column('major', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False)
    )

    # 3. documents
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('issuer_unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id'), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # 4. document_versions
    op.create_table(
        'document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_no', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('file_url', sa.String(1000), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), nullable=True)
    )

    # 5. chunks
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('article', sa.String(255), nullable=True),
        sa.Column('clause', sa.String(255), nullable=True),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.Vector(1024), nullable=True),
        sa.Column('tsv', postgresql.TSVECTOR(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, index=True, nullable=False)
    )
    # HNSW & GIN indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_tsv_gin ON chunks USING gin (tsv);")

    # 6. chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('channel', sa.String(50), default='WEB', nullable=False)
    )

    # 7. messages
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('anonymized_content', sa.Text(), nullable=True),
        sa.Column('intent', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('fallback', postgresql.JSONB(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('model_version', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # 8. citations
    op.create_table(
        'citations',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('chunk_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chunks.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('quote', sa.Text(), nullable=False)
    )

    # 9. feedback
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('messages.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('rating', sa.String(50), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('is_reported_wrong', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # 10. announcements
    op.create_table(
        'announcements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id'), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('audience', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('publish_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    # 11. announcement_reads
    op.create_table(
        'announcement_reads',
        sa.Column('announcement_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('announcements.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('read_at', sa.DateTime(), nullable=False),
        sa.Column('channel', sa.String(50), default='WEB', nullable=False)
    )

    # 12. rooms
    op.create_table(
        'rooms',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('building', sa.String(50), index=True, nullable=False),
        sa.Column('capacity', sa.Integer(), index=True, nullable=False),
        sa.Column('room_type', sa.String(50), nullable=False),
        sa.Column('equipment', postgresql.JSONB(), nullable=False),
        sa.Column('opening_hours', sa.String(100), nullable=False)
    )

    # 13. class_sections
    op.create_table(
        'class_sections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('course_code', sa.String(50), nullable=False),
        sa.Column('course_name', sa.String(255), nullable=False),
        sa.Column('semester', sa.String(20), nullable=False),
        sa.Column('lecturer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
    )

    # 14. schedule_entries
    op.create_table(
        'schedule_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('class_sections.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), index=True, nullable=False),
        sa.Column('room_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rooms.id'), index=True, nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), index=True, nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=False)
    )

    # 15. services
    op.create_table(
        'services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('unit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('units.id'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('procedure', sa.Text(), nullable=False),
        sa.Column('form_urls', postgresql.JSONB(), nullable=False),
        sa.Column('opening_hours', sa.String(100), nullable=False),
        sa.Column('contact', sa.String(255), nullable=False)
    )

    # 16. query_clusters, audit_logs, eval_runs, eval_results
    op.create_table(
        'query_clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('sample_questions', postgresql.JSONB(), nullable=False),
        sa.Column('is_failed_cluster', sa.Boolean(), default=False, nullable=False)
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('target_type', sa.String(100), nullable=False),
        sa.Column('target_id', sa.String(255), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    op.create_table(
        'eval_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config', postgresql.JSONB(), nullable=False),
        sa.Column('commit_sha', sa.String(100), nullable=True),
        sa.Column('metrics_summary', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False)
    )

    op.create_table(
        'eval_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('eval_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', sa.String(100), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('eval_results')
    op.drop_table('eval_runs')
    op.drop_table('audit_logs')
    op.drop_table('query_clusters')
    op.drop_table('services')
    op.drop_table('schedule_entries')
    op.drop_table('class_sections')
    op.drop_table('rooms')
    op.drop_table('announcement_reads')
    op.drop_table('announcements')
    op.drop_table('feedback')
    op.drop_table('citations')
    op.drop_table('messages')
    op.drop_table('chat_sessions')
    op.drop_table('chunks')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('users')
    op.drop_table('units')

