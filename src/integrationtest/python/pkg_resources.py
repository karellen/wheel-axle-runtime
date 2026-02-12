from __future__ import annotations

import dataclasses
import re
import sys
import types
from collections.abc import Iterable
from importlib.metadata import PathDistribution

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet, InvalidSpecifier

try:
    import importlib.metadata as meta
except ImportError:
    import importlib_metadata as meta

__all__ = ["SpecifierSet", "InvalidSpecifier"]


def safe_extra(extra: str) -> str:
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.-]+', '_', extra).lower()


class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""

    def __repr__(self) -> str:
        return self.__class__.__name__ + repr(self.args)


class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""


@dataclasses.dataclass
class Distribution:
    project_name: str
    version: str
    location: str
    _path_dist: PathDistribution

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _compute_dependencies(self) -> dict[str | None, list[Requirement]]:
        """Recompute this distribution's dependencies."""
        self.__dep_map: dict[str | None, list[Requirement]] = {None: []}

        reqs: list[Requirement] = list(Requirement(req_str) for req_str in self._path_dist.requires or ())

        def reqs_for_extra(extra):
            for req in reqs:
                if not req.marker or req.marker.evaluate({'extra': extra}):
                    req.project_name = req.name
                    yield req

        common = types.MappingProxyType(dict.fromkeys(reqs_for_extra(None)))
        self.__dep_map[None].extend(common)

        for extra in self._path_dist.metadata.get_all('Provides-Extra') or []:
            s_extra = safe_extra(extra.strip())
            self.__dep_map[s_extra] = [
                r for r in reqs_for_extra(extra) if r not in common
            ]

        return self.__dep_map

    def requires(self, extras: Iterable[str] = ()) -> list[Requirement]:
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps: list[Requirement] = []
        deps.extend(dm.get(None, ()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError as e:
                raise UnknownExtra(f"{self} has no such extra feature {ext!r}") from e
        return deps


class WorkingSet:
    def __init__(self, paths=None):
        self.paths = paths if paths is not None else list(sys.path)
        self._results = None

    def __iter__(self):
        if self._results is None:
            self.refresh()
        return iter(self._results)

    @property
    def by_key(self):
        return {r.project_name: r for r in self.refresh()}

    def refresh(self):
        results = []
        for dist in meta.Distribution.discover(path=self.paths):
            results.append(Distribution(dist.metadata.get("Name"),
                                        dist.version,
                                        dist._path.parent,
                                        dist))
        results.sort(key=lambda x: x.project_name)
        self._results = results
        return results

    def add_entry(self, path):
        self.paths.append(path)
