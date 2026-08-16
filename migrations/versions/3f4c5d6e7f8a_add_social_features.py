"""Add social features: userid, phone, location, and friendship

Revision ID: 3f4c5d6e7f8a
Revises: 2e6bd9840883
Create Date: 2025-11-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f4c5d6e7f8a'
down_revision = '2e6bd9840883'
branch_labels = None
depends_on = None


def upgrade():
    # Create friendship table
    op.create_table('friendship',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('friend_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('user_id != friend_id', name='no_self_friendship'),
        sa.ForeignKeyConstraint(['friend_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'friend_id', name='unique_friendship')
    )
    
    # Add new columns to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('userid', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('phone_number', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('last_location_update', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_user_userid'), ['userid'], unique=True)
        batch_op.create_index(batch_op.f('ix_user_phone_number'), ['phone_number'], unique=False)


def downgrade():
    # Remove indexes and columns from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_phone_number'))
        batch_op.drop_index(batch_op.f('ix_user_userid'))
        batch_op.drop_column('last_location_update')
        batch_op.drop_column('longitude')
        batch_op.drop_column('latitude')
        batch_op.drop_column('phone_number')
        batch_op.drop_column('userid')
    
    # Drop friendship table
    op.drop_table('friendship')

