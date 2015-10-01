#Skytap Dynamic Inventory
Ansible is a lightweight configuration management/orchestration tool that works over SSH, with minimal requirements for managed hosts: 
http://docs.ansible.com/ansible/index.html 

This Python script wraps the Environment/Configuration method of the Skytap API, in order to retrieve information about your Skytap Environment and parse that information into an Ansible dynamic inventory.  

Together, this dynamic inventory script and Ansible provide Skytap users the ability to finely tune administration of a sets of hosts within a Skytap Environment.  


##Examples
*Usage example* (Ansible-ping all of the hosts in the environment): 

    ansible -i skytap_inventory.py all -m ping

*Usage example* (Ansible-ping a single host by name in the environment) : 

    ansible -i skytap_inventory.py myHost -m ping 

This usage assumes the presence of a valid skytap.ini.  

skytap_inventory.py may be run in standalone mode, to return JSON structured in Ansible inventory format.  If run in standalone mode, you may supply arguments for the Skytap API requirements, or over-ride the skytap.ini file, to match this method signature: 

    def __init__(self, configuration_id=None, username=None, api_token=None, override_config_file=None):

## skytap.ini  
An example skytap.ini is included with this package: 

    EXAMPLEskytap.ini 

Skytap specific configuration is set in two blocks, in skytap.ini: 
`[skytap_vars]`  -- global vars related to the Skytap account 
`[skytap_env_vars]`  -- variables related to the specific Skytap Environment

A third block, `[ansible_ssh_vars]` may be used to override SSH parameters configured for the system or user, such that Skytap specific SSH parameters can be set.   

Copy the example to a file named skytap.ini, and fill in your credentials and environment info.  

**Don't forget to add skytap.ini to your .ignore files for your version control system!** This file, when properly configured, will contain your Skytap API credentials, and may contain information such as SSH usernames and password.  ***Do not check it in to source control!*** 

##Ansible Notes 
 Make sure you've got ansible installed: 
 http://docs.ansible.com/ansible/intro_installation.html 

Your Ansible.cfg and .ssh/config need to be set up so that Ansible can communicate with the hosts in your Skytap Environment.  The networking variations and quirks possible in the wild are outside of the scope of this document, but the settings below have worked on Debian based distros for some users.  This isn't guaranteed to work, but may provide a good baseline:  

    ~/.ssh/config 
    Host *
    ssh_args = -o ControlMaster=auto -o
    ControlPersist=60s
      ControlPath /tmp/ans-%r@%h:%p
      #necessary for password-based auth, 
      #but prefer key-based auth if you can!
      StrictHostKeyChecking no 

You may need to install sshpass for password-based SSH auth to work correctly.  

SSH parameters may also be set in your ansible.cfg, if you'd prefer not to tweak with your ~/.ssh/config

    [defaults]
    host_key_checking=False
    timeout = 10
    
    [ssh_connection]
    ssh_args = -o ControlMaster=auto -o ControlPersist=60s
    control_path = /tmp/ans-%r@%h:%p

Finally, Skytap specific SSH information may be set in `skytap.ini`

**NOTE:** if parameters are present, but blank (E.G., ansible_ssh_private_key_file), Ansible will interpet these as SSH options but supply
empty parameters.  You'll probably get esoteric SSH errors such as: 

        FAILED => SSH Error: command-line line 0: Missing argument.
    or 
        FAILED => SSH encountered an unknown error. The output was:
        command-line line 0: Missing argument.

use the `[ansible_ssh_vars]` block in your skytap.ini to set parameters specific to your Skytap Environment (such as usernames, SSH key locations, ports -- see `EXAMPLEskytap.ini` for possible values

##Unit Tests
If you need to extend the inventory script for personal use, this package includes a basic set of unit tests which should validate correct behavior for  `skytap_inventory.py` 

Tests and mock data are included in the `/test` sub-package.  You should have mock installed for Python version <= 3.0 (`pip install mock`).  

The tests will run as a self-contained script: 
`./test_inventory.py` 

Test fixtures are provided by a mock API response, expected dynamic inventory, and several mock configurations 

##Python Version Compatability
The script has been developed and tested with Python 2.7.  Some minor effort has been made to handle cross-version compatibility, but this has **not** been tested with >= Python 3.0.  

##Copyright##
Copyright 2015 Skytap Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

