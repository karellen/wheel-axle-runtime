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

from pybuilder.core import (use_plugin, init, Author)

use_plugin("python.core")
use_plugin("python.integrationtest")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")
use_plugin("python.pycharm")
use_plugin("python.coveralls")
use_plugin("copy_resources")
use_plugin("filter_resources")

name = "wheel-axle-runtime"
version = "0.0.1.dev"

summary = "Axle Runtime is the runtime part of the Python Wheel enhancement library"
authors = [Author("Karellen, Inc.", "supervisor@karellen.co")]
maintainers = [Author("Arcadiy Ivanov", "arcadiy@karellen.co")]
url = "https://github.com/karellen/wheel-axle-runtime"
urls = {
    "Bug Tracker": "https://github.com/karellen/wheel-axle-runtime/issues",
    "Source Code": "https://github.com/karellen/wheel-axle-runtime/",
    "Documentation": "https://github.com/karellen/wheel-axle-runtime/"
}
license = "Apache License, Version 2.0"

requires_python = ">=3.7"

default_task = ["analyze", "publish"]


@init
def set_properties(project):
    project.depends_on("pip")
    project.depends_on("filelock")

    project.set_property("coverage_break_build", False)

    project.set_property("integrationtest_inherit_environment", True)

    project.set_property("flake8_break_build", True)
    project.set_property("flake8_extend_ignore", "E303,E402")
    project.set_property("flake8_include_test_sources", True)
    project.set_property("flake8_include_scripts", True)
    project.set_property("flake8_max_line_length", 130)

    project.set_property("copy_resources_target", "$dir_dist/wheel_axle/runtime")
    project.get_property("copy_resources_glob").append("LICENSE")
    project.include_file("wheel_axle/runtime", "LICENSE")

    project.set_property("filter_resources_target", "$dir_dist")
    project.get_property("filter_resources_glob").append("wheel_axle/runtime/__init__.py")

    project.set_property("distutils_readme_description", True)
    project.set_property("distutils_description_overwrite", True)
    project.set_property("distutils_upload_skip_existing", True)
    project.set_property("distutils_setup_keywords", ["wheel", "packaging",
                                                      "setuptools", "bdist_wheel",
                                                      "symlink", "postinstall"])

    project.set_property("pybuilder_header_plugin_break_build", False)

    project.set_property("distutils_classifiers", [
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Topic :: System :: Archiving :: Packaging",
        "Topic :: Software Development :: Build Tools",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta"
    ])
