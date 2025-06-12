from alembic import op
import sqlalchemy as sa

revision = 'b208c4d76f7b'
down_revision = 'bebcf6094b2a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('balances', sa.Column('frozen', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('balances', 'frozen')