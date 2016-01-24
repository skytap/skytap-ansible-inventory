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
import six
from six.moves import configparser

import requests
from requests.adapters import HTTPAdapter

from urlparse import urljoin, urlunsplit
from urllib import urlencode

RESOURCE_NAME = "configurations"
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
        url_parts = (None, None, urljoin(base_url, resource), urlencode(kwargs), None)
        return urlunsplit(url_parts)

    def _handle_response(self, response, resource):
        try:
            response.raise_for_status()
        except requests.HTTPError:
            try:
                result = response.json() if response.json() else response.text
            except ValueError:
                result = response.text
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


    def __init__(self, configuration_id=None, username=None, api_token=None, override_config_file=None):
        """ Excecution path """
        self._ansible_config_vars =     {}
        self._skytap_env_vars     =     {u"network_type":u"private",
                                         u"network_connection_id":None,
                                            u"configuration_id":configuration_id,
                                            u'use_api_credentials':False,
                                            u'skytap_vm_username':None,
                                            u'api_credential_delimiter':'/'} 
        self._skytap_vars         =     {u"base_url":u"https://cloud.skytap.com/v2/",
                                            u"username":username,
                                            u"api_token":api_token}
        self._empty_inventory     =     {u"_meta":{u"hostvars": {}}}
        self._inventory_template  =     {u"skytap_environment"  : {u"hosts": [], u"vars": {}},
                                            u"_meta": {u"hostvars":{}}}
        self._network_types        =     {"nat_vpn": self.build_vpn_ip_group, 
                                            "nat_icnr":self.build_icnr_ip_group,
                                            "private": self.build_private_ip_group}
        
        self._clientData = {}
        self._inventory = self._inventory_template
   
        for vars_dict in (self.skytap_env_vars, self.skytap_vars):
            for var in vars_dict:
                if os.environ.get('SKYTAP_' + str(var).upper()):
                    vars_dict[var] = unicode(os.environ.get('SKYTAP_' + str(var).upper()))

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
        if config.has_option("skytap_env_vars", "network_connection_id"):
            self.skytap_env_vars["network_connection_id"] = unicode(config.get("skytap_env_vars", "network_connection_id"))
        if config.has_option("skytap_vars", "base_url"):
            self.skytap_vars[u"base_url"] = unicode(config.get("skytap_vars", "base_url"))
        #these vars are used to set ssh credentials from the 'credentials' field in the Skytap API response for VM's
        if config.has_option('skytap_env_vars', 'use_api_credentials'):
            #no booleans in ini; 'true' is true, everything else is false.  This is an on/off flag. 
            value = unicode(config.get('skytap_env_vars', 'use_api_credentials')).upper()
            if (value == u'TRUE'):
                self.skytap_env_vars[u'use_api_credentials'] = True
        if config.has_option('skytap_env_vars', 'skytap_vm_username'):
            self.skytap_env_vars[u'skytap_vm_username'] = unicode(config.get('skytap_env_vars', 'skytap_vm_username'))
        if config.has_option('skytap_env_vars', 'api_credential_delimiter'):
            self.skytap_env_vars[u'api_credential_delimiter'] = unicode(config.get('skytap_env_vars', 'api_credential_delimiter'))
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
    

    #add user/pass data to the individual hosts in the inventory if the necessary data is present in both skytap.ini nd the API response
    #this is set for VM's, not for interfaces -- so each of the network parser types will use this method the same way
    #NOTE: this parses a free-form field; it expects a <user_token> <delimiter_token> <password_token> format; 
    #if anything else is used, this will probably break
    def parse_credentials_for_vm(self, vm_data):
        user_pass = {} 
        if self.skytap_env_vars[u'use_api_credentials'] is not True: return user_pass 
        elif len(vm_data['credentials']) < 1: return user_pass
        
        #local shortnames
        l_delim = self.skytap_env_vars[u'api_credential_delimiter'] 
        l_uname = self.skytap_env_vars[u'skytap_vm_username']

        #if there is a single credential pair and username is unset, use the pair available
        if (len(vm_data['credentials']) is 1) and (l_uname is None):
            selected_creds = vm_data['credentials']
        else: 
            #credentials object is a list of dictionaries; each dictionary contains a field called 'text'.  We're interested in 
            #the first token of the 'text' field when the field is split on some delimeter (e.g., {'text': 'username / password'})
            selected_creds = filter(lambda cred_obj:cred_obj['text'].split(l_delim)[0].strip() == l_uname, vm_data['credentials'])
        
        if len(selected_creds) < 1: return user_pass #no match; return empty dict
        else: selected_creds = selected_creds[0]['text']

        #now split the selected_creds string into a dictionary that we can merge with the inventory data structure
        user_pass[u'ansible_ssh_user'] = unicode(selected_creds.split(l_delim)[0].strip())
        user_pass[u'ansible_ssh_pass'] = unicode(selected_creds.split(l_delim)[1].strip())
        return user_pass 


    def build_private_ip_group(self, client_data, inventory):
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]: 
                if (interface.has_key("ip")) and (interface["ip"] is not None):
                    hostname = unicode(interface["hostname"])
                    inventory[u"skytap_environment"][u"hosts"].append(hostname)
                    inventory[u"_meta"][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(interface["ip"])}
                    inventory[u'_meta'][u'hostvars'][hostname].update(creds_dict)
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
                if (interface.has_key("nat_addresses")) and (interface["nat_addresses"].has_key("network_nat_addresses")):  
                    for network_nat in interface["nat_addresses"]["network_nat_addresses"]:
                        if tunnel_source_network and network_nat["network_url"] != tunnel_source_network:
                            continue
                        hostname = unicode(interface["hostname"])
                        inventory[u"skytap_environment"][u"hosts"].append(hostname)
                        inventory[u"_meta"][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(network_nat["ip_address"])} 
                        inventory[u'_meta'][u'hostvars'][hostname].update(creds_dict)
        return inventory


    def build_vpn_ip_group(self, client_data, inventory): 
        """update the inventory file to include a group for the VPN IP addresees"""
        for vm in client_data["vms"]:
            creds_dict = self.parse_credentials_for_vm(vm)
            for interface in vm["interfaces"]:
                if (interface.has_key("nat_addresses")) and (interface["nat_addresses"].has_key("vpn_nat_addresses")):
                    for vpn_nat in interface["nat_addresses"]["vpn_nat_addresses"]:
                        if self.skytap_env_vars["network_connection_id"] and self.skytap_env_vars["network_connection_id"] != vpn_nat["vpn_id"]:
                            continue
                        hostname = unicode(interface["hostname"])
                        inventory[u"skytap_environment"][u"hosts"].append(hostname)
                        inventory[u'_meta'][u"hostvars"][hostname] = {u"ansible_ssh_host":unicode(vpn_nat["ip_address"])}
                        inventory[u'_meta'][u'hostvars'][hostname].update(creds_dict)
                        
                        # just hostname/nat_vpn per interface
                        break
        return inventory

    def get_inventory(self):
        """get the API data, parse it into an inventory"""
        api_data = self.get_data() 
        network_type = self.skytap_env_vars[u"network_type"]
        parse_method = self.network_types[str(network_type)] 
        parse_method(api_data, self.inventory)

        return self.inventory

    def run_as_script(self): 
        """get the invenotry data, dump it into json string"""
        return json.dumps(self.get_inventory())

def main():
    print(SkytapInventory().run_as_script())

if __name__ == "__main__":
    main()

