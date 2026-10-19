import os
from dataclasses import dataclass

from .extractors import EXTRACTORS, PlaintextExtractor


class PathTraversalError(Exception):
    pass


@dataclass
class LocalFileResult:
    path: str
    ok: bool
    title: str | None = None
    text: str | None = None
    error: str | None = None


def resolve_case_path(case_dir, rel_path):
    if ":" in rel_path:
        raise PathTraversalError(f"{rel_path!r} contains a colon (NTFS ADS / drive syntax not allowed)")
    for component in rel_path.replace("\\", "/").split("/"):
        if component in ("", ".", ".."):
            continue
        stripped = component.rstrip(". ")
        if stripped == "":
            raise PathTraversalError(f"{rel_path!r} has a component that collapses onto the uploads directory")
        if stripped != component:
            raise PathTraversalError(f"{rel_path!r} has a trailing dot/space component Windows would silently rewrite")

    base = os.path.realpath(os.path.join(case_dir, "uploads"))
    target = os.path.realpath(os.path.join(base, rel_path))
    try:
        inside = os.path.commonpath([base, target]) == base
    except ValueError:
        # Different drives (e.g. C:\ target when case is on D:\) -> escape.
        inside = False
    if not inside:
        raise PathTraversalError(f"{rel_path!r} escapes the case uploads directory")
    return target


class LocalFileLoader:
    def __init__(self, config=None):
        cfg = (config or {}).get("localfiles", {})
        self.max_bytes = cfg.get("max_bytes", 20_000_000)
        self.timeout = cfg.get("timeout", 60)

    def load(self, case_dir, rel_path):
        try:
            abs_path = resolve_case_path(case_dir, rel_path)
        except PathTraversalError as e:
            return LocalFileResult(rel_path, False, error=str(e))

        if not os.path.isfile(abs_path):
            return LocalFileResult(rel_path, False, error="file not found in case uploads directory")
        if os.path.getsize(abs_path) > self.max_bytes:
            return LocalFileResult(rel_path, False, error=f"file exceeds max_bytes ({self.max_bytes})")

        ext = os.path.splitext(abs_path)[1].lower()
        extractor = EXTRACTORS.get(ext, PlaintextExtractor())
        if not extractor.available():
            return LocalFileResult(rel_path, False, error=f"{extractor.name} not installed, cannot extract {ext}")

        result = extractor.run(abs_path, timeout=self.timeout)
        if result.error:
            return LocalFileResult(rel_path, False, error=result.error)
        return LocalFileResult(rel_path, True, title=os.path.basename(abs_path), text=result.raw)
