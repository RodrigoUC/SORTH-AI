"""Single source of Windows version and exact source identity (not a signature)."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def identity(commit):
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("VERSION must contain major.minor.patch")
    if any(int(part) > 65535 for part in version.split(".")):
        raise ValueError("Windows version component exceeds 65535")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full lowercase source commit SHA is required")
    return {"version": version, "source_commit": commit,
            "build_id": f"{version}-{commit[:12]}", "signed": False}

def generate(commit, output):
    info = identity(commit)
    output.mkdir(parents=True, exist_ok=True)
    parts = tuple(map(int, info["version"].split("."))) + (0,)
    resource = (ROOT / "windows_version_info.txt").read_text(encoding="utf-8")
    resource = resource.replace("(2, 0, 0, 0)", repr(parts))
    resource = resource.replace("'2.0.0'", repr(info["version"]))
    resource = resource.replace("StringStruct('ProductVersion', " + repr(info["version"]) + ")",
                                "StringStruct('ProductVersion', " + repr(info["build_id"]) + ")")
    (output / "windows_version_info.txt").write_text(resource, encoding="utf-8")
    (output / "build-identity.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("build/identity"))
    args = parser.parse_args()
    generate(args.commit, args.output)
