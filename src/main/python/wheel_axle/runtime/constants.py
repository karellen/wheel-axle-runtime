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

AXLE_DONE_FILE = "axle.done"
AXLE_LOCK_FILE = "axle.lck"
SYMLINKS_FILE = "symlinks.txt"
REQUIRE_LIBPYTHON_FILE = "require-libpython"

DIST_INFO_SUFFIX = ".dist-info"
PTH_SUFFIX = ".pth"
START_SUFFIX = ".start"

# The PEP 829 startup entry point referenced by the `.start` file of every Axle
# distribution, honored by `site` starting with Python 3.15
START_ENTRY_POINT = "wheel_axle.runtime:start"

# The very same entry point spelled as a `.pth` `import` line, which covers the Python
# versions predating PEP 829. Deriving it from `START_ENTRY_POINT` is what keeps the two
# startup files calling the same thing, as the `site` documentation prescribes.
START_PTH_LINE = "import {0}; {0}.{1}();".format(*START_ENTRY_POINT.split(":"))
