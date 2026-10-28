"""Bounded source delivery, not certification of redistribution or binary identity."""
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import stat
import tarfile
from unittest.mock import patch
import zipfile

import pytest

from tools import prepare_release_sources as sources
from tests.zip_fixtures import raw_zip_info, zip_separators


def pin(data, **extra):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest(), **extra}


def source_row(data=b"source"):
    return pin(data, filename="pyqt6-6.11.0.tar.gz", kind="source",
               destination="sources/pyqt6-6.11.0.tar.gz",
               url="https://files.pythonhosted.org/packages/abc/pyqt6-6.11.0.tar.gz")


def test_committed_manifest_is_pinned_bounded_and_scoped():
    raw = sources.MANIFEST.read_text()
    manifest = json.loads(raw)
    sources.validate_manifest(manifest)
    assert manifest["final_artifact_correspondence_verified"] is False
    assert len([r for r in manifest["downloads"] if r["kind"] == "source"]) == 8
    assert all("?" not in row["url"] for row in manifest["downloads"])
    assert not any(x in raw for x in ("/workspace/", "/tmp/", "file://", "localhost", "token=", "saved_as"))
    correspondence = (sources.ROOT / "third_party/release-source-correspondence.json").read_text()
    assert "/workspace/" not in correspondence
    data = json.loads(correspondence)
    assert len(data["retained_qt_pe_rows"]) == 20
    assert all(r["final_sorth_artifact_file_hash_verified"] is False for r in data["retained_qt_pe_rows"])
    assert all(r["wheel_to_supplier_file_match"] for r in data["retained_qt_pe_rows"])


@pytest.mark.parametrize("url", [
    "file:///tmp/sources.tar.gz", "http://files.pythonhosted.org/packages/x",
    "https://files.pythonhosted.org.evil.example/packages/x", "https://localhost/packages/x",
    "https://user:secret@files.pythonhosted.org/packages/x", "https://files.pythonhosted.org:443/packages/x",
    "https://files.pythonhosted.org/packages/x?token=secret", "https://files.pythonhosted.org/packages/x#token",
    "https://files.pythonhosted.org/packages/../x", "https://files.pythonhosted.org/packages/%2e%2e/x",
    "https://download.qt.io/archive/qt/6.11/6.11.2/submodules/x", "https://master.qt.io/private/x",
])
def test_unsupported_destinations_rejected(url):
    with pytest.raises(sources.SourceError):
        sources.official_url(url)


def test_redirect_rejected_before_followup_request():
    with pytest.raises(sources.SourceError, match="redirect refused"):
        sources.NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://example.org/x")


@pytest.mark.parametrize("name", ["../x", "/x", "a/../../x", "a\\x", "C:/x", "a:stream", "a//x", "a/./x", "a\nsecret", "a\x00x", "AUX.txt", "foo.", "foo "])
def test_unsafe_names_rejected(name):
    with pytest.raises(sources.SourceError):
        sources.safe_name(name)


def test_manifest_rejects_missing_duplicate_and_oversized_content():
    base = {"schema_version": 1, "downloads": [source_row()]}
    for patch in ({"size": sources.MAX_DOWNLOAD + 1}, {"sha256": "bad"}, {"filename": "../bad"}, {"kind": "execute"}):
        manifest = copy.deepcopy(base)
        manifest["downloads"][0].update(patch)
        with pytest.raises(sources.SourceError):
            sources.validate_manifest(manifest)
    manifest = {"schema_version": 1, "downloads": [source_row(), source_row()]}
    with pytest.raises(sources.SourceError, match="Duplicate"):
        sources.validate_manifest(manifest)
    row = {**source_row(), "kind": "zip-evidence", "files": []}
    with pytest.raises(sources.SourceError, match="Empty"):
        sources.validate_manifest({"schema_version": 1, "downloads": [row]})


def test_cache_tamper_missing_and_symlink_rejected(tmp_path):
    row = source_row()
    with pytest.raises(sources.SourceError, match="missing"):
        sources.fetch(row, tmp_path, offline=True)
    path = tmp_path / row["filename"]
    path.write_bytes(b"tamper")
    with pytest.raises(sources.SourceError, match="SHA-256"):
        sources.fetch(row, tmp_path, offline=True)
    path.write_bytes(b"source")
    assert sources.fetch(row, tmp_path, offline=True) == path
    link = tmp_path / "link"
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("Symlink creation not available on this runner")
    with pytest.raises(sources.SourceError):
        sources.plain_file(link)


