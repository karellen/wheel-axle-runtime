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

import os
import contextlib
import sys
import site
from os.path import exists, isabs, join as jp, commonpath
from threading import RLock

from wheel_axle.runtime.constants import (AXLE_DONE_FILE, AXLE_LOCK_FILE, DIST_INFO_SUFFIX,
                                          PTH_SUFFIX, START_SUFFIX)

__version__ = "${dist_version}"

inter_thread_lock = RLock()

# `site` runs both kinds of startup file from a frame that holds the path of the file
# being processed. Up to Python 3.14 `site.addpackage` calls it `fullname`; the PEP 829
# implementation calls it `filename`, both when executing a `.pth` `import` line and
# when calling a `.start` entry point.
_STARTUP_PATH_LOCALS = ("filename", "fullname")

_STARTUP_SUFFIXES = (PTH_SUFFIX, START_SUFFIX)


def _run_installers(dist_info_dir):
    # Get metadata
    from wheel_axle.runtime._libpython import LibPythonInstaller
    from wheel_axle.runtime._symlinks import SymlinksInstaller
    from wheel_axle.runtime._axle import AxleFinalizer

    installers = [LibPythonInstaller, SymlinksInstaller, AxleFinalizer]  # AxleFinalizer is always last!
    for installer in installers:
        installer(dist_info_dir).run()


@contextlib.contextmanager
def user_site_handler(dist_path):
    # PEP 829 has Python 3.15+ apply every `.pth` path extension before it runs any
    # startup code, so the global site-packages - and with them `pip` - are already
    # importable by the time a startup file of the user site directory gets its turn
    if sys.version_info >= (3, 15) or sys.flags.no_site or (not site.check_enableusersite()):
        yield
        return

    user_site_path = site.getusersitepackages()
    in_user_site_path = False
    try:
        if commonpath((user_site_path, dist_path)) == user_site_path:
            in_user_site_path = True

        if in_user_site_path:
            current_sys_path = sys.path[:]
            sys.path[:] = site.addsitepackages(set(sys.path))
        yield
    finally:
        if in_user_site_path:
            sys.path[:] = current_sys_path


def start():
    """Finalizes the Axle distribution whose startup file is being processed.

    Both startup files of a distribution call this. The PEP 829 `.start` file names it
    as its `wheel_axle.runtime:start` entry point and the `.pth` file calls it from its
    `import` line, which is exactly the straddling form the `site` documentation
    prescribes, so the two are guaranteed to do the same thing.

    A startup callable takes no arguments and the name of a startup file is not
    constrained to the distribution that installed it, so the only thing that identifies
    the caller is the path `site` is holding while it runs us.
    """
    _finalize(_startup_dist_path(sys._getframe(1)))


def _startup_dist_path(frame):
    """Returns `<site dir>/<name>-<version>` of the distribution owning `frame`'s file.

    Both the `.pth` and the `.start` file of a distribution are installed next to its
    `.dist-info` directory and named after it, so stripping the suffix off the path
    `site` is processing yields the distribution, and only ever that distribution.
    """
    frame_locals = frame.f_locals

    for local_name in _STARTUP_PATH_LOCALS:
        dist_path = _dist_path(frame_locals.get(local_name))
        if dist_path:
            return dist_path

    # `site` is free to rename its locals - it did so in 3.15 - and the name it uses is
    # not part of any contract, so fall back on what the frame actually holds
    candidates = set(filter(None, map(_dist_path, frame_locals.values())))
    if len(candidates) == 1:
        return candidates.pop()

    raise RuntimeError("wheel_axle.runtime.start() is only callable by `site` while it "
                       "processes a %s or a %s file, and the file being processed was "
                       "not found in %r" % (PTH_SUFFIX, START_SUFFIX, frame))


def _dist_path(value):
    """Returns the distribution owning the startup file `value`, `None` if it is not one."""
    if isinstance(value, str) and isabs(value):
        for suffix in _STARTUP_SUFFIXES:
            if value.endswith(suffix):
                return value[:-len(suffix)]


def finalize(pth_path):
    """Finalizes the Axle distribution owning the `.pth` file at `pth_path`.

    Retained for the distributions built by `bdist_axle` before 0.0.13, whose `.pth`
    `import` line passes the path `site` is processing.
    """
    _finalize(pth_path[:-len(PTH_SUFFIX)])


def _finalize(dist_path):
    dist_info_dir = dist_path + DIST_INFO_SUFFIX
    axle_done_path = jp(dist_info_dir, AXLE_DONE_FILE)

    # Double lock-check for performance
    if exists(axle_done_path):
        return

    lock_path = jp(dist_info_dir, AXLE_LOCK_FILE)

    # Lock in-process for thread race
    with inter_thread_lock:
        from filelock import FileLock  # Local import for speed

        # Lock inter-process for process race
        with FileLock(lock_path):
            # Double lock-check for performance
            if exists(axle_done_path):
                return

            with user_site_handler(dist_path):
                _run_installers(dist_info_dir)

            # Always the last step
            for suffix in _STARTUP_SUFFIXES:
                try:
                    os.unlink(dist_path + suffix)
                except OSError:
                    # The `.start` file is absent from the distributions built by
                    # `bdist_axle` before 0.0.13 and both will probably fail to be
                    # removed on Windows
                    pass
