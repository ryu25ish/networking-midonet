# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""LBaaS router insertion

Revision ID: 3aa7e7bee966
Revises: 421564f630b1
Create Date: 2015-03-17 07:00:19.852536

"""

# revision identifiers, used by Alembic.
revision = '3aa7e7bee966'
down_revision = '421564f630b1'

from alembic import op
import sqlalchemy as sa

# Should only be pool mappings
INSERT_POOL_ROUTER_ASSOC_STATEMENT = (
    "insert into midonet_pool_router_associations "
    "select "
    "m.resource_id as pool_id, m.router_id "
    "from midonet_servicerouterbindings m"
)


def upgrade():
    op.create_table(
        'midonet_pool_router_associations',
        sa.Column('pool_id', sa.String(length=36), nullable=False,
                  primary_key=True),
        sa.Column('router_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['pool_id'], ['pools.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['router_id'], ['routers.id'],
                                ondelete='CASCADE')
    )
    op.execute(INSERT_POOL_ROUTER_ASSOC_STATEMENT)
    op.drop_table('midonet_routerservicetypebindings')
    op.drop_table('midonet_servicerouterbindings')