def test_download_length_and_hash_are_verified(tmp_path, monkeypatch):
    row = source_row()
    class Response(io.BytesIO):
        status = 200
        headers = {}
        def geturl(self):
            return row["url"]
    class Opener:
        data = b"source"
        def open(self, url, timeout):
            assert url == row["url"] and timeout == sources.TIMEOUT
            return Response(self.data)
    opener = Opener()
    monkeypatch.setattr(sources.urllib.request, "build_opener", lambda *a: opener)
    opener.data = b"source-more-than-pinned-size"
    with pytest.raises(sources.SourceError):
        sources.fetch(row, tmp_path)
    assert not (tmp_path / row["filename"]).exists()
    opener.data = b"tamper"
    with pytest.raises(sources.SourceError):
        sources.fetch(row, tmp_path)
    opener.data = b"source"
    assert sources.fetch(row, tmp_path).read_bytes() == b"source"


def make_tar(path, name="pkg/LICENSE", kind=tarfile.REGTYPE, duplicate=False):
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(name)
        info.type = kind
        info.size = 3 if kind == tarfile.REGTYPE else 0
        info.linkname = "../escape" if kind != tarfile.REGTYPE else ""
        archive.addfile(info, io.BytesIO(b"abc") if info.size else None)
        if duplicate:
            archive.addfile(info, io.BytesIO(b"abc"))


@pytest.mark.parametrize("kind", [tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE])
def test_source_links_special_files_rejected(tmp_path, kind):
    path = tmp_path / "source.tar.gz"
    make_tar(path, kind=kind)
    with pytest.raises(sources.SourceError):
        sources.validate_source_archive(path)


def test_source_traversal_duplicates_and_budget_rejected(tmp_path, monkeypatch):
    path = tmp_path / "source.tar.gz"
    make_tar(path)
    sources.validate_source_archive(path)
    make_tar(path, name="../escape")
    with pytest.raises(sources.SourceError):
        sources.validate_source_archive(path)
    make_tar(path, duplicate=True)
    with pytest.raises(sources.SourceError, match="Duplicate"):
        sources.validate_source_archive(path)
    make_tar(path)
    monkeypatch.setattr(sources, "MAX_EXPANDED", 2)
    with pytest.raises(sources.SourceError, match="budget"):
        sources.validate_source_archive(path)


def test_zip_only_pinned_text_selected_and_original_bytes_kept(tmp_path):
    path = tmp_path / "vendor.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("bindings/core.sip", b"original\r\n")
        archive.writestr("bin/vendor.dll", b"not-delivered")
    item = pin(b"original\r\n", path="bindings/core.sip", destination="evidence/core.sip")
    assert sources.selected_zip(path, {"files": [item]}) == {"evidence/core.sip": b"original\r\n"}
    item["sha256"] = "0" * 64
    with pytest.raises(sources.SourceError):
        sources.selected_zip(path, {"files": [item]})
    item["path"] = "missing"
    with pytest.raises(sources.SourceError, match="Missing"):
        sources.selected_zip(path, {"files": [item]})


@pytest.mark.parametrize("name,mode", [("../escape", 0), ("link", stat.S_IFLNK | 0o777)])
def test_zip_traversal_and_symlink_rejected(tmp_path, name, mode):
    path = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(path, "w") as archive:
        member = zipfile.ZipInfo(name)
        member.external_attr = mode << 16
        archive.writestr(member, "target")
    with pytest.raises(sources.SourceError):
        sources.selected_zip(path, {"files": []})


@pytest.mark.parametrize("separator", ["/", "\\"])
@pytest.mark.parametrize("name", ["bindings\\core.sip", "bindings/core.sip\x00hidden",
                                "bindings//core.sip", "bindings/./core.sip",
                                "bindings//", "bindings/\x00hidden"])
