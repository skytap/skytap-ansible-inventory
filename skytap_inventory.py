#!/usr/bin/python 

#Copyright 2015 Skytap Inc.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.


import json
import os 
import six
from six.moves import configparser

from client import Client

RESOURCE_NAME = "configurations"


class SkytapInventory(object):

    
    @property 
    def empty_inventory(self): 
        return self._empty_inventory

    @property 
    def network_types(self):
        return self._network_types 

    @property 
    def skytap_inventory_template(self): 
        return self._inventory_template

    @property 
    def inventory(self):
        return self._inventory

    @property 
    def skytap_vars(self):
        return self._skytap_vars

    @property
    def skytap_env_vars(self):
        return self._skytap_env_vars

    @property
    def ansible_config_vars(self):
        return self._ansible_config_vars


    """ Excecution path """
    def __init__(self, configuration_id=None, username=None, api_token=None, override_config_file=None):
        self._ansible_config_vars =     {}
        self._skytap_env_vars     =     {u"network_type":u"private", 
                                            u"configuration_id":configuration_id}
        self._skytap_vars         =     {u"base_url":u"https:/cloud.skytap.com/v2/",
                                            u"username":username,
                                            u"api_token":api_token}
        self._empty_inventory     =     {u"_meta":{u"hostvars": {}}}
        self._inventory_template  =     {u"skytap_environment"  : {u"hosts": [], u"vars": {}},
                                            u"_meta": {u"hostvars":{}}}
        self._network_types        =     {"nat_vpn": self.build_vpn_ip_group, 
                                            "nat_incr":self.build_incr_ip_group,
                                            "private": self.build_private_ip_group}
        
        self._client_data = {}
        self._inventory = self._inventory_template
        self.read_settings(override_config_file)
        self._client = Client(self.skytap_vars[u"base_url"], self.skytap_vars[u"username"], self.skytap_vars[u"api_token"])


    def read_settings(self, override_config_file=None): 
        if six.PY2: 
            config = configparser.SafeConfigParser(allow_no_value=True)
        else: 
            config = configparser.ConfigParser(allow_no_value=True)

        #default looks for skytap.ini in the current working directory; can be over-ridden by $SKYTAP_INI env variable
        #config filename can be over-ridden with function argument (expected use: unit testing)
        config_filename = "skytap.ini"
        if override_config_file:
            config_filename = override_config_file
        skytap_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_filename)
        skytap_ini_path = os.path.expanduser(os.path.expandvars(os.environ.get("SKYTAP_INI", skytap_default_ini_path)))
        config.read(skytap_ini_path)
 
        #config values are set as side effects in three places: skytap_vars, skytap_env_vars, and ansible_config_vars
        #tests should validate the state of these three objects.  
        #----
        #these are required args; "None" indicates no CLI args were present
        if self.skytap_vars[u"username"] is None:
            self.skytap_vars[u"username"] = unicode(config.get("skytap_vars", "username"))
        if self.skytap_vars[u"api_token"] is None:
            self.skytap_vars[u"api_token"] = unicode(config.get("skytap_vars", "api_token"))
        if self.skytap_env_vars[u"configuration_id"] is None:
            self.skytap_env_vars[u"configuration_id"] = unicode(config.get("skytap_env_vars", "configuration_id"))
        #defaults are set in __init__; config may over-ride 
        if config.has_option("skytap_env_vars", "network_type"):
            self.skytap_env_vars["network_type"] = unicode(config.get("skytap_env_vars", "network_type"))
        if config.has_option("skytap_vars", "base_url"):
            self.skytap_vars[u"base_url"] = unicode(config.get("skytap_vars", "base_url"))
        #skytap.ini may over-ride ansible variables  
        if config.has_option("ansible_ssh_vars", "user"):
            self.ansible_config_vars[u"ansible_ssh_user"] = unicode(config.get("ansible_ssh_vars", "user"))
        if  config.has_option("ansible_ssh_vars", "port"):
            self.ansible_config_vars[u"ansible_ssh_port"] = unicode(config.get("ansible_ssh_vars", "port"))
        if  config.has_option("ansible_ssh_vars", "pass"):
            self.ansible_config_vars[u"ansible_ssh_pass"] = unicode(config.get("ansible_ssh_vars", "pass"))
        if  config.has_option("ansible_ssh_vars", "host"):
            self.ansible_config_vars[u"ansible_ssh_host"] = unicode(config.get("ansible_ssh_vars", "host"))
        if  config.has_option("ansible_ssh_vars", "private_key_file"):
            self.ansible_config_vars[u"ansible_ssh_private_key_file"] = unicode(config.get("ansible_ssh_vars", "private_key_file"))
        #set ansible vars in inventory object
        self._inventory_template[u"skytap_environment"][u"vars"] = self._ansible_config_vars


    def get_data(self):
        query_string = RESOURCE_NAME + "/" + str(self.skytap_env_vars[u"configuration_id"]) + ".json"
        url = Client.construct_url(self.skytap_vars[u"base_url"], query_string)
        self._clientData = self._client.get(url)
        return self._clientData


    def build_private_ip_group(self, client_data, inventory):
        for vm in client_data["vms"]:
            for interface in vm["interfaces"]: 
                if (interface.has_key("ip")) and (interface["ip"] is not None):
                    hostname = unicode(interface["hostname"])
                    inventory[u"skytap_environment"][u"hosts"].append(hostname)
                    inventory[u"_meta"][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(interface["ip"])} 
        return inventory


    def build_incr_ip_group(self, client_data, inventory): 
        """update the inventory file to include a group for the INCR IP addresses""" 
        for vm in client_data["vms"]: 
            for interface in vm["interfaces"]:
                if (interface.has_key("nat_addresses")) and (interface["nat_addresses"].has_key("network_nat_addresses")):  
                    for network_nat in interface["nat_addresses"]["network_nat_addresses"]:
                        hostname = unicode(interface["hostname"])
                        inventory[u"skytap_environment"][u"hosts"].append(hostname)
                        inventory[u"_meta"][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(network_nat["ip_address"])} 
        return inventory


    def build_vpn_ip_group(self, client_data, inventory): 
        """update the inventory file to include a group for the VPN IP addresees"""
        for vm in client_data["vms"]:
            for interface in vm["interfaces"]:
                if (interface.has_key("nat_addresses")) and (interface["nat_addresses"].has_key("vpn_nat_addresses")):
                    for vpn_nat in interface["nat_addresses"]["vpn_nat_addresses"]:
                        hostname = unicode(interface["hostname"])
                        inventory[u"skytap_environment"][u"hosts"].append(hostname)
                        inventory[u"_meta"][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(vpn_nat["ip_address"])} 
        return inventory

    def run_as_script(self): 
        """instantiate the class, set configuration, get the API data, parse it into an inventory"""
        #inventory_object = SkytapInventory()
        api_data = self.get_data() 
        network_type = self.skytap_env_vars[u"network_type"]
        parse_method = self.network_types[network_type] 
        parse_method(api_data, self.inventory)
        return json.dumps(self.inventory)


if __name__ == "__main__":
    inv = SkytapInventory()
    print(inv.run_as_script())
