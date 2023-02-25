# Axle-Runtime - Python Wheel enhancement library

[![Gitter](https://img.shields.io/gitter/room/karellen/Lobby?logo=gitter)](https://app.gitter.im/#/room/#karellen_Lobby:gitter.im)
[![Build Status](https://img.shields.io/github/actions/workflow/status/karellen/wheel-axle-runtime/build.yml?branch=master)](https://github.com/karellen/wheel-axle-runtime/actions/workflows/build.yml)
[![Coverage Status](https://img.shields.io/coveralls/github/karellen/wheel-axle-runtime/master?logo=coveralls)](https://coveralls.io/r/karellen/wheel-axle-runtime?branch=master)

[![PyBuilder Version](https://img.shields.io/pypi/v/wheel-axle-runtime?logo=pypi)](https://pypi.org/project/wheel-axle-runtime/)
[![PyBuilder Python Versions](https://img.shields.io/pypi/pyversions/wheel-axle-runtime?logo=pypi)](https://pypi.org/project/wheel-axle-runtime/)
[![PyBuilder Downloads Per Day](https://img.shields.io/pypi/dd/wheel-axle-runtime?logo=pypi)](https://pypi.org/project/wheel-axle-runtime/)
[![PyBuilder Downloads Per Week](https://img.shields.io/pypi/dw/wheel-axle-runtime?logo=pypi)](https://pypi.org/project/wheel-axle-runtime/)
[![PyBuilder Downloads Per Month](https://img.shields.io/pypi/dm/wheel-axle-runtime?logo=pypi)](https://pypi.org/project/wheel-axle-runtime/)

# This is a companion project to [Wheel Axle/bdist_axle](https://github.com/karellen/wheel-axle)

## Problem

1. Python wheels do not support symlinks.
2. PIP installation procedure is not locally extensible and does not allow adding post-install hooks.

## Solution

**WARNING: THIS IS EXPERIMENTAL BETA SOFTWARE. THERE ARE NO WARRANTIES OF ANY KIND. USE AT YOUR OWN RISK. ADDITIONAL
INCLUDED DISCLAIMERS ALSO APPLY.**

Wheel Axle Runtime library utilizes a little-known trick used in `site.py`'s `.pth` files that allows executing
arbitrary code while the site packages are being added. Thus, specially-crafted wheels can silently execute installed
code on Python interpreter startup, facilitating the "post-install hook" functionality.

### Python Invariants

The core functionality relies on the following Python behaviors:

* `site.py` [processes .pth files](https://github.com/python/cpython/blob/8b1b27f1939cc4060531d198fdb09242f247ca7c/Lib/site.py#L171)
* `site.py` [executes .pth import lines](https://github.com/python/cpython/blob/8b1b27f1939cc4060531d198fdb09242f247ca7c/Lib/site.py#L186)
* `.pth` file's line is executed with a local
  variable [`fullname` denoting the `.pth` file path](https://github.com/python/cpython/blob/8b1b27f1939cc4060531d198fdb09242f247ca7c/Lib/site.py#L170)

These invariants have not changed for *18 years*.

### Implementation

Once the distribution-specific `.pth` is executed by the Python interpreter, the Wheel Axle Runtime behaves as follows:

1. The library checks whether a file `.dist-info/axle.done` exists. If it does it is the indication that the
   post-install hook has executed successfully and nothing more is to be done, terminating all further processing.
2. A process-wide *inter-thread* lock is acquired.
3. An OS-wide *inter-process file* lock is acquired on a file `.dist-info/axle.lck`.
4. Once the locks are acquired the `.dist-info/axle.done` existence is rechecked (double-checked locking optimization).
5. Now that in-process and inter-process race conditions are excluded the post-install work can begin.
6. Registered `installers` are run in sequence. Installers *should be* idempotent. The following installers are
   currently implemented:
    1. *Symlinks installer* processes `.dist-info/symlinks.txt`, if any.
        1. Based on the location of the `.pth` file being executed the current installation `schema` and its paths are
           determined. Currently, installation into a virtual environment or user location is supported and tested.
        2. For each symlink the target path is resolved and `realpath` is used to determine the final target path.
        3. If the symlink path and symlink target path are within one of the permitted schema locations the symlink is
           created. Otherwise, an exception is raised and the processing is aborted.
        4. After all symlinks are created, the `.dist-info/RECORD` file is updated to reflect the created symlinks.
    2. *Axle installer* finalizes the installation. This installer is always executed last.
        1. The `.dist-info/RECORD` is updated with `.dist-info/axle.done` file record.
        2. `.dist-info/axle.done` is created.
        3. `<distribution name and version>.pth` is then removed. If the file cannot be removed it is left in place.
           This can happen on Windows, since the `.pth` file in question is likely opened for exclusive reading on
           Windows.
7. Any failure anywhere in the above process will result in an abort, an error message, and a retry the next time
   the `.pth` will be activated.

### Security

There are several security requirements and implications of having post-install hooks implemented this way.

1. The installation requires write permissions to the distribution. This will be a problem if the package is installed
   as `root` in locations such as `/usr` or `/usr/local`, or is otherwise not write-permitted, unless the post-install
   hook is also ran with the sufficient privileges. This is generally acceptable as the primary use is considered to be
   installation into virtual envs and user locations. That said, simply running `python -c pass` or any other python
   invocation that does activate `site.py` under the required privileges will finalize post-install procedures.
2. There is *an attempt* to ensure that that axle wheels symlinks and targets don't extend beyond the allowed `schema`
   locations. *Those attempts are **superficial** and **have not been formally verified**.* For example, it may be
   possible to escape the path validation/confinement by:
    * hacking symlink creation order
    * hacking symlink directory targets
    * exploiting OS-specific `realpath` implementation idiosyncrasies (i.e. `strict` vs not, and what is considered
      strict)

### TODOs

* Support schema detection for `home` and `prefix` installations.
* Validate and verify Windows support.
