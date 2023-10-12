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
import logging
import os
import requests
import configparser
from requests.adapters import HTTPAdapter
from urllib.parse import urljoin, urlunsplit, urlencode

RESOURCE_NAME = "configurations"
DEFAULT_BASE_URL = "https://cloud.skytap.com/v2/"
LOG = logging.getLogger(__name__)


class Client(object):
    """
    REST API client class
    """

    def __init__(self, base_url, username, password, **kwargs):
        """Initialize a client session"""
        self.session = requests.Session()
        self.session.mount("http://", HTTPAdapter(max_retries=kwargs.get("max_retries", 5)))
        self.session.mount("https://", HTTPAdapter(max_retries=kwargs.get("max_retries", 5)))
        self.session.auth = (username, password)
        self.session.verify = kwargs.get("ssl_cert_file", True)
        self.base_url = base_url
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Skytap Ansible Inventory"})

    @staticmethod
    def construct_url(base_url, resource, **kwargs):
        url_parts = ('', '', urljoin(base_url, resource), urlencode(kwargs, doseq=True), '')
        return urlunsplit(url_parts)


    def _handle_response(self, response, resource):
        try:
            response.raise_for_status()
        except requests.HTTPError:
            result = response.json() or response.text
            raise requests.HTTPError(response, result, resource)

    REQUEST_TIMEOUT = 90

    def get(self, resource, **kwargs):
        """Send a GET request"""
        url = self.construct_url(self.base_url, resource, **kwargs)
        LOG.debug("%s", url)
        response = self.session.get(url, timeout=Client.REQUEST_TIMEOUT)
        LOG.debug("result: [%s]", response)
        self._handle_response(response, resource)
        return response.json()

    def close(self):
        """Close the client session"""
        self.session.close()
        return True

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

    def __init__(self, configuration_id=None, username=None, api_token=None, override_config_file=None, base_url=DEFAULT_BASE_URL):
        """ Execution path """
        self._ansible_config_vars = {}
        self._skytap_env_vars = {
            "network_type": "private",
            "network_connection_id": None,
            "configuration_id": configuration_id,
            'use_api_credentials': False,
            'skytap_vm_username': None,
            'api_credential_delimiter': '/'}
        self._skytap_vars = {
            "base_url": base_url,
            "username": username,
            "api_token": api_token}
        self._empty_inventory = {"_meta": {"hostvars": {}}}
        self._inventory_template = {
            "skytap_environment": {"hosts": [], "vars": {}},
            "_meta": {"hostvars": {}}}
        self._network_types = {
            "nat_vpn": self.build_vpn_ip_group,
            "nat_icnr": self.build_icnr_ip_group,
            "private": self.build_private_ip_group}
        self._clientData = {}
        self._inventory = self._inventory_template

        self.read_settings(override_config_file)

        # override settings from environment variables, if present
        for vars_dict in (self.skytap_env_vars, self.skytap_vars):
            for var in vars_dict:
                if os.environ.get('SKYTAP_' + var.upper()):
                    vars_dict[var] = os.environ.get('SKYTAP_' + var.upper())

        self._client = Client(self.skytap_vars["base_url"], self.skytap_vars["username"], self.skytap_vars["api_token"])

    def read_settings(self, override_config_file=None):
        config = configparser.ConfigParser(allow_no_value=True)

        # default looks for skytap.ini in the current working directory; can be over-ridden by $SKYTAP_INI env variable
        # config filename can be over-ridden with function argument (expected use: unit testing)
        config_filename = "skytap.ini"
        if override_config_file:
            config_filename = override_config_file
        skytap_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_filename)
        skytap_ini_path = os.path.expanduser(os.path.expandvars(os.environ.get("SKYTAP_INI", skytap_default_ini_path)))
        config.read(skytap_ini_path)

        # config values are set as side effects in three places: skytap_vars, skytap_env_vars, and ansible_config_vars
        # tests should validate the state of these three objects.
        # these are required args; "None" indicates no CLI args were present
        if self.skytap_vars["username"] is None:
            self.skytap_vars["username"] = config.get("skytap_vars", "username")
        if self.skytap_vars["api_token"] is None:
           self.skytap_vars["api_token"] = config.get("skytap_vars", "api_token")
        if self.skytap_env_vars["configuration_id"] is None:
           self.skytap_env_vars["configuration_id"] = config.get("skytap_env_vars", "configuration_id")
        # defaults are set in __init__; config may over-ride 
        if config.has_option("skytap_env_vars", "network_type"):
           self.skytap_env_vars["network_type"] = config.get("skytap_env_vars", "network_type")
        if config.has_option("skytap_env_vars", "network_connection_id"):
            self.skytap_env_vars["network_connection_id"] = config.get("skytap_env_vars", "network_connection_id")
        if config.has_option("skytap_vars", "base_url"):
            self.skytap_vars["base_url"] = config.get("skytap_vars", "base_url")
        # these vars are used to set ssh credentials from the 'credentials' field in the Skytap API response for VM's
        if config.has_option('skytap_env_vars', 'use_api_credentials'):
            value = config.get('skytap_env_vars', 'use_api_credentials').upper()
        if value == 'TRUE':
            self.skytap_env_vars['use_api_credentials'] = True
        if config.has_option('skytap_env_vars', 'skytap_vm_username'):
            self.skytap_env_vars['skytap_vm_username'] = config.get('skytap_env_vars', 'skytap_vm_username')
        if config.has_option('skytap_env_vars', 'api_credential_delimiter'):
            self.skytap_env_vars['api_credential_delimiter'] = config.get('skytap_env_vars', 'api_credential_delimiter')
        # skytap.ini may over-ride ansible variables  
        if config.has_option("ansible_ssh_vars", "user"):
            self.ansible_config_vars["ansible_ssh_user"] = config.get("ansible_ssh_vars", "user")
        if config.has_option("ansible_ssh_vars", "port"):
            self.ansible_config_vars["ansible_ssh_port"] = config.get("ansible_ssh_vars", "port")
        if config.has_option("ansible_ssh_vars", "pass"):
            self.ansible_config_vars["ansible_ssh_pass"] = config.get("ansible_ssh_vars", "pass")
        if config.has_option("ansible_ssh_vars", "host"):
            self.ansible_config_vars["ansible_ssh_host"] = config.get("ansible_ssh_vars", "host")
        if config.has_option("ansible_ssh_vars", "private_key_file"):
            self.ansible_config_vars["ansible_ssh_private_key_file"] = config.get("ansible_ssh_vars", "private_key_file")
        # set ansible vars in inventory object
        self._inventory_template["skytap_environment"]["vars"] = self._ansible_config_vars

    def get_data(self):
        query_string = f"{RESOURCE_NAME}/{self.skytap_env_vars['configuration_id']}.json"
        url = Client.construct_url(self.skytap_vars["base_url"], query_string)
        self._clientData = self._client.get(url)
        return self._clientData

    #add user/pass data to the individual hosts in the inventory if the necessary data is present in both skytap.ini nd the API response
    #this is set for VM's, not for interfaces -- so each of the network parser types will use this method the same way
    #NOTE: this parses a free-form field; it expects a <user_token> <delimiter_token> <password_token> format; 
    #if anything else is used, this will probably break

    def parse_credentials_for_vm(self, vm_data):
        user_pass = {}
        if not self.skytap_env_vars['use_api_credentials']:
            return user_pass
        if not vm_data['credentials']:
            return user_pass

        # local shortnames
        l_delim = self.skytap_env_vars['api_credential_delimiter']
        l_uname = self.skytap_env_vars['skytap_vm_username']

        # if there is a single credential pair and username is unset, use the pair available
        if len(vm_data['credentials']) == 1 and l_uname is None:
            selected_creds = vm_data['credentials']
        else:
            # credentials object is a list of dictionaries; each dictionary contains a field called 'text'. We're interested in 
            # the first token of the 'text' field when the field is split on some delimiter (e.g., {'text': 'username / password'})
            selected_creds = list(filter(lambda cred_obj: cred_obj['text'].split(l_delim)[0].strip() == l_uname, vm_data['credentials']))

        if not selected_creds:
            return user_pass  # no match; return empty dict
        else:
            selected_creds = selected_creds[0]['text']

        # now split the selected_creds string into a dictionary that we can merge with the inventory data structure
        user_pass['ansible_ssh_user'] = selected_creds.split(l_delim)[0].strip()
        user_pass['ansible_ssh_pass'] = selected_creds.split(l_delim)[1].strip()

        return user_pass
    
    def build_private_ip_group(self, client_data, inventory):
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]: 
                if "ip" in interface and interface["ip"] is not None:
                    hostname = str(interface["hostname"])
                    inventory["skytap_environment"]["hosts"].append(hostname)
                    inventory["_meta"]["hostvars"][hostname] = {"ansible_ssh_host": str(interface["ip"])}
                    inventory["_meta"]['hostvars'][hostname].update(creds_dict)
        return inventory
    
    def build_icnr_ip_group(self, client_data, inventory): 
        """update the inventory file to include a group for the ICNR IP addresses"""
        tunnel_source_network = None
        if self.skytap_env_vars["network_connection_id"]:
            matching_tunnels = [ tunnel for tunnel in client_data["tunnels"] if tunnel["id"] == self.skytap_env_vars["network_connection_id"] ]
            if not matching_tunnels:
                raise Exception("No tunnels with id %s found" % self.skytap_env_vars["network_connection_id"])

            tunnel_source_network = matching_tunnels[0]["source_network"]["url"]

        for vm in client_data["vms"]: 
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if "nat_addresses" in interface and "network_nat_addresses" in interface["nat_addresses"]:  
                    for network_nat in interface["nat_addresses"]["network_nat_addresses"]:
                        if tunnel_source_network and network_nat["network_url"] != tunnel_source_network:
                            continue
                        hostname = str(interface["hostname"])
                        inventory["skytap_environment"]["hosts"].append(hostname)
                        inventory["_meta"]["hostvars"][hostname] = {"ansible_ssh_host": str(network_nat["ip_address"])} 
                        inventory["_meta"]['hostvars'][hostname].update(creds_dict)
        return inventory
    
    def build_vpn_ip_group(self, client_data, inventory): 
        """update the inventory file to include a group for the VPN IP addresses"""
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if "nat_addresses" in interface and "vpn_nat_addresses" in interface["nat_addresses"]:
                    for vpn_nat in interface["nat_addresses"]["vpn_nat_addresses"]:
                        if self.skytap_env_vars["network_connection_id"] and self.skytap_env_vars["network_connection_id"] != vpn_nat["vpn_id"]:
                            continue
                        hostname = str(interface["hostname"])
                        inventory["skytap_environment"]["hosts"].append(hostname)
                        inventory["_meta"]["hostvars"][hostname] = {"ansible_ssh_host": str(vpn_nat["ip_address"])}
                        inventory["_meta"]['hostvars'][hostname].update(creds_dict)
                        
                        # just hostname/nat_vpn per interface
                        break
        return inventory
    
    def get_inventory(self):
        """get the API data, parse it into an inventory"""
        api_data = self.get_data() 
        network_type = self.skytap_env_vars["network_type"]
        parse_method = self.network_types[str(network_type)] 
        parse_method(api_data, self.inventory)

        return self.inventory

    def run_as_script(self):
        """get the inventory data, dump it into json string"""
        return json.dumps(self.get_inventory())

def main():
    print(SkytapInventory().run_as_script())

if __name__ == "__main__":
    main()
