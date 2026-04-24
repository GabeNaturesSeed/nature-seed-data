"""reconcile pre-existing model drift

Revision ID: fea5bbbdad5a
Revises: a159c3c3cf1e
Create Date: 2026-04-24 16:31:42.306535

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'fea5bbbdad5a'
down_revision: Union[str, Sequence[str], None] = 'a159c3c3cf1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — idempotent: safe to run on both fresh and pre-populated DBs."""
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_tables = set(inspector.get_table_names())

    def col_exists(table: str, col: str) -> bool:
        return col in {c["name"] for c in inspector.get_columns(table)}

    # ------------------------------------------------------------------
    # New tables (7 tables missing from the migration chain)
    # ------------------------------------------------------------------
    if 'competitor_domains' not in existing_tables:
        op.create_table('competitor_domains',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('domain', sa.String(length=300), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('discovered_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('keyword_overlap_count', sa.Integer(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain')
        )

    if 'gsc_query_performance' not in existing_tables:
        op.create_table('gsc_query_performance',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('page', sa.String(length=500), nullable=False),
        sa.Column('date', sa.String(length=10), nullable=False),
        sa.Column('device', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=10), nullable=False),
        sa.Column('impressions', sa.Integer(), nullable=False),
        sa.Column('clicks', sa.Integer(), nullable=False),
        sa.Column('ctr', sa.Float(), nullable=False),
        sa.Column('position', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('query', 'page', 'date', 'device', 'country', name='uq_gsc_row')
        )
        op.create_index(op.f('ix_gsc_query_performance_query'), 'gsc_query_performance', ['query'], unique=False)

    if 'media_index' not in existing_tables:
        op.create_table('media_index',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('wp_media_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('filename', sa.String(length=300), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('alt_text', sa.String(length=500), nullable=True),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=50), nullable=True),
        sa.Column('description_text', sa.Text(), nullable=True),
        sa.Column('indexed_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wp_media_id')
        )

    if 'orphan_references' not in existing_tables:
        op.create_table('orphan_references',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content_inventory_id', sa.Integer(), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=False),
        sa.Column('reference_value', sa.String(length=500), nullable=False),
        sa.Column('matched_inactive_product_id', sa.Integer(), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=False),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('user_decision_at', sa.DateTime(), nullable=True),
        sa.Column('user_notes', sa.Text(), nullable=True),
        sa.Column('redirect_target_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['content_inventory_id'], ['content_inventory.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'redirects' not in existing_tables:
        op.create_table('redirects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('target_url', sa.String(length=500), nullable=False),
        sa.Column('orphan_reference_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['orphan_reference_id'], ['orphan_references.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'refresh_queue' not in existing_tables:
        op.create_table('refresh_queue',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content_inventory_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('orphan_reference_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['content_inventory_id'], ['content_inventory.id'], ),
        sa.ForeignKeyConstraint(['orphan_reference_id'], ['orphan_references.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'refresh_history' not in existing_tables:
        op.create_table('refresh_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content_inventory_id', sa.Integer(), nullable=False),
        sa.Column('wp_post_id', sa.Integer(), nullable=False),
        sa.Column('brief_id', sa.Integer(), nullable=True),
        sa.Column('draft_id', sa.Integer(), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['brief_id'], ['brief_queue.id'], ),
        sa.ForeignKeyConstraint(['content_inventory_id'], ['content_inventory.id'], ),
        sa.ForeignKeyConstraint(['draft_id'], ['drafts.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    # ------------------------------------------------------------------
    # Missing columns on existing tables
    # SQLite does not support ALTER TABLE ADD CONSTRAINT or CREATE FOREIGN KEY
    # outside of batch mode. New FKs and unique constraints on existing tables
    # must be added via batch_alter_table (copy-and-move strategy).
    # For simple ADD COLUMN (no constraint), plain op.add_column works fine.
    # ------------------------------------------------------------------

    # brief_queue — new columns + new FK on keyword_candidate_id
    brief_queue_new_cols = {
        'keyword_candidate_id': not col_exists('brief_queue', 'keyword_candidate_id'),
        'is_refresh': not col_exists('brief_queue', 'is_refresh'),
        'original_wp_post_id': not col_exists('brief_queue', 'original_wp_post_id'),
    }
    if any(brief_queue_new_cols.values()):
        with op.batch_alter_table('brief_queue') as batch_op:
            if brief_queue_new_cols['keyword_candidate_id']:
                batch_op.add_column(sa.Column('keyword_candidate_id', sa.Integer(), nullable=True))
                batch_op.create_foreign_key(
                    'fk_brief_queue_keyword_candidate_id',
                    'keyword_candidates',
                    ['keyword_candidate_id'],
                    ['id'],
                )
            if brief_queue_new_cols['is_refresh']:
                batch_op.add_column(sa.Column('is_refresh', sa.Integer(), nullable=False, server_default='0'))
            if brief_queue_new_cols['original_wp_post_id']:
                batch_op.add_column(sa.Column('original_wp_post_id', sa.Integer(), nullable=True))

    # content_inventory
    if not col_exists('content_inventory', 'content_html'):
        op.add_column('content_inventory', sa.Column('content_html', sa.Text(), nullable=True))

    # drafts
    drafts_new_cols = {
        'image_assignments': not col_exists('drafts', 'image_assignments'),
        'meta_description': not col_exists('drafts', 'meta_description'),
        'reviewer_notes': not col_exists('drafts', 'reviewer_notes'),
    }
    for col_name, missing in drafts_new_cols.items():
        if missing:
            if col_name == 'image_assignments':
                op.add_column('drafts', sa.Column('image_assignments', sa.JSON(), nullable=True))
            elif col_name == 'meta_description':
                op.add_column('drafts', sa.Column('meta_description', sa.String(length=320), nullable=True))
            elif col_name == 'reviewer_notes':
                op.add_column('drafts', sa.Column('reviewer_notes', sa.Text(), nullable=True))

    # keyword_candidates — new columns + unique constraint on keyword
    kc_new_cols = {
        'difficulty_source': not col_exists('keyword_candidates', 'difficulty_source'),
        'gap_score': not col_exists('keyword_candidates', 'gap_score'),
        'best_ranking_url': not col_exists('keyword_candidates', 'best_ranking_url'),
        'best_ranking_position': not col_exists('keyword_candidates', 'best_ranking_position'),
        'competition_index': not col_exists('keyword_candidates', 'competition_index'),
        'priority_score': not col_exists('keyword_candidates', 'priority_score'),
        'enriched_at': not col_exists('keyword_candidates', 'enriched_at'),
    }
    # Check if the unique constraint on keyword is already present.
    # SQLite surfaces unique constraints as unique indexes; check both.
    keyword_uc_present = any(
        'keyword' in (uc.get('column_names') or [])
        for uc in inspector.get_unique_constraints('keyword_candidates')
    ) or any(
        'keyword' in (ix.get('column_names') or [])
        for ix in inspector.get_indexes('keyword_candidates')
        if ix.get('unique')
    )
    need_kc_batch = any(kc_new_cols.values()) or not keyword_uc_present
    if need_kc_batch:
        with op.batch_alter_table('keyword_candidates') as batch_op:
            if kc_new_cols['difficulty_source']:
                batch_op.add_column(sa.Column('difficulty_source', sa.String(length=50), nullable=True))
            if kc_new_cols['gap_score']:
                batch_op.add_column(sa.Column('gap_score', sa.Float(), nullable=True))
            if kc_new_cols['best_ranking_url']:
                batch_op.add_column(sa.Column('best_ranking_url', sa.String(length=500), nullable=True))
            if kc_new_cols['best_ranking_position']:
                batch_op.add_column(sa.Column('best_ranking_position', sa.Float(), nullable=True))
            if kc_new_cols['competition_index']:
                batch_op.add_column(sa.Column('competition_index', sa.Float(), nullable=True))
            if kc_new_cols['priority_score']:
                batch_op.add_column(sa.Column('priority_score', sa.Float(), nullable=True))
            if kc_new_cols['enriched_at']:
                batch_op.add_column(sa.Column('enriched_at', sa.DateTime(), nullable=True))
            if not keyword_uc_present:
                batch_op.create_unique_constraint('uq_keyword_candidates_keyword', ['keyword'])


def downgrade() -> None:
    """Downgrade is intentionally left as a no-op.

    This migration reconciles pre-existing schema drift that was present before
    Alembic tracking began. Rolling back would leave the database in an inconsistent
    state that predates version control. Drop the database and recreate from scratch
    if a clean slate is needed.
    """
    pass
