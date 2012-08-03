#!/usr/bin/python
# -*- coding: utf-8 -*-

#
#Copyright (C) 2012 Vector Guo <vectorguo@gmail.com>
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
#

"""
a utility library used by self.
"""

import urllib2

# recover short links
def unshortlink(url, times):
    try:
        return urllib2.urlopen(urllib2.Request(url=url)).url
    except:
        return url if times <= 0 else unshortlink(url, times-1)
