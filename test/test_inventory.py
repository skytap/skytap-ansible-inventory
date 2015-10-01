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


"""add parent module to sys.path if running as script"""
if __name__ == "__main__" and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import json
import six
from six.moves import configparser
import unittest

import mock
from mock import MagicMock  #pip install mock for Python 2.7 

from skytap_inventory import SkytapInventory


class TestInstantiationMethods(unittest.TestCase): 
    def test_asert_on_username_missing(self):
        self.assertRaises(configparser.NoOptionError, 
                SkytapInventory,None,None,None,"test/config_fixtures/config_missing_username_fixture.ini")


    def test_assert_on_token_missing(self):
        self.assertRaises(configparser.NoOptionError,
                SkytapInventory,None,None,None,"test/config_fixtures/config_missing_token_fixture.ini")
    

    def test_assert_on_configuration_id_missing(self):
        self.assertRaises(configparser.NoOptionError,
                SkytapInventory,None,None,None,"test/config_fixtures/config_missing_configuration_id_fixture.ini")

    @mock.patch("skytap_inventory.SkytapInventory.read_settings")
    @mock.patch("client.Client.__init__")
    def test_calls_correct_methods(self, mock_client, mock_read_settings):
        mock_client.return_value = None
        SkytapInventory()
        mock_read_settings.assert_called_once_with(None)
        mock_client.assert_called_once_with(mock.ANY, mock.ANY, mock.ANY)


class TestRuntimeMethods(unittest.TestCase):
    @mock.patch("client.Client.__init__")
    @mock.patch("client.Client.get")
    def test_get_data(self, mock_get, mock_client):
        mock_client.return_value = None
        mock_get.return_value = None
        test_inv = SkytapInventory(None,None,None,"test/config_fixtures/config_fixture.ini")
        expected_calling_url = (u"https://_testfixture_.net/configurations/0000000.json")
        test_inv.get_data()
        mock_get.assert_called_once_with(expected_calling_url)



class TestParseMethods(unittest.TestCase):
    def setUp(self):
        with(open("dynamic_inventory_fixture.json", "r")) as inv_fh:
            with(open("api_response_fixture.json", "r")) as api_fh:
                self.expected_inventory = json.loads(inv_fh.read())
                self.mock_api_response = json.loads(api_fh.read())

        self.script_under_test = SkytapInventory(None,None,None,"test/config_fixtures/config_fixture.ini")  
        self.script_under_test.get_data = MagicMock(return_value=self.mock_api_response)
    

    def test_correct_empty_inventory(self): 
        testObj = SkytapInventory()
        knownGood = {"_meta":{"hostvars":{}}}
        self.assertDictEqual(knownGood, testObj.empty_inventory)

    
    def test_ansible_config_vars_set(self):
        known_good = {u"ansible_ssh_host": u"_ANSIBLE-SSH-HOST_",
                        u"ansible_ssh_pass": u"_ANSIBLE-SSH-PASS_",
                        u"ansible_ssh_port": u"65535",
                        u"ansible_ssh_private_key_file": u"_ANSIBLE-SSH-PRIVATE-KEY-FILE_",
                        u"ansible_ssh_user": u"_ANSIBLE-SSH-USER_"}
        actual = self.script_under_test.ansible_config_vars
        self.assertDictEqual(known_good, actual)


    def test_skytap_vars(self):
        known_good = {u"api_token": u"abcdefghijklmnopqrstuvwxyz01234567890abcef",
                        u"base_url": u"https://_testfixture_.net",
                        u"username": u"_SKYTAP-USERNAME_"}
        actual = self.script_under_test.skytap_vars
        self.assertDictEqual(known_good, actual)


    def test_skytap_env_vars(self):
        known_good =  {u"configuration_id": u"0000000", 
                       u"network_type": "nat_vpn"}
        actual = self.script_under_test.skytap_env_vars
        self.assertDictEqual(known_good, actual)


    def test_parse_vpn_ips(self):
        mock_api_data = self.script_under_test.get_data() #fixture data 
        actual_result = self.script_under_test.build_vpn_ip_group(mock_api_data, self.script_under_test.inventory)
        self.assertDictEqual(self.expected_inventory, actual_result)


    def test_parse_private_ips(self):
        mock_api_data = self.script_under_test.get_data() #fixture data 
        actual_result = self.script_under_test.build_private_ip_group(mock_api_data, self.script_under_test.inventory)
        self.assertDictEqual(self.expected_inventory, actual_result)


    def test_parse_incr_ips(self):
        mock_api_data = self.script_under_test.get_data() #fixture data 
        actual_result = self.script_under_test.build_incr_ip_group(mock_api_data, self.script_under_test.inventory)
        self.assertDictEqual(self.expected_inventory, actual_result)


    def test_run_as_script(self):
        actual_result = json.loads(SkytapInventory.run_as_script(self.script_under_test))
        self.assertDictEqual(self.expected_inventory, actual_result) 
        

if __name__ == "__main__":
    instantiationMethodsSuite = unittest.TestLoader().loadTestsFromTestCase(TestInstantiationMethods)
    parseMethodsSuite = unittest.TestLoader().loadTestsFromTestCase(TestParseMethods)
    runtimeMethodsSuite = unittest.TestLoader().loadTestsFromTestCase(TestRuntimeMethods)

    unittest.TextTestRunner(verbosity=2).run(instantiationMethodsSuite)
    unittest.TextTestRunner(verbosity=2).run(parseMethodsSuite)
    unittest.TextTestRunner(verbosity=2).run(runtimeMethodsSuite)