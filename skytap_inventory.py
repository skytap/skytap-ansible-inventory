#!/usr/bin/python 

#Copyright 2015 Skytap Inc.
#Copyright 2023 Blagovest Petrov <blagovest@petrovs.info>
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
        config = self._load_config(override_config_file)
        self._load_skytap_vars(config)
        self._load_skytap_env_vars(config)
        self._load_ansible_config_vars(config)

    def _load_config(self, override_config_file):
        config = configparser.ConfigParser(allow_no_value=True)
        config_filename = "skytap.ini" if not override_config_file else override_config_file
        skytap_default_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), config_filename)
        skytap_ini_path = os.path.expanduser(os.path.expandvars(os.environ.get("SKYTAP_INI", skytap_default_ini_path)))
        config.read(skytap_ini_path)

        # Check for environment variables for API credentials
        self.skytap_vars["username"] = os.environ.get("SKYTAP_USERNAME", None)
        self.skytap_vars["api_token"] = os.environ.get("SKYTAP_API_TOKEN", None)
        self.skytap_env_vars["configuration_id"] = os.environ.get("SKYTAP_CONFIGURATION_ID", None)

        # If environment variables are not set, try to get values from the .ini file
        if not self.skytap_vars["username"]:
            try:
                self.skytap_vars["username"] = config.get("skytap_vars", "username")
            except configparser.NoOptionError:
                pass

        if not self.skytap_vars["api_token"]:
            try:
                self.skytap_vars["api_token"] = config.get("skytap_vars", "api_token")
            except configparser.NoOptionError:
                pass

        if not self.skytap_env_vars["configuration_id"]:
            try:
                self.skytap_env_vars["configuration_id"] = config.get("skytap_env_vars", "configuration_id")
            except configparser.NoOptionError:
                pass

        return config

    def _load_skytap_vars(self, config):
        vars_mapping = {
            "username": "username",
            "api_token": "api_token",
            "base_url": "base_url"
        }
        for var, config_key in vars_mapping.items():
            if self.skytap_vars[var] is None and config.has_option("skytap_vars", config_key):
                self.skytap_vars[var] = config.get("skytap_vars", config_key)

    def _load_skytap_env_vars(self, config):
        vars_mapping = {
            "network_type": "network_type",
            "network_connection_id": "network_connection_id",
            "configuration_id": "configuration_id",
            "use_api_credentials": "use_api_credentials",
            "skytap_vm_username": "skytap_vm_username",
            "api_credential_delimiter": "api_credential_delimiter"
        }
        for var, config_key in vars_mapping.items():
            if config.has_option("skytap_env_vars", config_key):
                value = config.get("skytap_env_vars", config_key)
                if var == "use_api_credentials":
                    self.skytap_env_vars[var] = value.upper() == 'TRUE'
                else:
                    self.skytap_env_vars[var] = value

    def _load_ansible_config_vars(self, config):
        vars_mapping = {
            "ansible_ssh_user": "user",
            "ansible_ssh_port": "port",
            "ansible_ssh_pass": "pass",
            "ansible_ssh_host": "host",
            "ansible_ssh_private_key_file": "private_key_file"
        }
        for var, config_key in vars_mapping.items():
            if config.has_option("ansible_ssh_vars", config_key):
                self.ansible_config_vars[var] = config.get("ansible_ssh_vars", config_key)
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

        if not self.skytap_env_vars['use_api_credentials'] or not vm_data.get('credentials'):
            return user_pass

        l_delim = self.skytap_env_vars['api_credential_delimiter']
        l_uname = self.skytap_env_vars['skytap_vm_username']

        # Filter credentials based on provided username or select the first one if username is not provided
        selected_creds = next((cred for cred in vm_data['credentials'] if l_uname and cred['text'].split(l_delim)[0].strip() == l_uname), vm_data['credentials'][0])

        # Extract user and password from the selected credentials
        user, _, password = selected_creds['text'].partition(l_delim)
        user_pass['ansible_ssh_user'] = user.strip()
        user_pass['ansible_ssh_pass'] = password.strip()

        return user_pass

    def add_host_to_inventory(self, inventory, interface, ip_address, creds_dict):
        hostname = str(interface["hostname"])
        inventory["skytap_environment"]["hosts"].append(hostname)
        inventory["_meta"]["hostvars"][hostname] = {"ansible_ssh_host": ip_address}
        inventory["_meta"]['hostvars'][hostname].update(creds_dict)

    
    def build_private_ip_group(self, client_data, inventory):
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if "ip" in interface and interface["ip"]:
                    self.add_host_to_inventory(inventory, interface, str(interface["ip"]), creds_dict)
        return inventory
    
    def build_icnr_ip_group(self, client_data, inventory):
        tunnel_source_network = None
        if self.skytap_env_vars["network_connection_id"]:
            matching_tunnels = [tunnel for tunnel in client_data["tunnels"] if tunnel["id"] == self.skytap_env_vars["network_connection_id"]]
            if matching_tunnels:
                tunnel_source_network = matching_tunnels[0]["source_network"]["url"]

        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if "nat_addresses" in interface:
                    for network_nat in interface["nat_addresses"].get("network_nat_addresses", []):
                        if not tunnel_source_network or network_nat["network_url"] == tunnel_source_network:
                            self.add_host_to_inventory(inventory, interface, str(network_nat["ip_address"]), creds_dict)
        return inventory
    
    def build_vpn_ip_group(self, client_data, inventory):
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if "nat_addresses" in interface:
                    for vpn_nat in interface["nat_addresses"].get("vpn_nat_addresses", []):
                        if not self.skytap_env_vars["network_connection_id"] or self.skytap_env_vars["network_connection_id"] == vpn_nat["vpn_id"]:
                            self.add_host_to_inventory(inventory, interface, str(vpn_nat["ip_address"]), creds_dict)
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
