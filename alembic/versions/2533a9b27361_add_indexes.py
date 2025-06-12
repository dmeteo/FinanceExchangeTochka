from alembic import op
import sqlalchemy as sa

revision = '2533a9b27361'
down_revision = '58075008296b'
branch_labels = None
depends_on = None

def upgrade():
    # Orders
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_orders_ticker', 'orders', ['ticker'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_ticker_status', 'orders', ['ticker', 'status'])
    op.create_index('ix_orders_user_id_status', 'orders', ['user_id', 'status'])

    # Balances
    op.create_index('ix_balances_user_id_ticker', 'balances', ['user_id', 'ticker'])

    # Transactions
    op.create_index('ix_transactions_ticker', 'transactions', ['ticker'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])

def downgrade():
    op.drop_index('ix_orders_user_id', table_name='orders')
    op.drop_index('ix_orders_ticker', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_index('ix_orders_ticker_status', table_name='orders')
    op.drop_index('ix_orders_user_id_status', table_name='orders')
    op.drop_index('ix_balances_user_id_ticker', table_name='balances')
    op.drop_index('ix_transactions_ticker', table_name='transactions')
    op.drop_index('ix_transactions_created_at', table_name='transactions')