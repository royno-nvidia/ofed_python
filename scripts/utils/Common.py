#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#
# Copyright (c) 2016 Mellanox Technologies. All rights reserved.
#
# This Software is licensed under one of the following licenses:
#
# 1) under the terms of the "Common Public License 1.0" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/cpl.php.
#
# 2) under the terms of the "The BSD License" a copy of which is
#    available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/bsd-license.php.
#
# 3) under the terms of the "GNU General Public License (GPL) Version 2" a
#    copy of which is available from the Open Source Initiative, see
#    http://www.opensource.org/licenses/gpl-license.php.
#
# Licensee has the right to choose one of the above licenses.
#
# Redistributions of source code must retain the above copyright
# notice and one of the license notices.
#
# Redistributions in binary form must reproduce both the above copyright
# notice, one of the license notices in the documentation
# and/or other materials provided with the distribution.
#
#
# Author: Alaa Hleihel - alaa@mellanox.com
#
#########################################################################

import os
import re

def parse_patch_info(line):
    info = {}
    pid = re.sub(".*Change-Id=\s*", "", re.sub(";\s*subject=.*", "", line))
    info['Change-Id'] = pid
    info['subject'] = re.sub(".*;\s*subject=\s*", "", re.sub(";\s*feature.*", "", line))
    info['feature'] = re.sub(".*;\s*feature=\s*", "", re.sub(";\s*upstream_status.*", "", line))
    info['upstream_status'] = re.sub(".*;\s*upstream_status=\s*", "", re.sub(";\s*general.*", "", line))
    info['general'] = re.sub(";$", "", re.sub(".*;\s*general=\s*", "", line))
    info['keys'] = ['Change-Id', 'subject', 'feature', 'upstream_status', 'general']
    return (pid, info)

def parse_feature_info(line):
    info = {}
    name = re.sub(".*name=\s*", "", re.sub(";\s*type=.*", "", line))
    info['type'] = re.sub(".*type=\s*", "", re.sub(";\s*upstream_status=.*", "", line))
    info['upstream_status'] = re.sub(";$", "", re.sub(".*;\s*upstream_status=\s*", "", line))
    return (name, info)
