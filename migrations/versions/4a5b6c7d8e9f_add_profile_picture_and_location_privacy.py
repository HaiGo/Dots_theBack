"""Add profile picture and location privacy features

Revision ID: 4a5b6c7d8e9f
Revises: 3f4c5d6e7f8a
Create Date: 2025-11-07 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a5b6c7d8e9f'
down_revision = '3f4c5d6e7f8a'
branch_labels = None
depends_on = None


def upgrade():
    # Create location_sharing_permission table
    op.create_table('location_sharing_permission',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('friend_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('user_id != friend_id', name='no_self_location_permission'),
        sa.ForeignKeyConstraint(['friend_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'friend_id', name='unique_location_permission')
    )
    
    # Add new columns to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('share_location_globally', sa.Boolean(), nullable=False, server_default='1'))


def downgrade():
    # Remove columns from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('share_location_globally')
        batch_op.drop_column('profile_picture')
    
    # Drop location_sharing_permission table
    op.drop_table('location_sharing_permission')