@pytest.mark.parametrize("selected", [False, True])
def test_zip_raw_noncanonical_names_rejected_before_read(tmp_path, separator, name, selected):
    path = tmp_path / "raw.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(raw_zip_info(name), b"abc")
    item = pin(b"abc", path="bindings/core.sip", destination="evidence/core.sip")
    with zip_separators(separator), patch.object(zipfile.ZipFile, "open", side_effect=AssertionError("Read before validation")):
        with pytest.raises(sources.SourceError, match="member name"):
            sources.selected_zip(path, {"files": [item] if selected else []})


@pytest.mark.parametrize("separator", ["/", "\\"])
def test_zip_canonical_directory_and_selected_file_accepted(tmp_path, separator):
    path = tmp_path / "canonical.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(raw_zip_info("bindings/", stat.S_IFDIR | 0o755), b"")
        archive.writestr(raw_zip_info("bindings/core.sip"), b"abc")
    item = pin(b"abc", path="bindings/core.sip", destination="evidence/core.sip")
    with zip_separators(separator):
        assert sources.selected_zip(path, {"files": [item]}) == {"evidence/core.sip": b"abc"}


def listing(name="config.opt", size=3, extra=""):
    return f"Path = {name}\nSize = {size}\nAttributes = A\nEncrypted = -\n{extra}\n".encode()


def test_7z_streaming_selection_fake_cli(tmp_path, monkeypatch):
    path = tmp_path / "supplier.7z"
    item = pin(b"abc", path="config.opt", destination="supplier/config.opt")
    calls = []
    def run(args, maximum):
        calls.append(args)
        assert args[0] == "trusted-system-7z" and "--" in args
        if args[1] == "l":
            return listing()
        assert "-so" in args and "-spd" in args and args[-1] == "config.opt"
        assert maximum == 3
        return b"abc"
    monkeypatch.setattr(sources, "bounded_command", run)
    assert sources.selected_7z(path, {"files": [item]}, "trusted-system-7z") == {"supplier/config.opt": b"abc"}
    assert len(calls) == 2
    item["path"] = "missing"
    with pytest.raises(sources.SourceError, match="Missing"):
        sources.selected_7z(path, {"files": [item]}, "trusted-system-7z")


@pytest.mark.parametrize("reported", ["include/QtCore/config.opt", r"include\QtCore\config.opt",
                                     r"include\QtCore/config.opt"])
def test_7z_nested_selection_matches_canonical_pin_and_streams_listed_name(tmp_path, monkeypatch, reported):
    """The platform-specific listing must not change the pinned output bytes."""
    item = pin(b"abc", path="include/QtCore/config.opt", destination="supplier/config.opt")
    calls = []

    def run(args, maximum):
        calls.append(args)
        if args[1] == "l":
            return listing(reported)
        assert args[-1] == reported
        assert "-so" in args and "-spd" in args and "--" in args
        assert maximum == item["size"]
        return b"abc"

    monkeypatch.setattr(sources, "bounded_command", run)
    assert sources.selected_7z(tmp_path / "supplier.7z", {"files": [item]}, "system-7z") == {
        item["destination"]: b"abc",
    }
    assert len(calls) == 2


@pytest.mark.parametrize("reported", ["include/QtCore/", "include\\QtCore\\"])
@pytest.mark.parametrize("folder_field", ["Folder = +\n", ""])
def test_7z_directory_metadata_is_retained_without_reading_it(tmp_path, monkeypatch, reported, folder_field):
    """Attributes alone can identify a directory in a native 7-Zip listing."""
    data = f"Path = {reported}\nSize = 3\nAttributes = D\n{folder_field}\n".encode()
    calls = []

    def run(args, maximum):
        calls.append(args)
        assert args[1] == "l", "A directory must never be streamed as a selected file"
        return data

    monkeypatch.setattr(sources, "bounded_command", run)
    item = pin(b"abc", path="include/QtCore", destination="supplier/config.opt")
    with pytest.raises(sources.SourceError, match="Missing or changed"):
        sources.selected_7z(tmp_path / "supplier.7z", {"files": [item]}, "system-7z")
    assert len(calls) == 1


