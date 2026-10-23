"""Build and verify the narrowly scoped public synthetic Replit project ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "futurepath-public-prototype-synthetic-v1.zip"
MANIFEST_NAME = "PUBLIC_PACKAGE_MANIFEST.json"
SCHEMA = "futurepath-public-synthetic-package-v1"
MEMBERS = (
    ".replit",
    ".streamlit/config.toml",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "app.py",
    "deployment/public_package.py",
    "domain/__init__.py",
    "domain/models.py",
    "fixtures/__init__.py",
    "fixtures/synthetic_profiles.json",
    "fixtures/synthetic_profiles.py",
    "fixtures/synthetic_requirements.json",
    "fixtures/synthetic_requirements.py",
    "requirements-public.lock",
    "services/__init__.py",
    "services/matching.py",
    "services/profile_intake.py",
    "services/synthetic_journey.py",
    "ui/__init__.py",
    "ui/skills_intake.py",
    "ui/synthetic_journey.py",
    "ui/synthetic_matching.py",
)
MAX_MEMBER_BYTES = 2_000_000
MAX_PACKAGE_BYTES = 10_000_000
FORBIDDEN_PATHS = (
    "data", "review_app.py", "ingestion", "storage", "tests",
    "ui/review_data.py", "ui/occupation_browser.py", ".env",
    ".streamlit/secrets.toml", "requirements.txt",
)


class PackageError(ValueError):
    """The public project is incomplete or contains forbidden content."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False) + "\n").encode("utf-8")


def _source_bytes(root: Path, name: str) -> bytes:
    path = root / name
    if any(part.is_symlink() for part in (path, *path.parents) if part != root.parent):
        raise PackageError(f"symlink in package source: {name}")
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise PackageError(f"missing or invalid package source: {name}")
    payload = path.read_bytes()
    if len(payload) > MAX_MEMBER_BYTES:
        raise PackageError(f"package member too large: {name}")
    return payload


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def build_package(root: Path = ROOT, output: Path | None = None) -> tuple[Path, str]:
    """Create byte-identical ZIPs for byte-identical allowlisted source files."""
    output = output or root / "dist" / PACKAGE_NAME
    source = {name: _source_bytes(root, name) for name in MEMBERS}
    if source["requirements-public.lock"] != _source_bytes(root, "requirements.txt"):
        raise PackageError("public runtime lock differs from local requirements")
    manifest = {
        "schema": SCHEMA,
        "members": [
            {"path": name, "size": len(source[name]), "sha256": _sha256(source[name])}
            for name in MEMBERS
        ],
    }
    source[MANIFEST_NAME] = _json_bytes(manifest)
    if sum(map(len, source.values())) > MAX_PACKAGE_BYTES:
        raise PackageError("package exceeds the size limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for name in sorted(source):
            archive.writestr(_zip_info(name), source[name])
    digest = _sha256(output.read_bytes())
    output.with_suffix(".sha256").write_text(f"{digest}  {output.name}\n", encoding="ascii")
    verify_package(output)
    return output, digest


def verify_package(path: Path) -> dict:
    """Verify exact member names, content hashes, sizes and regular-file types."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if names != sorted((*MEMBERS, MANIFEST_NAME)):
            raise PackageError("package member list differs from the public allowlist")
        if len(names) != len(set(names)):
            raise PackageError("duplicate package member")
        for info in infos:
            if (info.is_dir() or info.compress_type != zipfile.ZIP_STORED
                    or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
                    or info.file_size > MAX_MEMBER_BYTES or info.flag_bits & 1):
                raise PackageError("unsafe package member")
        if sum(info.file_size for info in infos) > MAX_PACKAGE_BYTES:
            raise PackageError("package exceeds the size limit")
        manifest = json.loads(archive.read(MANIFEST_NAME))
        expected = {
            "schema": SCHEMA,
            "members": [
                {"path": name, "size": len(payload := archive.read(name)),
                 "sha256": _sha256(payload)}
                for name in MEMBERS
            ],
        }
        if manifest != expected:
            raise PackageError("package manifest or content hash mismatch")
        return manifest


def verify_root(root: Path = ROOT) -> dict:
    """Fail deployment builds from the full review repository or changed ZIP imports."""
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise PackageError("sanitized public package manifest is required")
    for forbidden in FORBIDDEN_PATHS:
        if (root / forbidden).exists() or (root / forbidden).is_symlink():
            raise PackageError(f"forbidden public project path: {forbidden}")
    expected = {
        "schema": SCHEMA,
        "members": [
            {"path": name, "size": len(payload := _source_bytes(root, name)),
             "sha256": _sha256(payload)}
            for name in MEMBERS
        ],
    }
    if manifest_path.read_bytes() != _json_bytes(expected):
        raise PackageError("public project manifest or source hash mismatch")
    return expected


def extract_package(path: Path, destination: Path) -> None:
    """Extract only a verified ZIP into a new project directory."""
    verify_package(path)
    if destination.exists():
        raise PackageError("destination must not exist")
    destination.mkdir(parents=True)
    with zipfile.ZipFile(path) as archive:
        for name in sorted((*MEMBERS, MANIFEST_NAME)):
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    verify_root(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify", "list", "extract", "verify-root"))
    parser.add_argument("--package", type=Path, default=ROOT / "dist" / PACKAGE_NAME)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "build":
            package, digest = build_package(output=args.package)
            print(f"{package}: sha256={digest}")
        elif args.action == "verify-root":
            verify_root()
            print("sanitized public project root verified")
        elif args.action == "extract":
            if args.destination is None:
                parser.error("--destination is required for extract")
            extract_package(args.package, args.destination)
            print(f"extracted and verified: {args.destination}")
        else:
            manifest = verify_package(args.package)
            if args.action == "list":
                for member in manifest["members"]:
                    print(f'{member["sha256"]}  {member["size"]:>8}  {member["path"]}')
                print(f'{_sha256(args.package.read_bytes())}  {args.package.name}')
            else:
                print(f'package verified: sha256={_sha256(args.package.read_bytes())}')
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"public package check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
