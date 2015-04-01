# Copyright (C) 2015 Midokura SARL
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from midonet.neutron.db import db_util
from midonet.neutron.db import loadbalancer_router_insertion_db as lbri_db
from midonet.neutron.db import task_db as task

from neutron.common import exceptions as n_exc
from neutron.i18n import _LI, _LE
from neutron_lbaas.db.loadbalancer import loadbalancer_db as ldb
from neutron.plugins.common import constants

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class LoadBalancerPlugin(ldb.LoadBalancerPluginDb,
                         lbri_db.LoadbalancerRouterInsertionDbMixin):
    """Implementation of the Neutron Loadbalancer Service Plugin.

    This class manages the workflow of LBaaS request/response.
    Most DB related works are implemented in class
    loadbalancer_db.LoadBalancerPluginDb.
    """
    supported_extension_aliases = ["lbaas",
                                   "lbaasrouterinsertion"]

    def _validate_vip_subnet(self, context, subnet_id, pool_id):
        # ensure that if the vip subnet is public, the router has its
        # gateway set.
        subnet = self._get_subnet(context, subnet_id)
        if db_util.is_subnet_external(context, subnet):
            router_id = db_util.get_router_from_pool(context, pool_id)
            # router_id should never be None because it was already validated
            # when we created the pool
            assert router_id is not None

            router = self._get_router(context, router_id)
            if router.get('gw_port_id') is None:
                msg = (_LE("The router must have its gateway set if the "
                           "VIP subnet is external"))
                raise n_exc.BadRequest(resource='router', msg=msg)

    def create_vip(self, context, vip):
        LOG.debug("LoadBalancerPlugin.create_vip called: %(vip)r",
                  {'vip': vip})
        with context.session.begin(subtransactions=True):

            self._validate_vip_subnet(context, vip['vip']['subnet_id'],
                                      vip['vip']['pool_id'])

            v = super(LoadBalancerPlugin, self).create_vip(context, vip)
            task.create_task(context, task.CREATE, data_type=task.VIP,
                             resource_id=v['id'], data=v)
            v['status'] = constants.ACTIVE
            self.update_status(context, ldb.Vip, v['id'], v['status'])

        LOG.debug("LoadBalancerPlugin.create_vip exiting: id=%r", v['id'])
        return v

    def delete_vip(self, context, id):
        LOG.debug("LoadBalancerPlugin.delete_vip called: id=%(id)r",
                  {'id': id})

        with context.session.begin(subtransactions=True):
            super(LoadBalancerPlugin, self).delete_vip(context, id)
            task.create_task(context, task.DELETE, data_type=task.VIP,
                             resource_id=id)

        LOG.debug("LoadBalancerPlugin.delete_vip existing: id=%(id)r",
                  {'id': id})

    def update_vip(self, context, id, vip):
        LOG.debug("LoadBalancerPlugin.update_vip called: id=%(id)r, "
                  "vip=%(vip)r", {'id': id, 'vip': vip})

        with context.session.begin(subtransactions=True):
            v = super(LoadBalancerPlugin, self).update_vip(context, id, vip)
            task.create_task(context, task.UPDATE, data_type=task.VIP,
                             resource_id=id, data=v)

        LOG.debug("LoadBalancerPlugin.update_vip exiting: id=%(id)r, "
                  "vip=%(vip)r", {'id': id, 'vip': v})
        return v

    def _update_pool_router_dict(self, context, pool):
        pool_router = self.get_pool_router(context, pool['id'])
        if pool_router:
            pool['router_id'] = pool_router['router_id']

    def create_pool(self, context, pool):
        LOG.debug("LoadBalancerPlugin.create_pool called: %(pool)r",
                  {'pool': pool})

        subnet = db_util.get_subnet(context, pool['pool']['subnet_id'])
        if subnet is None:
            msg = (_LE("subnet does not exist"))
            raise n_exc.BadRequest(resource='pool', msg=msg)

        if db_util.is_subnet_external(context, subnet):
            msg = (_LE("pool subnet must not be public"))
            raise n_exc.BadRequest(resource='subnet', msg=msg)

        router_id = db_util.get_router_from_subnet(context, subnet)

        if not router_id:
            msg = (_LE("pool subnet must be associated with router"))
            raise n_exc.BadRequest(resource='router', msg=msg)

        pool['pool'].update({'router_id': router_id})
        self.validate_pool_router_not_in_use(context, router_id)

        with context.session.begin(subtransactions=True):
            p = super(LoadBalancerPlugin, self).create_pool(context, pool)
            self.create_pool_router(context, {'pool_id': p['id'],
                                              'router_id': router_id})
            p['router_id'] = router_id
            p['status'] = constants.ACTIVE
            self.update_status(context, ldb.Pool, p['id'], p['status'])

            task.create_task(context, task.CREATE, data_type=task.POOL,
                             resource_id=p['id'], data=p)

        LOG.debug("LoadBalancerPlugin.create_pool exiting: %(pool)r",
                  {'pool': p})
        return p

    def get_pool(self, context, id, fields=None):
        LOG.debug("LoadBalancerPlugin.get_pool called: id=%(id)r", {'id': id})

        pool = super(LoadBalancerPlugin, self).get_pool(context, id)
        self._update_pool_router_dict(context, pool)
        return pool

    def update_pool(self, context, id, pool):
        LOG.debug("LoadBalancerPlugin.update_pool called: id=%(id)r, "
                  "pool=%(pool)r", {'id': id, 'pool': pool})

        with context.session.begin(subtransactions=True):
            p = super(LoadBalancerPlugin, self).update_pool(context, id, pool)
            task.create_task(context, task.UPDATE, data_type=task.POOL,
                             resource_id=id, data=p)

        self._update_pool_router_dict(context, p)

        LOG.debug("LoadBalancerPlugin.update_pool exiting: id=%(id)r, "
                  "pool=%(pool)r", {'id': id, 'pool': p})
        return p

    def delete_pool(self, context, id):
        LOG.debug("LoadBalancerPlugin.delete_pool called: %(id)r", {'id': id})

        with context.session.begin(subtransactions=True):
            self.delete_pool_router(context, id)
            super(LoadBalancerPlugin, self).delete_pool(context, id)
            task.create_task(context, task.DELETE, data_type=task.POOL,
                             resource_id=id)

        LOG.debug("LoadBalancerPlugin.delete_pool exiting: %(id)r", {'id': id})

    def create_member(self, context, member):
        LOG.debug("LoadBalancerPlugin.create_member called: %(member)r",
                  {'member': member})

        with context.session.begin(subtransactions=True):
            m = super(LoadBalancerPlugin, self).create_member(context, member)
            task.create_task(context, task.CREATE, data_type=task.MEMBER,
                             resource_id=m['id'], data=m)
            m['status'] = constants.ACTIVE
            self.update_status(context, ldb.Member, m['id'], m['status'])

        LOG.debug("LoadBalancerPlugin.create_member exiting: %(member)r",
                  {'member': m})
        return m

    def update_member(self, context, id, member):
        LOG.debug("LoadBalancerPlugin.update_member called: id=%(id)r, "
                  "member=%(member)r", {'id': id, 'member': member})

        with context.session.begin(subtransactions=True):
            m = super(LoadBalancerPlugin, self).update_member(context, id,
                                                              member)
            task.create_task(context, task.UPDATE, data_type=task.MEMBER,
                             resource_id=id, data=m)

        LOG.debug("LoadBalancerPlugin.update_member exiting: id=%(id)r, "
                  "member=%(member)r", {'id': id, 'member': m})
        return m

    def delete_member(self, context, id):
        LOG.debug("LoadBalancerPlugin.delete_member called: %(id)r",
                  {'id': id})

        with context.session.begin(subtransactions=True):
            super(LoadBalancerPlugin, self).delete_member(context, id)
            task.create_task(context, task.DELETE,
                             data_type=task.MEMBER, resource_id=id)

        LOG.debug("LoadBalancerPlugin.delete_member exiting: %(id)r",
                  {'id': id})

    def create_health_monitor(self, context, health_monitor):
        LOG.debug("LoadBalancerPlugin.create_health_monitor called: "
                  " %(health_monitor)r", {'health_monitor': health_monitor})

        with context.session.begin(subtransactions=True):
            hm = super(LoadBalancerPlugin, self).create_health_monitor(
                context, health_monitor)
            task.create_task(context, task.CREATE,
                             data_type=task.HEALTH_MONITOR,
                             resource_id=hm['id'], data=hm)

        LOG.debug("LoadBalancerPlugin.create_health_monitor exiting: "
                  "%(health_monitor)r", {'health_monitor': hm})
        return hm

    def update_health_monitor(self, context, id, health_monitor):
        LOG.debug("LoadBalancerPlugin.update_health_monitor called: "
                  "id=%(id)r, health_monitor=%(health_monitor)r",
                  {'id': id, 'health_monitor': health_monitor})

        with context.session.begin(subtransactions=True):
            hm = super(LoadBalancerPlugin, self).update_health_monitor(
                context, id, health_monitor)
            task.create_task(context, task.UPDATE,
                             data_type=task.HEALTH_MONITOR,
                             resource_id=id, data=hm)

        LOG.debug("LoadBalancerPlugin.update_health_monitor exiting: "
                  "id=%(id)r, health_monitor=%(health_monitor)r",
                  {'id': id, 'health_monitor': hm})
        return hm

    def delete_health_monitor(self, context, id):
        LOG.debug("LoadBalancerPlugin.delete_health_monitor called: %(id)r",
                  {'id': id})

        with context.session.begin(subtransactions=True):
            super(LoadBalancerPlugin, self).delete_health_monitor(context, id)
            task.create_task(context, task.DELETE,
                             data_type=task.HEALTH_MONITOR, resource_id=id)

        LOG.debug("LoadBalancerPlugin.delete_health_monitor exiting: %(id)r",
                  {'id': id})

    def create_pool_health_monitor(self, context, health_monitor, pool_id):
        LOG.debug("LoadBalancerPlugin.create_pool_health_monitor called: "
                  "hm=%(health_monitor)r, pool_id=%(pool_id)r",
                  {'health_monitor': health_monitor, 'pool_id': pool_id})

        pool = self.get_pool(context, pool_id)
        monitors = pool.get('health_monitors')
        if len(monitors) > 0:
            msg = (_LE("MidoNet right now can only support one monitor per "
                       "pool"))
            raise n_exc.BadRequest(resource='pool_health_monitor', msg=msg)

        with context.session.begin(subtransactions=True):
            monitors = super(LoadBalancerPlugin,
                             self).create_pool_health_monitor(context,
                                                              health_monitor,
                                                              pool_id)

        LOG.debug("LoadBalancerPlugin.create_pool_health_monitor exiting: "
                  "%(health_monitor)r, %(pool_id)r",
                  {'health_monitor': health_monitor, 'pool_id': pool_id})
        return monitors

    def delete_pool_health_monitor(self, context, id, pool_id):
        LOG.debug("LoadBalancerPlugin.delete_pool_health_monitor called: "
                  "id=%(id)r, pool_id=%(pool_id)r",
                  {'id': id, 'pool_id': pool_id})

        with context.session.begin(subtransactions=True):
            super(LoadBalancerPlugin, self).delete_pool_health_monitor(
                context, id, pool_id)

        LOG.debug("LoadBalancerPlugin.delete_pool_health_monitor exiting: "
                  "%(id)r, %(pool_id)r", {'id': id, 'pool_id': pool_id})
