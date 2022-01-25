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
import unittest
from os.path import dirname, join as jp, exists, basename, islink, realpath, samefile
from subprocess import check_call

import pkg_resources
from pip._internal.locations import get_scheme
from pip._internal.utils.virtualenv import virtualenv_no_global


class InstrumentedAxleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.test_dir = dirname(__file__)
        self.wheel_file = jp(self.test_dir, "test_axle_1-0.0.1-py3-none-any.whl")
        self.wheels = set()

    def tearDown(self) -> None:
        for wheel_file in list(self.wheels):
            try:
                self.uninstall(wheel_file)
            except Exception:
                sys.excepthook(*sys.exc_info())

    def install(self, wheel_file, user=False, deps=["filelock", "pip"]):
        check_call([sys.executable, "-m", "pip", "install", "--no-deps"] +
                   (["--user", "--force-reinstall"] if user else []) +
                   [wheel_file] + deps)
        self.wheels.add(wheel_file)

    def uninstall(self, wheel_file):
        check_call([sys.executable, "-m", "pip", "uninstall", "--yes", wheel_file])
        self.wheels.remove(wheel_file)

    def check_installed_contents(self, scheme):
        package_data_link = jp(scheme.purelib, "bar", "foo.so")
        data_link = jp(scheme.data, "lib", "foo.so")
        data_lib = jp(scheme.data, "lib", "foo.1.so")

        header1 = jp(scheme.headers, "header1.h")
        header2 = jp(scheme.headers, "header2.h")

        script1 = jp(scheme.scripts, "script1")
        script2 = jp(scheme.scripts, "script2")

        self.assertTrue(islink(package_data_link))
        self.assertTrue(islink(data_link))
        self.assertTrue(samefile(package_data_link, data_link))
        self.assertEqual(realpath(package_data_link), realpath(data_lib))
        self.assertEqual(realpath(data_link), realpath(data_lib))

        self.assertTrue(islink(header2))
        self.assertTrue(samefile(header1, header2))

        self.assertTrue(islink(script2))
        self.assertTrue(samefile(script1, script2))

    def test_install_uninstall(self):
        self.install(self.wheel_file)
        self.uninstall(self.wheel_file)

    def test_verify_install(self):
        self.install(self.wheel_file)

        ws = pkg_resources.WorkingSet()
        list(map(ws.add_entry, sys.path))
        pkg = ws.by_key["test-axle-1"]
        scheme = get_scheme("test-axle-1")

        prefix = scheme.purelib
        pth_file = basename(pkg.egg_info[:-len("dist-info")] + "pth")
        pth_path = jp(prefix, pth_file)
        dist_info = jp(prefix, basename(pkg.egg_info))
        axle_done = jp(dist_info, "axle.done")

        self.assertTrue(exists(pth_path))
        self.assertFalse(exists(axle_done))

        site.addpackage(prefix, pth_file, None)

        self.assertFalse(exists(pth_path))
        self.assertTrue(exists(axle_done))

        self.check_installed_contents(scheme)

        self.uninstall(self.wheel_file)

        self.assertFalse(exists(dist_info))

    @unittest.skipIf(virtualenv_no_global(), "no user site available under virtualenv")
    def test_verify_user_install(self):
        self.install(self.wheel_file, True)

        ws = pkg_resources.WorkingSet()
        list(map(ws.add_entry, sys.path))
        ws.add_entry(site.getusersitepackages())
        pkg = ws.by_key["test-axle-1"]
        scheme = get_scheme("test-axle-1", True)

        prefix = scheme.purelib
        pth_file = basename(pkg.egg_info[:-len("dist-info")] + "pth")
        pth_path = jp(prefix, pth_file)
        dist_info = jp(prefix, basename(pkg.egg_info))
        axle_done = jp(dist_info, "axle.done")

        self.assertTrue(exists(pth_path))
        self.assertFalse(exists(axle_done))

        site.addpackage(prefix, pth_file, None)

        self.assertFalse(exists(pth_path))
        self.assertTrue(exists(axle_done))

        self.check_installed_contents(scheme)

        self.uninstall(self.wheel_file)

        self.assertFalse(exists(dist_info))


if __name__ == "__main__":
    unittest.main()
