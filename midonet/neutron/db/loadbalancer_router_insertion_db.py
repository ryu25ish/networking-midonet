# Copyright 2015 Midokura SARL
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sqlalchemy as sa
from sqlalchemy.orm import exc

from neutron.common import log
from neutron.db import model_base
from oslo_log import log as logging

from neutron_lbaas.extensions import loadbalancer as lb

LOG = logging.getLogger(__name__)


class PoolRouterAssociation(model_base.BASEV2):

    """Tracks Pool Router Association"""

    __tablename__ = 'midonet_pool_router_associations'

    pool_id = sa.Column(sa.String(36),
                        sa.ForeignKey('pools.id', ondelete="CASCADE"),
                        primary_key=True)
    router_id = sa.Column(sa.String(36),
                          sa.ForeignKey('routers.id', ondelete="CASCADE"))


class LoadbalancerRouterInsertionDbMixin(object):

    """Access methods for the pool_router_associations table."""

    @log.log
    def create_pool_router(self, context, pool_router):
        """Sets the router associated with the pool."""
        with context.session.begin(subtransactions=True):
            pool_router_db = PoolRouterAssociation(
                pool_id=pool_router['pool_id'],
                router_id=pool_router['router_id'])
            context.session.add(pool_router_db)

    @log.log
    def delete_pool_router(self, context, pool_id):
        """Delete the pool router association."""
        with context.session.begin(subtransactions=True):
            query = context.session.query(PoolRouterAssociation)
            query.filter(pool_id == pool_id).delete()

    @log.log
    def get_pool_router(self, context, pool_id):
        """Gets the pool router association."""
        try:
            query = context.session.query(PoolRouterAssociation)
            return query.filter(pool_id == pool_id).one()
        except exc.NoResultFound:
            return None

    @log.log
    def validate_pool_router_not_in_use(self, context, router_id):
        """Validate if router-id is not associated with any pool.

        If the router-id is already associated with a pool, raise an exception
        else just return.
        """
        query = context.session.query(PoolRouterAssociation)
        pool_router = query.filter_by(router_id=router_id).first()
        if pool_router:
            raise lb.PoolInUse(pool_id=pool_router.pool_id)
