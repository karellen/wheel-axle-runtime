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
from os.path import exists, join as jp
from threading import RLock

from wheel_axle.runtime.constants import AXLE_DONE_FILE, AXLE_LOCK_FILE

__version__ = "${dist_version}"

_DIST_INFO = "dist-info"

inter_thread_lock = RLock()


def finalize(pth_path):
    dist_info_dir = pth_path[:-3] + _DIST_INFO
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

            # Get metadata
            from wheel_axle.runtime._symlinks import SymlinksInstaller
            from wheel_axle.runtime._axle import AxleFinalizer

            installers = [SymlinksInstaller, AxleFinalizer]  # AxleFinalizer is always last!
            for installer in installers:
                installer(dist_info_dir).run()

            # Always the last step
            try:
                os.unlink(pth_path)
            except OSError:
                # This will probably fail on Windows
                pass
