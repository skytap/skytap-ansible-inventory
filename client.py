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

"""
This file implements GET for the Skytap API client
"""

import json
import logging
import requests
from requests.adapters import HTTPAdapter

from urlparse import urljoin, urlunsplit
from urllib import urlencode


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
