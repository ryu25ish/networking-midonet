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

from midonet.neutron.db import loadbalancer_db as mn_lb_db
from midonet.neutron.db import task_db as task

from neutron.plugins.common import constants
from neutron_lbaas.db.loadbalancer import loadbalancer_db as ldb
from neutron_lbaas.services.loadbalancer.drivers import abstract_driver

from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class MidonetLoadbalancerDriver(abstract_driver.LoadBalancerAbstractDriver,
                                mn_lb_db.LoadBalancerMixin):

    def __init__(self, plugin):
        self._plugin = plugin

    def create_vip(self, context, vip):
        LOG.debug("MidonetLoadbalancerDriver.create_vip called: %(vip)r",
                  {'vip': vip})

        try:
            self._validate_vip_subnet(context, vip)
        except:
            self._plugin._delete_db_vip(context, vip['id'])
            raise

        task.create_task(context, task.CREATE, data_type=task.VIP,
                         resource_id=vip['id'], data=vip)
        self._plugin.update_status(context, ldb.Vip, vip['id'],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.create_vip exiting: id=%r",
                  vip['id'])

    def delete_vip(self, context, vip):
        LOG.debug("MidonetLoadbalancerDriver.delete_vip called: id=%(vip)r",
                  {'vip': vip})

        task.create_task(context, task.DELETE, data_type=task.VIP,
                         resource_id=vip['id'])
        self._plugin._delete_db_vip(context, vip['id'])

        LOG.debug("MidonetLoadbalancerDriver.delete_vip existing: vip=%(vip)r",
                  {'vip': vip})

    def update_vip(self, context, old_vip, new_vip):
        LOG.debug("MidonetLoadbalancerDriver.update_vip called: "
                  "old_vip=%(old_vip)r, new_vip=%(new_vip)r",
                  {'old_vip': old_vip, 'new_vip': new_vip})

        task.create_task(context, task.UPDATE, data_type=task.VIP,
                         resource_id=old_vip['id'], data=new_vip)
        self._plugin.update_status(context, ldb.Vip, new_vip["id"],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.update_vip exiting: "
                  "old_vip=%(old_vip)r, new_vip=%(new_vip)r",
                  {'old_vip': old_vip, 'new_vip': new_vip})

    def create_pool(self, context, pool):
        LOG.debug("MidonetLoadbalancerDriver.create_pool called: %(pool)r",
                  {'pool': pool})

        try:
            router_id = self._check_and_get_router_id_for_pool(
                context, pool['subnet_id'])
        except:
            self._plugin._delete_db_pool(context, pool['id'])
            raise

        pool.update({'router_id': router_id, 'status': constants.ACTIVE})
        task.create_task(context, task.CREATE, data_type=task.POOL,
                         resource_id=pool['id'], data=pool)
        self._plugin.update_status(context, ldb.Pool, pool['id'],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.create_pool exiting: %(pool)r",
                  {'pool': pool})

    def update_pool(self, context, old_pool, new_pool):
        LOG.debug("MidonetLoadbalancerDriver.update_pool called: "
                  "old_pool=%(old_pool)r, new_pool=%(new_pool)r",
                  {'old_pool': old_pool, 'new_pool': new_pool})

        task.create_task(context, task.UPDATE, data_type=task.POOL,
                         resource_id=old_pool['id'], data=new_pool)
        self._plugin.update_status(context, ldb.Pool, new_pool["id"],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.update_pool exiting: "
                  "new_pool=%(new_pool)r", {'new_pool': new_pool})

    def delete_pool(self, context, pool):
        LOG.debug("MidonetLoadbalancerDriver.delete_pool called: %(pool)r",
                  {'pool': pool})

        task.create_task(context, task.DELETE, data_type=task.POOL,
                         resource_id=pool['id'])
        self._plugin._delete_db_pool(context, pool['id'])

        LOG.debug("MidonetLoadbalancerDriver.delete_pool exiting: %(pool)r",
                  {'pool': pool})

    def create_member(self, context, member):
        LOG.debug("MidonetLoadbalancerDriver.create_member called: %(member)r",
                  {'member': member})

        task.create_task(context, task.CREATE, data_type=task.MEMBER,
                         resource_id=member['id'], data=member)
        self._plugin.update_status(context, ldb.Member, member['id'],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.create_member exiting: "
                  "%(member)r", {'member': member})

    def update_member(self, context, old_member, new_member):
        LOG.debug("MidonetLoadbalancerDriver.update_member called: "
                  "old_member=%(old_member)r, new_member=%(new_member)r",
                  {'old_member': old_member, 'new_member': new_member})

        task.create_task(context, task.UPDATE, data_type=task.MEMBER,
                         resource_id=old_member['id'], data=new_member)
        self._plugin.update_status(context, ldb.Member, new_member["id"],
                                   constants.ACTIVE)

        LOG.debug("MidonetLoadbalancerDriver.update_member exiting: "
                  "new_member=%(new_member)r", {'new_member': new_member})

    def delete_member(self, context, member):
        LOG.debug("MidonetLoadbalancerDriver.delete_member called: %(member)r",
                  {'member': member})

        task.create_task(context, task.DELETE, data_type=task.MEMBER,
                         resource_id=member['id'])
        self._plugin._delete_db_member(context, member['id'])

        LOG.debug("MidonetLoadbalancerDriver.delete_member exiting: %(member)r",
                  {'member': member})

    def create_pool_health_monitor(self, context, health_monitor, pool_id):
        LOG.debug("MidonetLoadbalancerDriver.create_pool_health_monitor "
                  "called: hm=%(health_monitor)r, pool_id=%(pool_id)r",
                  {'health_monitor': health_monitor, 'pool_id': pool_id})

        try:
            self._validate_pool_hm_assoc(context, pool_id,
                                         health_monitor['id'])
        except:
            self._plugin._delete_db_pool_health_monitor(context,
                                                        health_monitor['id'],
                                                        pool_id)
            raise

        task.create_task(context, task.CREATE,
                         data_type=task.HEALTH_MONITOR,
                         resource_id=health_monitor['id'], data=health_monitor)
        self._plugin.update_pool_health_monitor(context, health_monitor['id'],
                                                pool_id, constants.ACTIVE, "")

        LOG.debug("MidonetLoadbalancerDriver.create_pool_health_monitor "
                  "exiting: %(health_monitor)r, %(pool_id)r",
                  {'health_monitor': health_monitor, 'pool_id': pool_id})

    def delete_pool_health_monitor(self, context, health_monitor, pool_id):
        LOG.debug("MidonetLoadbalancerDriver.delete_pool_health_monitor "
                  "called: health_monitor=%(health_monitor)r, "
                  "pool_id=%(pool_id)r",  {'health_monitor': health_monitor,
                                           'pool_id': pool_id})

        task.create_task(context, task.DELETE, data_type=task.HEALTH_MONITOR,
                         resource_id=health_monitor['id'])
        self._plugin._delete_db_pool_health_monitor(context,
                                                    health_monitor['id'],
                                                    pool_id)

        LOG.debug("MidonetLoadbalancerDriver.delete_pool_health_monitor "
                  "exiting: %(health_monitor)r, %(pool_id)r",
                  {'health_monitor': health_monitor, 'pool_id': pool_id})

    def update_pool_health_monitor(self, context, old_health_monitor,
                                   health_monitor, pool_id):
        raise NotImplementedError()

    def stats(self, context, pool_id):
        raise NotImplementedError()