@pytest.mark.parametrize("reported", [r"..\escape", r"include\..\escape", r"C:\escape",
                                     r"C:escape", r"\\server\share", r"\absolute",
                                     r"include\\config.opt", r"include\.\config.opt",
                                     "include\\config.opt\\", r"include\AUX.txt",
                                     "include\\config.opt ", "include\\config.opt.",
                                     "include/config.opt\x00hidden"])
def test_7z_unsafe_names_report_archive_and_raw_member_without_extraction(tmp_path, monkeypatch, reported):
    """Separator adaptation preserves rejection and actionable error context."""
    calls = []

    def run(args, maximum):
        calls.append(args)
        assert args[1] == "l", "Invalid inventories must fail before extraction"
        return listing(reported)

    monkeypatch.setattr(sources, "bounded_command", run)
    with pytest.raises(sources.SourceError) as error:
        sources.selected_7z(tmp_path / "supplier.7z", {"files": []}, "system-7z")
    assert "supplier.7z" in str(error.value)
    assert repr(reported) in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("second", [r"include\QtCore\config.opt", "INCLUDE/qtcore/CONFIG.OPT"])
def test_7z_separator_and_case_aliases_cannot_hide_duplicate_members(second):
    with pytest.raises(sources.SourceError, match="Duplicate"):
        sources.seven_zip_inventory(listing("include/QtCore/config.opt") + listing(second))


@pytest.mark.parametrize("changed", ["size", "case", "bytes"])
def test_7z_windows_names_do_not_bypass_identity_size_or_content_pins(tmp_path, monkeypatch, changed):
    item = pin(b"abc", path="include/QtCore/config.opt", destination="supplier/config.opt")
    reported = r"include\QtCore\config.opt"
    if changed == "case":
        reported = reported.upper()
    calls = []

    def run(args, maximum):
        calls.append(args)
        if args[1] == "l":
            return listing(reported, size=4 if changed == "size" else 3)
        assert changed == "bytes", "Identity mismatches must fail before extraction"
        return b"bad"

    monkeypatch.setattr(sources, "bounded_command", run)
    with pytest.raises(sources.SourceError, match="SHA-256" if changed == "bytes" else "Missing or changed"):
        sources.selected_7z(tmp_path / "supplier.7z", {"files": [item]}, "system-7z")
    assert len(calls) == (2 if changed == "bytes" else 1)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("reported", ["include/QtCore/", "include\\QtCore\\"])
def test_7z_native_final_empty_fields_keep_the_field_separator(newline, reported):
    """Real supplier 7z archives end with directory records and an empty Block."""
    data = newline.join([f"Path = {reported}", "Size = 0", "Attributes = D drwxr-xr-x",
                         "CRC = ", "Encrypted = -", "Method = ", "Block = ", "", ""]).encode()
    member = sources.seven_zip_inventory(data)["include/qtcore"]
    assert member.name == "include/QtCore"
    assert member.listed_name == reported
    assert member.is_directory and member.size == 0


def test_7z_final_path_space_is_not_silently_trimmed():
    data = b"Size = 3\nAttributes = A\nEncrypted = -\nPath = config.opt \n\n"
    with pytest.raises(sources.SourceError, match="member"):
        sources.seven_zip_inventory(data)


@pytest.mark.parametrize("container", ["zip", "7z"])
def test_7z_native_nested_listing_and_streaming(tmp_path, container):
    """Exercise the system CLI on Windows CI instead of only a fake listing."""
    executable = shutil.which("7z") or shutil.which("7zz")
    if not executable:
        pytest.skip("System 7-Zip is required for the native listing regression")
    path = tmp_path / f"supplier.{container}"
    content = b"original supplier text\r\n"
    if container == "zip":
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("include/QtCore/", b"")
            archive.writestr("include/QtCore/config.opt", content)
            archive.writestr("include/QtCore/unselected.txt", b"not selected")
    else:
        directory = tmp_path / "include" / "QtCore"
        directory.mkdir(parents=True)
        (directory / "config.opt").write_bytes(content)
        (directory / "unselected.txt").write_bytes(b"not selected")
        sources.bounded_command([executable, "a", "-t7z", "-bd", "-y", "--", str(path),
                                 str(tmp_path / "include")], sources.MAX_LISTING)
    item = pin(content, path="include/QtCore/config.opt", destination="supplier/config.opt")
    assert sources.selected_7z(path, {"files": [item]}, executable) == {item["destination"]: content}


