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

from neutron.api import extensions
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


EXTENDED_ATTRIBUTES_2_0 = {
    'pools': {
        'router_id': {'allow_post': False, 'allow_put': False,
                      'is_visible': True},
    }
}


class Loadbalancer_router_insertion(extensions.ExtensionDescriptor):
    """Extension class supporting LB Pool and Router association."""
    @classmethod
    def get_name(cls):
        return "Loadbalancer Router insertion"

    @classmethod
    def get_alias(cls):
        return "lbaasrouterinsertion"

    @classmethod
    def get_description(cls):
        return "Loadbalancer Router insertion on a specified router"

    @classmethod
    def get_namespace(cls):
        return ("http://docs.openstack.org/ext/neutron/lbaasrouterinsertion"
                "/api/v1.0")

    @classmethod
    def get_updated(cls):
        return "2015-04-11T10:00:00-00:00"

    def get_extended_resources(self, version):
        if version == "2.0":
            return EXTENDED_ATTRIBUTES_2_0
        else:
            return {}