"""Local file ingestion stage (parallel to fetcher/).

Extracts text from `file` artifacts uploaded into a case's uploads/
directory. Produces the same ok/text/title/error shape as
fetcher.Fetcher.fetch(), so downstream nlp/correlate stages stay
source-agnostic between web-fetched and locally-uploaded text.
"""

from .loader import LocalFileLoader, LocalFileResult, PathTraversalError, resolve_case_path

__all__ = ["LocalFileLoader", "LocalFileResult", "PathTraversalError", "resolve_case_path"]
