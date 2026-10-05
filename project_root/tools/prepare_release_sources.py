"""Prepare a bounded, reproducible source asset; never install or run vendor code.

Inputs are pinned in third_party/release-source-manifest.json. 7-Zip is a system
prerequisite for inspecting official Qt supplier packages, not a downloaded tool.
This asset is intentionally not a statement of final binary correspondence.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "third_party/release-source-manifest.json"
MAX_DOWNLOAD = 100 * 1024 * 1024
MAX_TOTAL_DOWNLOAD = 300 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
MAX_ENTRIES = 100000
MAX_LISTING = 8 * 1024 * 1024
TIMEOUT = 120
PREFIX = "THIRD-PARTY-SOURCES/"


class SourceError(ValueError):
    """Fail closed on changed, missing, unsafe, or out-of-scope inputs."""


def safe_name(value: str) -> str:
    """Portable relative file names only, including on Windows extraction."""
    if not isinstance(value, str) or not value or len(value) > 500:
        raise SourceError("Invalid member name")
    parts = value.split("/")
    if any(c in value for c in "\\:\x00\r\n") or any(ord(c) < 32 for c in value):
        raise SourceError("Unsafe member name")
    for part in parts:
        if (part in ("", ".", "..") or part.endswith((".", " "))
                or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)):
            raise SourceError("Unsafe member name")
    if PurePosixPath(value).is_absolute():
        raise SourceError("Absolute member name")
    return value


def official_url(url: str) -> str:
    """Do not follow arbitrary mirrors, local URLs, credentials or query tokens."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port is not None or parsed.query or parsed.fragment
            or '%' in parsed.path):
        raise SourceError("Unsupported source URL")
    paths = {
        "master.qt.io": ("/archive/qt/6.11/6.11.2/submodules/", "/online/qtsdkrepository/windows_x86/desktop/qt6_6112/"),
        "files.pythonhosted.org": ("/packages/",),
        "archive.mesa3d.org": ("/older-versions/11.x/11.2.2/",),
        "releases.llvm.org": ("/3.6.2/",),
    }
    if parsed.hostname not in paths or not parsed.path.startswith(paths[parsed.hostname]):
        raise SourceError("Unsupported source destination")
    safe_name(parsed.path.lstrip("/"))
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceError("Source redirect refused; review and pin an official direct URL")