@pytest.mark.parametrize("data", [listing("../escape"), listing() + listing(), listing(extra="Symbolic Link = ../escape"), listing(extra="Hard Link = x"), listing(extra="Anti = +"), listing(extra="Encrypted = +"), listing(size=-1), b"invalid listing"])
def test_7z_malformed_duplicate_links_rejected(data):
    with pytest.raises(sources.SourceError):
        sources.seven_zip_inventory(data)


def test_7z_listing_oversized_rejected(monkeypatch):
    monkeypatch.setattr(sources, "MAX_EXPANDED", 2)
    with pytest.raises(sources.SourceError, match="budget"):
        sources.seven_zip_inventory(listing())


def test_output_deterministic_sorted_safe_and_preserves_licenses(tmp_path):
    one, two = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    files = {"z/LICENSE": b"original\r\nlicense", "sources/a.tar.gz": b"original archive"}
    result = sources.write_bundle(files, one)
    sources.write_bundle(dict(reversed(list(files.items()))), two)
    assert one.read_bytes() == two.read_bytes()
    assert result["final_artifact_correspondence_verified"] is False
    assert "publication" in result["delivery_status"]
    assert b"a.tar" not in one.read_bytes()[:30]
    with tarfile.open(one) as archive:
        members = archive.getmembers()
        assert [m.name for m in members] == sorted(m.name for m in members)
        assert all(m.isreg() and m.mtime == 0 and m.uid == m.gid == 0 and m.mode == 0o644 for m in members)
        assert archive.extractfile(sources.PREFIX + "z/LICENSE").read() == b"original\r\nlicense"
        lines = archive.extractfile(sources.PREFIX + "SHA256SUMS").read().decode().splitlines()
        for line in lines:
            digest, name = line.split("  ", 1)
            assert hashlib.sha256(archive.extractfile(sources.PREFIX + name).read()).hexdigest() == digest
    with pytest.raises(sources.SourceError):
        sources.write_bundle({"../escape": b"bad"}, one)
    assert one.read_bytes() == two.read_bytes()


def test_output_symlink_rejected(tmp_path):
    target = tmp_path / "target"
    target.write_bytes(b"keep")
    link = tmp_path / "output"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation not available on this runner")
    with pytest.raises(sources.SourceError):
        sources.write_bundle({"LICENSE": b"valid"}, link)
    assert target.read_bytes() == b"keep"


def test_repository_notices_preserve_inventory_and_editable_psl():
    files = sources.notice_files(sources.ROOT)
    assert any(name.endswith("public_suffix_list.dat") for name in files)
    assert any(name.endswith("psl-make-dafsa") for name in files)
    assert "notices/licenses/pyinstaller.txt" in files
    assert not any(name.endswith((".dll", ".exe", ".pyd")) for name in files)


def test_no_seven_zip_blocks_before_download(tmp_path, monkeypatch):
    monkeypatch.setattr(sources.shutil, "which", lambda name: None)
    with pytest.raises(sources.SourceError, match="System 7z"):
        sources.prepare(tmp_path / "result.tar.gz", tmp_path / "cache")
    assert not (tmp_path / "result.tar.gz").exists()


def test_cross_input_collisions_fail():
    files = {"notices/LICENSE": b"original"}
    with pytest.raises(sources.SourceError, match="collision"):
        sources.add_files(files, {"notices/license": b"changed"})
    assert files == {"notices/LICENSE": b"original"}


def test_path_content_is_snapshotted_once(tmp_path, monkeypatch):
    path = tmp_path / "original"
    path.write_bytes(b"original")
    original_read = Path.read_bytes
    reads = []
    def changing_read(self):
        if self == path:
            reads.append(True)
            return b"original" if len(reads) == 1 else b"changed"
        return original_read(self)
    monkeypatch.setattr(Path, "read_bytes", changing_read)
    output = tmp_path / "result.tar.gz"
    sources.write_bundle({"LICENSE": path}, output)
    assert len(reads) == 1
    with tarfile.open(output) as archive:
        data = archive.extractfile(sources.PREFIX + "LICENSE").read()
        sums = archive.extractfile(sources.PREFIX + "SHA256SUMS").read()
    assert data == b"original"
    assert hashlib.sha256(data).hexdigest().encode() in sums


