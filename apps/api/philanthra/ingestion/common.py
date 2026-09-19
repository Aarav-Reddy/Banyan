"""Bounded, persistence-free normalization. Inputs are untrusted data."""

import hashlib
import io
import re
import time
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath

from defusedxml import ElementTree

PARSER_VERSION = "philanthra-import-v1"
MAX_BYTES = 5 * 1024 * 1024
MAX_EXPANDED_BYTES = 20 * 1024 * 1024
MAX_ROWS = 5000
MAX_COLUMNS = 64
MAX_CELL = 10000
MAX_PAGES = 40
MAX_SECONDS = 15


class ImportProblem(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def envelope(payload, kind):
    return {
        "records": [],
        "diagnostics": [],
        "columns": [],
        "preview": [],
        "kind": kind,
        "status": "validated",
        "checksum": hashlib.sha256(payload).hexdigest(),
        "parser_version": PARSER_VERSION,
    }


def issue(result, code, message, *, row=None, field=None, severity="error"):
    diagnostic = {"code": code, "message": message, "severity": severity}
    if row is not None:
        diagnostic["row"] = row
    if field is not None:
        diagnostic["field"] = field
    result["diagnostics"].append(diagnostic)


def finish(result):
    if any(d["severity"] == "error" for d in result["diagnostics"]):
        result["status"] = "partial" if result["records"] else "invalid"
    return result


def size_check(payload):
    if not payload:
        raise ImportProblem("empty_file", "The file is empty.")
    if len(payload) > MAX_BYTES:
        raise ImportProblem("file_too_large", "The file exceeds the 5 MiB import limit.")


def deadline_check(start):
    if time.monotonic() - start > MAX_SECONDS:
        raise ImportProblem("time_limit", "Import processing exceeded its time limit.")


def decimal_string(value, *, nonnegative=False):
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if not re.fullmatch(r"-?\d{1,20}(?:\.\d{1,8})?", text):
        raise ImportProblem("invalid_number", "Use a finite decimal number without separators.")
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ImportProblem("invalid_number", "Invalid decimal number.") from exc
    if not number.is_finite() or (nonnegative and number < 0):
        raise ImportProblem("invalid_number", "The value must be a finite nonnegative number.")
    return format(number, "f")


def xml_root(payload):
    size_check(payload)
    try:
        root = ElementTree.fromstring(
            payload, forbid_dtd=True, forbid_entities=True, forbid_external=True
        )
    except Exception as exc:
        raise ImportProblem(
            "unsafe_or_malformed_xml", "XML is malformed or uses forbidden declarations."
        ) from exc
    count = 0
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > 50000 or depth > 40:
            raise ImportProblem("xml_limit", "XML exceeds the node or depth limit.")
        stack.extend((child, depth + 1) for child in node)
    return root


def archive_entries(payload):
    """Read safe local ZIP contents without extracting anything onto the filesystem."""
    size_check(payload)
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ImportProblem("invalid_archive", "The archive is not a valid ZIP file.") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > 200:
            raise ImportProblem("archive_limit", "Archive has too many entries.")
        total = 0
        names = set()
        for entry in infos:
            name = entry.filename
            path = PurePosixPath(name)
            mode = entry.external_attr >> 16
            if (
                name in names
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in name
                or ":" in name
                or mode & 0o170000 == 0o120000
                or entry.flag_bits & 1
            ):
                raise ImportProblem(
                    "unsafe_archive", "Archive contains an unsafe, duplicate or encrypted entry."
                )
            names.add(name)
            total += entry.file_size
            if total > MAX_EXPANDED_BYTES or entry.file_size > MAX_BYTES:
                raise ImportProblem("archive_limit", "Archive exceeds expanded size limits.")
            if entry.file_size > 100 * max(entry.compress_size, 1):
                raise ImportProblem("archive_ratio", "Archive compression ratio exceeds the limit.")
        result = {}
        for entry in infos:
            if not entry.is_dir():
                with archive.open(entry) as stream:
                    data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    raise ImportProblem("archive_limit", "Expanded entry exceeds the limit.")
                result[entry.filename] = data
        return result
