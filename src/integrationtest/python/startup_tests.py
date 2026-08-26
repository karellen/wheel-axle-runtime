# -*- coding: utf-8 -*-
#
# (C) Copyright 2026 Karellen, Inc. (https://www.karellen.co/)
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

import os
import site
import sys
import unittest
from os.path import exists, join as jp
from tempfile import TemporaryDirectory
from unittest.mock import patch

from wheel_axle.runtime import _dist_path, _finalize, finalize, start
from wheel_axle.runtime.constants import (AXLE_DONE_FILE, DIST_INFO_SUFFIX, PTH_SUFFIX,
                                          START_SUFFIX, START_ENTRY_POINT, START_PTH_LINE)


class StartupFileTest(unittest.TestCase):
    """Verifies the startup files against the `site` of the interpreter running the tests.

    Whichever of the two files this Python honors, the outcome has to be the same: every
    distribution present is finalized exactly once and only ever by its own startup file.
    """

    def setUp(self) -> None:
        site_dir = TemporaryDirectory(prefix="site-packages")
        self.addCleanup(site_dir.cleanup)
        self.site_dir = site_dir.name

        current_sys_path = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), current_sys_path))

        self.finalize = patch("wheel_axle.runtime._finalize").start()
        self.addCleanup(patch.stopall)

    def make_dist(self, dist_name, suffixes=(PTH_SUFFIX, START_SUFFIX)):
        """Installs the startup files and the `.dist-info` of `dist_name` into the site dir."""
        contents = {PTH_SUFFIX: START_PTH_LINE, START_SUFFIX: START_ENTRY_POINT}
        for suffix in suffixes:
            with open(jp(self.site_dir, dist_name + suffix), "w", encoding="utf-8") as f:
                f.write(contents[suffix] + "\n")

        os.mkdir(jp(self.site_dir, dist_name + DIST_INFO_SUFFIX))

        return jp(self.site_dir, dist_name)

    def finalized(self):
        return sorted(call.args[0] for call in self.finalize.call_args_list)

    def test_finalizes_the_distribution_owning_the_startup_files(self):
        dist_path = self.make_dist("alpha-1.0")

        site.addsitedir(self.site_dir)

        self.assertEqual(self.finalized(), [dist_path])

    def test_finalizes_each_distribution_by_its_own_startup_files_only(self):
        dist_paths = sorted((self.make_dist("alpha-1.0"), self.make_dist("bravo-2.1")))

        site.addsitedir(self.site_dir)

        self.assertEqual(self.finalized(), dist_paths)

    @unittest.skipUnless(sys.version_info >= (3, 15), "PEP 829 requires Python 3.15")
    def test_finalizes_a_distribution_from_its_start_file_alone(self):
        """Proves the `.start` file is what does the work, and not the `.pth` file."""
        dist_path = self.make_dist("alpha-1.0", suffixes=(START_SUFFIX,))

        site.addsitedir(self.site_dir)

        self.assertEqual(self.finalized(), [dist_path])

    def test_finalizes_a_distribution_without_a_start_file(self):
        """A distribution built by `bdist_axle` before 0.0.13 only ships the `.pth` file."""
        dist_paths = sorted((self.make_dist("alpha-1.0", suffixes=(PTH_SUFFIX,)),
                             self.make_dist("bravo-2.1")))

        site.addsitedir(self.site_dir)

        self.assertEqual(self.finalized(), dist_paths)


class StartTest(unittest.TestCase):
    """Verifies the resolution of the startup file `site` is processing.

    The `.pth` `import` line is executed by `site` in a frame of its own, and the PEP 829
    entry point is called from the frame of the `site` function walking the entry points.
    In both cases the path of the file being processed is a local of that frame, which is
    the only thing tying the call to the distribution that asked for it.
    """

    def setUp(self) -> None:
        self.finalize = patch("wheel_axle.runtime._finalize").start()
        self.addCleanup(patch.stopall)

    @staticmethod
    def call_pth_import_line(**frame_locals):
        """Executes the `.pth` `import` line the way `site` executes it."""
        exec(START_PTH_LINE, {}, frame_locals)

    # PEP 829 resolves an entry point with `strict=True`, which is what rejects everything
    # but the `pkg.mod:callable` form. The keyword only exists starting with Python 3.15
    RESOLVE_ENTRY_POINT = ("pkgutil.resolve_name(%r, strict=True)" if sys.version_info >= (3, 15)
                           else "pkgutil.resolve_name(%r)") % START_ENTRY_POINT

    @classmethod
    def call_start_entry_point(cls, **frame_locals):
        """Calls the `.start` entry point the way PEP 829 prescribes - with no arguments."""
        exec("import pkgutil; %s()" % cls.RESOLVE_ENTRY_POINT, {}, frame_locals)

    def test_resolves_the_pth_file_of_python_3_14_and_older(self):
        self.call_pth_import_line(fullname=jp(os.sep, "site-packages", "alpha-1.0" + PTH_SUFFIX))

        self.finalize.assert_called_once_with(jp(os.sep, "site-packages", "alpha-1.0"))

    def test_resolves_the_pth_file_of_python_3_15_and_newer(self):
        self.call_pth_import_line(filename=jp(os.sep, "site-packages", "alpha-1.0" + PTH_SUFFIX))

        self.finalize.assert_called_once_with(jp(os.sep, "site-packages", "alpha-1.0"))

    def test_resolves_the_start_file(self):
        self.call_start_entry_point(filename=jp(os.sep, "site-packages", "alpha-1.0" + START_SUFFIX))

        self.finalize.assert_called_once_with(jp(os.sep, "site-packages", "alpha-1.0"))

    def test_resolves_a_startup_file_held_by_a_local_of_an_unknown_name(self):
        """`site` renamed the local once already and is free to do so again."""
        self.call_pth_import_line(sitedir=jp(os.sep, "site-packages"),
                                  a_local_of_a_name_we_do_not_know=jp(os.sep, "site-packages",
                                                                      "alpha-1.0" + START_SUFFIX))

        self.finalize.assert_called_once_with(jp(os.sep, "site-packages", "alpha-1.0"))

    def test_refuses_to_guess_between_several_startup_files(self):
        with self.assertRaises(RuntimeError):
            self.call_pth_import_line(one=jp(os.sep, "site-packages", "alpha-1.0" + PTH_SUFFIX),
                                      other=jp(os.sep, "site-packages", "bravo-2.1" + PTH_SUFFIX))

        self.finalize.assert_not_called()

    def test_refuses_to_run_outside_of_a_startup_file(self):
        with self.assertRaises(RuntimeError):
            start()

        self.finalize.assert_not_called()


