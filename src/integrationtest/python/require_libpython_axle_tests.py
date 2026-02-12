# -*- coding: utf-8 -*-
#
# (C) Copyright 2022 Karellen, Inc. (https://www.karellen.co/)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import site
import sys
import sysconfig
import unittest
from os.path import join as jp, exists, basename, islink

import pkg_resources
from pip._internal.locations import get_scheme

from instrumented_axle_tests import InstrumentedAxleTest


def is_enabled_shared():
    enable_shared = sysconfig.get_config_var("PY_ENABLE_SHARED") or sysconfig.get_config_var("Py_ENABLE_SHARED")
    return enable_shared and int(enable_shared)


class RequireLibPythonAxleTest(InstrumentedAxleTest):
    def setUp(self) -> None:
        super().setUp()

        self.wheel_file = jp(self.test_dir, "test_axle_2_libpython-0.0.1-py3-none-any.whl")

    def check_libpython_present(self, lib_dir):
        in_venv = sys.base_exec_prefix != sys.exec_prefix
        is_user_site = lib_dir.startswith(site.USER_SITE)
        if in_venv or is_user_site:
            self.assertTrue(islink(jp(lib_dir, sysconfig.get_config_var("LDLIBRARY"))))
            self.assertTrue(islink(jp(lib_dir, sysconfig.get_config_var("INSTSONAME"))))

    @unittest.skipIf(not is_enabled_shared(), "Python isn't compiled with --enable-shared")
    def test_install_uninstall(self):
        self.install(self.wheel_file)
        self.uninstall(self.wheel_file)

    @unittest.skipIf(not is_enabled_shared(), "Python isn't compiled with --enable-shared")
    def test_verify_install(self):
        self.install(self.wheel_file)

        ws = pkg_resources.WorkingSet()
        list(map(ws.add_entry, sys.path))
        pkg = ws.by_key["test-axle-2-libpython"]
        scheme = get_scheme("test-axle-2-libpython")

        prefix = scheme.purelib
        egg_info = str(pkg._path_dist._path)
        pth_file = basename(egg_info[:-len("dist-info")] + "pth")
        pth_path = jp(prefix, pth_file)
        dist_info = jp(prefix, basename(egg_info))
        axle_done = jp(dist_info, "axle.done")

        self.assertTrue(exists(pth_path))
        self.assertFalse(exists(axle_done))

        site.addpackage(prefix, pth_file, None)

        self.assertFalse(exists(pth_path))
        self.assertTrue(exists(axle_done))

        self.check_installed_contents(scheme)
        self.check_libpython_present(jp(scheme.data, sys.platlibdir))

        self.uninstall(self.wheel_file)

        self.assertFalse(exists(dist_info))

    @unittest.skipIf(not is_enabled_shared(), "Python isn't compiled with --enable-shared")
    @unittest.skipIf(sys.base_prefix != sys.prefix, "no user site available under virtualenv")
    def test_verify_user_install(self):
        self.install(self.wheel_file, True)

        ws = pkg_resources.WorkingSet()
        list(map(ws.add_entry, sys.path))
        ws.add_entry(site.getusersitepackages())
        pkg = ws.by_key["test-axle-2-libpython"]
        scheme = get_scheme("test-axle-2-libpython", True)

        prefix = scheme.purelib
        egg_info = str(pkg._path_dist._path)
        pth_file = basename(egg_info[:-len("dist-info")] + "pth")
        pth_path = jp(prefix, pth_file)
        dist_info = jp(prefix, basename(egg_info))
        axle_done = jp(dist_info, "axle.done")

        self.assertTrue(exists(pth_path))
        self.assertFalse(exists(axle_done))

        site.addpackage(prefix, pth_file, None)

        self.assertFalse(exists(pth_path))
        self.assertTrue(exists(axle_done))

        self.check_installed_contents(scheme)
        self.check_libpython_present(jp(scheme.data, sys.platlibdir))

        self.uninstall(self.wheel_file)

        self.assertFalse(exists(dist_info))


if __name__ == "__main__":
    unittest.main()