def check_pin(data: bytes, row: dict) -> None:
    if len(data) != row["size"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
        raise SourceError("Size/SHA-256 mismatch: " + row.get("filename", row.get("path", "input")))


def link_path(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def plain_file(path: Path) -> None:
    path = path.absolute()
    if link_path(path) or not path.is_file():
        raise SourceError("Expected a regular file: " + path.name)
    for parent in path.parents:
        if link_path(parent):
            raise SourceError("Symlink parent is not accepted")


def validate_manifest(manifest: dict) -> None:
    rows = manifest.get("downloads", [])
    if manifest.get("schema_version") != 1 or not 1 <= len(rows) <= 32:
        raise SourceError("Unsupported or empty source manifest")
    filenames, destinations = set(), set()
    total = 0
    for row in rows:
        filename = safe_name(row["filename"])
        if "/" in filename or filename.casefold() in filenames:
            raise SourceError("Duplicate or nested download name")
        filenames.add(filename.casefold())
        official_url(row["url"])
        if not row["url"].endswith("/" + filename):
            raise SourceError("Download name disagrees with pinned URL")
        if type(row["size"]) is not int or not 0 < row["size"] <= MAX_DOWNLOAD:
            raise SourceError("Unbounded download")
        if not re.fullmatch("[0-9a-f]{64}", row["sha256"]):
            raise SourceError("Invalid SHA-256")
        total += row["size"]
        if row["kind"] not in {"source", "7z-evidence", "zip-evidence"}:
            raise SourceError("Unsupported download kind")
        files = [row] if row["kind"] == "source" else row.get("files", [])
        if not 1 <= len(files) <= 1000:
            raise SourceError("Empty or excessive selection")
        selected = set()
        for item in files:
            target = safe_name(item["destination"])
            if target.casefold() in destinations:
                raise SourceError("Duplicate output destination")
            destinations.add(target.casefold())
            if row["kind"] != "source":
                name = safe_name(item["path"])
                if name.casefold() in selected:
                    raise SourceError("Duplicate selected member")
                selected.add(name.casefold())
                if type(item["size"]) is not int or not 0 < item["size"] <= MAX_MEMBER:
                    raise SourceError("Unbounded selected member")
                if not re.fullmatch("[0-9a-f]{64}", item["sha256"]):
                    raise SourceError("Invalid selected SHA-256")
                if name.lower().endswith((".dll", ".exe", ".pyd", ".whl", ".7z")):
                    raise SourceError("Binary supplier delivery is out of scope")
    if total > MAX_TOTAL_DOWNLOAD:
        raise SourceError("Total downloads exceed budget")


def fetch(row: dict, cache: Path, offline: bool = False) -> Path:
    path = cache / row["filename"]
    if path.exists() or path.is_symlink():
        plain_file(path)
        if path.stat().st_size != row["size"]:
            raise SourceError("Cached download size mismatch: " + path.name)
        check_pin(path.read_bytes(), row)
        return path
    if offline:
        raise SourceError("Required cached input is missing: " + path.name)
    url = official_url(row["url"])
    opener = urllib.request.build_opener(NoRedirect())
    # All redirects are denied before another request is made. Limit actual bytes,
    # not only Content-Length; no downloaded code is imported or executed.
    with opener.open(url, timeout=TIMEOUT) as response:
        if response.geturl() != url or response.status != 200:
            raise SourceError("Unexpected download response")
        length = response.headers.get("Content-Length")
        if length is not None and int(length) != row["size"]:
            raise SourceError("Download Content-Length mismatch")
        data = response.read(row["size"] + 1)
    check_pin(data, row)
    path.write_bytes(data)
    return path


def validate_source_archive(path: Path) -> None:
    """Inspect only; original archives and licenses are preserved byte-for-byte."""
    seen, count, total = set(), 0, 0
    with tarfile.open(path, "r:*") as archive:
        for member in archive:
            name = safe_name(member.name.rstrip("/") if member.isdir() else member.name)
            if name in seen:
                raise SourceError("Duplicate source archive member")
            seen.add(name)
            if not (member.isfile() or member.isdir()) or member.issparse():
                raise SourceError("Source archive links/special files are not accepted")
            count += 1
            total += member.size
            if member.size < 0 or count > MAX_ENTRIES or total > MAX_EXPANDED:
                raise SourceError("Source archive exceeds inspection budget")
    if not count:
        raise SourceError("Empty source archive")


def bounded_command(args: list[str], maximum: int) -> bytes:
    """System tool only; cap output and wall time without a shell or disk extract."""
    with tempfile.TemporaryFile() as errors:
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors) as process:
            timer = threading.Timer(TIMEOUT, process.kill)
            timer.start()
            try:
                data = process.stdout.read(maximum + 1)
                if len(data) > maximum:
                    process.kill()
                    raise SourceError("7-Zip output exceeds pinned size limit")
                if process.wait() != 0:
                    raise SourceError("7-Zip failed or timed out")
                return data
            finally:
                timer.cancel()


def seven_zip_inventory(data: bytes) -> dict[str, dict]:
    """Parse 7z l -slt -ba output, rejecting links and ambiguous entries."""
    text = data.decode("utf-8-sig").replace("\r\n", "\n")
    result = {}
    total = 0
    for block in re.split(r"\n\s*\n", text.strip()):
        fields = {}
        for line in block.splitlines():
            if " = " not in line:
                raise SourceError("Unsupported 7-Zip listing")
            key, value = line.split(" = ", 1)
            if key in fields:
                raise SourceError("Duplicate 7-Zip field")
            fields[key] = value
        attrs = fields.get("Attributes", "")
        is_directory = fields.get("Folder") == "+" or attrs.startswith("D")
        name = fields.get("Path", "")
        name = safe_name(name.rstrip("/") if is_directory else name)
        if name.casefold() in result:
            raise SourceError("Duplicate supplier member")
        if (any(fields.get(k) for k in ("Symbolic Link", "Hard Link"))
                or fields.get("Anti", "-") != "-"
                or "l" in attrs.split(" ")[-1][:1]
                or fields.get("Encrypted", "-") != "-"):
            raise SourceError("Supplier links or unsupported entries are not accepted")
        size = int(fields.get("Size", "-1"))
        if size < 0:
            raise SourceError("Supplier member has invalid size")
        total += size
        result[name.casefold()] = fields
        if len(result) > MAX_ENTRIES or total > MAX_EXPANDED:
            raise SourceError("Supplier archive exceeds inspection budget")
    return result


def selected_7z(path: Path, row: dict, executable: str) -> dict[str, bytes]:
    listing = bounded_command([executable, "l", "-slt", "-ba", "-sccUTF-8", "--", str(path)], MAX_LISTING)
    inventory = seven_zip_inventory(listing)
    result = {}
    for item in row["files"]:
        entry = inventory.get(item["path"].casefold())
        if (entry is None or entry["Path"] != item["path"]
                or int(entry["Size"]) != item["size"] or entry.get("Folder") == "+"):
            raise SourceError("Missing or changed supplier member: " + item["path"])
        data = bounded_command([executable, "x", "-so", "-bd", "-y", "-spd", "--", str(path), item["path"]], item["size"])
        check_pin(data, item)
        result[item["destination"]] = data
    return result


def selected_zip(path: Path, row: dict) -> dict[str, bytes]:
    result = {}
    with zipfile.ZipFile(path) as archive:
        entries = {}
        total = 0
        for member in archive.infolist():
            name = safe_name(member.filename.rstrip("/") if member.is_dir() else member.filename)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))):
                raise SourceError("Wheel links/special files are not accepted")
            if name.casefold() in entries or member.flag_bits & 1:
                raise SourceError("Duplicate or encrypted wheel member")
            entries[name.casefold()] = member
            total += member.file_size
            if len(entries) > MAX_ENTRIES or total > MAX_EXPANDED:
                raise SourceError("Wheel exceeds inspection budget")
        for item in row["files"]:
            entry = entries.get(item["path"].casefold())
            if entry is None or entry.filename != item["path"] or entry.file_size != item["size"] or entry.is_dir():
                raise SourceError("Missing or changed wheel member: " + item["path"])
            with archive.open(entry) as stream:
                data = stream.read(item["size"] + 1)
            check_pin(data, item)
            result[item["destination"]] = data
    return result


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def notice_files(root: Path, additional: list[dict] | None = None) -> dict[str, bytes]:
    """Only inventory-named repository notices; never recursively copy a checkout."""
    base = root / "third_party"
    native = json.loads((base / "native-source-inventory.json").read_text(encoding="utf-8"))
    wheels = json.loads((base / "wheel-inventory.json").read_text(encoding="utf-8"))
    result = {}
    for row in native["files"]:
        name = "native-notices/" + safe_name(row["path"])
        path = base / name
        plain_file(path)
        data = path.read_bytes()
        check_pin(data, row)
        result["notices/" + name] = data
    names = {safe_name(p["notice_file"]) for p in wheels["packages"]}
    names.update({"licenses/cpython-3.12.10.txt", "licenses/dejavu-font.txt"})
    for name in sorted(names):
        if not name.startswith("licenses/") or not name.endswith(".txt"):
            raise SourceError("Notice outside approved directory")
        path = base / name
        plain_file(path)
        if path.stat().st_size > MAX_MEMBER:
            raise SourceError("Oversized repository notice")
        result["notices/" + name] = path.read_bytes()
    for row in additional or []:
        name = safe_name(row["path"])
        if not name.startswith("licenses/") or not name.endswith(".txt"):
            raise SourceError("Additional notice outside approved directory")
        path = base / name
        plain_file(path)
        if path.stat().st_size > MAX_MEMBER:
            raise SourceError("Oversized additional notice")
        data = path.read_bytes()
        check_pin(data, row)
        if "notices/" + name in result:
            raise SourceError("Duplicate additional notice")
        result["notices/" + name] = data
    result["notices/native-source-inventory.json"] = json_bytes(native)
    result["notices/wheel-inventory.json"] = json_bytes(wheels)
    return result