class DistPathTest(unittest.TestCase):
    def test_strips_the_startup_file_suffixes(self):
        for suffix in (PTH_SUFFIX, START_SUFFIX):
            with self.subTest(suffix=suffix):
                self.assertEqual(_dist_path(jp(os.sep, "site-packages", "alpha-1.0" + suffix)),
                                 jp(os.sep, "site-packages", "alpha-1.0"))

    def test_rejects_everything_that_is_not_an_absolute_startup_file_path(self):
        for value in (None, 42, ["/site-packages/alpha-1.0.pth"], START_ENTRY_POINT, START_PTH_LINE,
                      "alpha-1.0" + PTH_SUFFIX, jp(os.sep, "site-packages", "alpha-1.0")):
            with self.subTest(value=value):
                self.assertIsNone(_dist_path(value))


class FinalizeTest(unittest.TestCase):
    """Verifies the API the distributions built by `bdist_axle` before 0.0.13 call."""

    def test_finalizes_the_distribution_owning_the_pth_file(self):
        with patch("wheel_axle.runtime._finalize") as _finalize:
            finalize(jp(os.sep, "site-packages", "alpha-1.0" + PTH_SUFFIX))

        _finalize.assert_called_once_with(jp(os.sep, "site-packages", "alpha-1.0"))


class FinalizeStartupFilesTest(unittest.TestCase):
    """Verifies the startup file bookkeeping `_finalize` does around the installers."""

    def setUp(self) -> None:
        site_dir = TemporaryDirectory(prefix="site-packages")
        self.addCleanup(site_dir.cleanup)
        self.site_dir = site_dir.name

        self.run_installers = patch("wheel_axle.runtime._run_installers").start()
        self.addCleanup(patch.stopall)

    def make_dist(self, dist_name, suffixes=(PTH_SUFFIX, START_SUFFIX), done=False):
        for suffix in suffixes:
            with open(jp(self.site_dir, dist_name + suffix), "wb"):
                pass

        dist_info_dir = jp(self.site_dir, dist_name + DIST_INFO_SUFFIX)
        os.mkdir(dist_info_dir)
        if done:
            with open(jp(dist_info_dir, AXLE_DONE_FILE), "wb"):
                pass

        return jp(self.site_dir, dist_name)

    def test_removes_both_startup_files(self):
        dist_path = self.make_dist("alpha-1.0")

        _finalize(dist_path)

        self.run_installers.assert_called_once_with(dist_path + DIST_INFO_SUFFIX)
        for suffix in (PTH_SUFFIX, START_SUFFIX):
            self.assertFalse(exists(dist_path + suffix))

    def test_removes_the_pth_file_of_a_distribution_that_has_no_start_file(self):
        """A distribution built by `bdist_axle` before 0.0.13 only ships the `.pth` file."""
        dist_path = self.make_dist("alpha-1.0", suffixes=(PTH_SUFFIX,))

        _finalize(dist_path)

        self.run_installers.assert_called_once_with(dist_path + DIST_INFO_SUFFIX)
        self.assertFalse(exists(dist_path + PTH_SUFFIX))

    def test_leaves_an_already_finalized_distribution_alone(self):
        dist_path = self.make_dist("alpha-1.0", done=True)

        _finalize(dist_path)

        self.run_installers.assert_not_called()
        for suffix in (PTH_SUFFIX, START_SUFFIX):
            self.assertTrue(exists(dist_path + suffix))


if __name__ == "__main__":
    unittest.main()