def test_bounded_command_rejects_excess_output_and_timeout(monkeypatch):
    import sys
    with pytest.raises(sources.SourceError, match="limit"):
        sources.bounded_command([sys.executable, "-c", "print('abcdefgh')"], 3)
    monkeypatch.setattr(sources, "TIMEOUT", 0.1)
    with pytest.raises(sources.SourceError, match="timed out"):
        sources.bounded_command([sys.executable, "-c", "import time; time.sleep(10)"], 3)


def test_additional_notices_are_explicitly_hash_pinned(tmp_path):
    manifest = json.loads(sources.MANIFEST.read_text())
    rows = manifest["additional_notices"]
    assert {r["path"] for r in rows} == {
        "licenses/cpython-3.12.10-embed-amd64-LICENSE.txt",
        "licenses/qt-v6.11.2-llvmpipe-NOTICES.txt",
        "licenses/llvm-3.6.2-MD5-NOTICES.txt",
    }
    # Fixtures need no copying of supplier notices into this implementation commit.
    base = tmp_path / "third_party"
    (base / "licenses").mkdir(parents=True)
    (base / "native-source-inventory.json").write_text('{"files": []}')
    (base / "wheel-inventory.json").write_text('{"packages": []}')
    for name in ("cpython-3.12.10.txt", "dejavu-font.txt"):
        (base / "licenses" / name).write_bytes(b"fixture")
    (base / "licenses" / "extra.txt").write_bytes(b"original")
    row = pin(b"original", path="licenses/extra.txt")
    files = sources.notice_files(tmp_path, [row])
    assert files["notices/licenses/extra.txt"] == b"original"
    (base / "licenses" / "extra.txt").write_bytes(b"modified")
    with pytest.raises(sources.SourceError):
        sources.notice_files(tmp_path, [row])


def test_final_artifact_comparison_rows_cover_retained_paths_without_claiming_identity():
    data = json.loads((sources.ROOT / "third_party/release-source-correspondence.json").read_text())
    rows = data["artifact_file_expectations"]
    by_path = {r["packaged_path"]: r for r in rows}
    assert len(by_path) == len(rows)
    assert data["schema_version"] == 1
    assert data["final_artifact_correspondence_verified"] is False
    assert sum(r["required"] for r in rows) == 24
    assert sum(r["category"] == "qt-translation" for r in rows) == 217
    assert not any(r["required"] for r in rows if r["category"] == "qt-translation")
    for retained in data["retained_qt_pe_rows"]:
        row = by_path[retained["retained_path"]]
        assert row["required"] and row["source_delivery_in_scope"]
        assert row["sha256"] == retained["wheel_file_sha256"] == retained["official_file_sha256"]
    assert by_path["_internal/PyQt6/sip.cp312-win_amd64.pyd"]["sha256"] == "80e3122ad70cc48f71388f18b9094eb655c0950e129463967e33f7d102b78f4c"
    assert not by_path["_internal/PyQt6/Qt6/bin/Qt6Pdf.dll"]["source_delivery_in_scope"]
    pins = {r["filename"]: r["sha256"] for r in json.loads(sources.MANIFEST.read_text())["downloads"]}
    assert all(pins[r["wheel_filename"]] == r["wheel_sha256"] for r in rows)


def test_supplier_directory_trailing_separator_is_bounded():
    data = b"Path = include/QtCore/\nSize = 0\nAttributes = D\nFolder = +\n\n"
    assert "include/qtcore" in sources.seven_zip_inventory(data)
    with pytest.raises(sources.SourceError):
        sources.seven_zip_inventory(data.replace(b"include/QtCore/", b"../escape/"))


def test_selection_cannot_deliver_supplier_binary():
    row = {**source_row(), "kind": "zip-evidence", "files": [pin(b"abc", path="bin/native.dll", destination="evidence/native.dll")]}
    with pytest.raises(sources.SourceError, match="Binary"):
        sources.validate_manifest({"schema_version": 1, "downloads": [row]})