def write_bundle(files: dict[str, bytes | Path], output: Path) -> dict:
    """Sorted regular members, fixed epoch/mode/owner and deterministic gzip header."""
    seen = set()
    checksums = []
    snapshot = {}
    total = 0
    for name, content in sorted(files.items()):
        safe_name(name)
        if name.casefold() in seen or name == "SHA256SUMS":
            raise SourceError("Duplicate or reserved output name")
        seen.add(name.casefold())
        if isinstance(content, Path):
            plain_file(content)
            data = content.read_bytes()
        else:
            data = content
        total += len(data)
        if total > MAX_TOTAL_DOWNLOAD or len(snapshot) >= MAX_ENTRIES:
            raise SourceError("Bundle exceeds output budget")
        snapshot[name] = data
        checksums.append(hashlib.sha256(data).hexdigest() + "  " + name + "\n")
    files = {**snapshot, "SHA256SUMS": "".join(checksums).encode("utf-8")}
    output = output.absolute()
    for path in (output, *output.parents):
        if link_path(path):
            raise SourceError("Output may not use a symlink")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".source-bundle-", delete=False) as raw:
            temporary = Path(raw.name)
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                    for name, content in sorted(files.items()):
                        data = content
                        item = tarfile.TarInfo(PREFIX + name)
                        item.size, item.mode, item.mtime = len(data), 0o644, 0
                        item.uid = item.gid = 0
                        item.uname = item.gname = ""
                        archive.addfile(item, io.BytesIO(data))
        os.replace(temporary, output)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return {"filename": output.name, "size": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "file_count": len(files), "final_artifact_correspondence_verified": False,
            "delivery_status": "prepared; publication and durable recipient access not verified"}


def add_files(files: dict, additions: dict) -> None:
    existing = {name.casefold() for name in files}
    for name, content in additions.items():
        safe_name(name)
        if name.casefold() in existing:
            raise SourceError("Cross-input destination collision")
        existing.add(name.casefold())
        files[name] = content


def prepare(output: Path, cache: Path, offline: bool = False) -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    cache = cache.absolute()
    for path in (cache, *cache.parents):
        if link_path(path):
            raise SourceError("Cache may not use a symlink")
    cache.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("7z") or shutil.which("7zz")
    if not executable:
        raise SourceError("System 7z or 7zz is required for supplier evidence; no vendor software is executed")
    files = notice_files(ROOT, manifest.get("additional_notices", []))
    files["source-manifest.json"] = json_bytes(manifest)
    correspondence = json.loads((ROOT / "third_party/release-source-correspondence.json").read_text(encoding="utf-8"))
    files["supplier-correspondence.json"] = json_bytes(correspondence)
    files["README.txt"] = (ROOT / "third_party/RELEASE_SOURCES.txt").read_bytes().replace(b"\r\n", b"\n")
    for row in manifest["downloads"]:
        path = fetch(row, cache, offline)
        if row["kind"] == "source":
            validate_source_archive(path)
            data = path.read_bytes()
            check_pin(data, row)
            add_files(files, {row["destination"]: data})
        elif row["kind"] == "7z-evidence":
            add_files(files, selected_7z(path, row, executable))
        else:
            add_files(files, selected_zip(path, row))
    return write_bundle(files, output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/release-sources/THIRD-PARTY-SOURCES.tar.gz"))
    parser.add_argument("--cache-dir", type=Path, default=Path("build/release-source-cache"))
    parser.add_argument("--offline", action="store_true", help="Require every hash-pinned download in the cache")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output, args.cache_dir, args.offline), sort_keys=True))
    except (SourceError, OSError, tarfile.TarError, zipfile.BadZipFile, KeyError) as error:
        parser.exit(1, "Source preparation failed: " + str(error) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
