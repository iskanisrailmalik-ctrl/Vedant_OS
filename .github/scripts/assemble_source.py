#!/usr/bin/env python3
"""Reassemble and verify the Verdant OS source package from staged text chunks."""
from __future__ import annotations

import base64
import hashlib
import re
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / ".bootstrap"
OUTPUT = ROOT / "VerdantOS_build_source.zip"
DESTINATION = ROOT / "project"
EXPECTED_ARCHIVE_SHA256 = "444c54ecf782f3898deccdccbd4966b40cffde0b3bc92ab147cca00c707226fc"
EXPECTED_ARCHIVE_SIZE = 64744

# Expected hashes are generated from the local source package before transport.
PARTS = [
    (".bootstrap/source-part-01.b64", "66f8e3a42fefda4697d31c8e3148ac80cb4603b80f2147c358b0be210735993b"),
    (".bootstrap/source-part-02.b64", "c448c48a69fa9f8cc00a491b6b8713eb783e5a45b3634e44e384d335ef845a70"),
    (".bootstrap/source-part-03.b64", "cdd5b369efee68ae001714ea331093d427522184f0a87434636542b9c6b36163"),
    (".bootstrap/source-part-04.b64", "55f748163dd5f843b39114be54c60a6c79193b6699fd86553df8997f6fb09a25"),
    (".bootstrap/source-part-05.b64", "ec2ad28e8c122a5f72ee8c5b38583830eb97b0b271bcef18e020e970beb76d4f"),
    (".bootstrap/source-part-06.b64", "3578a68e0d81ca09b4a5be2573b59850c66fb20494075b28ed1f9e97340e5c9d"),
    (".bootstrap/source-part-07.b64", "15fc1cbfed072821dd090b64c819a19e10f81d4432b7f9947789f399af2c8416"),
    (".bootstrap/source-part-07-tail.b64", "648d61e48c721bd04c2712f8a8cddde51a9ec451722fd6e614745233492c8dbe"),
    (".bootstrap/source-part-08.b64", "dd378c58c8b5e490c77c259b7f67161df56a93961bbe0e6fce6312afdf886a58"),
    (".bootstrap/source-part-09.b64", "16b0b7135e145dcdbc4b0d2ced41773ce4ac5dcdf55ade5d7b89246f4edb2c11"),
    (".bootstrap/source-part-10a.b64", "4e5c7f6006b55f60b7ee43531f9491e5f2fd8561bac43dbfe4f2cb65b02372f9"),
    (".bootstrap/source-part-10b.b64", "9ae5bf7e4c6c5326a6c67819fc0334313b71c4a000bf6f095496dabeb89954ab"),
    (".bootstrap/source-part-11.b64", "2f47afc1968e425192f95f61b604a58fec57264a748215d61773f0e220951a87"),
    (".bootstrap/source-part-12.b64", "51ef77a6fd746611f0a50a7ace12c2951c17c496602ee6fc4c1a6d0a8405e17d"),
]

def fail(message: str) -> None:
    raise SystemExit(f"BOOTSTRAP ERROR: {message}")

def main() -> None:
    chunks: list[str] = []
    for relative, expected_hash in PARTS:
        path = ROOT / relative
        if not path.is_file():
            fail(f"missing chunk: {relative}")
        raw = path.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != expected_hash:
            fail(f"checksum mismatch for {relative}: expected {expected_hash}, got {actual_hash}")
        try:
            chunk = raw.decode("ascii")
        except UnicodeDecodeError:
            fail(f"non-ASCII data in {relative}")
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", chunk):
            fail(f"invalid base64 characters in {relative}")
        chunks.append(chunk)

    try:
        package = base64.b64decode("".join(chunks), validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        fail(f"cannot decode base64: {exc}")

    if len(package) != EXPECTED_ARCHIVE_SIZE:
        fail(f"archive size mismatch: expected {EXPECTED_ARCHIVE_SIZE}, got {len(package)}")
    actual_archive_hash = hashlib.sha256(package).hexdigest()
    if actual_archive_hash != EXPECTED_ARCHIVE_SHA256:
        fail(f"archive checksum mismatch: expected {EXPECTED_ARCHIVE_SHA256}, got {actual_archive_hash}")

    OUTPUT.write_bytes(package)
    try:
        with zipfile.ZipFile(OUTPUT) as archive:
            bad_member = archive.testzip()
            if bad_member:
                fail(f"damaged ZIP member: {bad_member}")
            members = archive.infolist()
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    fail(f"unsafe archive member path: {member.filename}")
            if not any(m.filename.endswith("settings.gradle.kts") for m in members):
                fail("archive lacks settings.gradle.kts")
            if not any(m.filename.endswith("gradlew") for m in members):
                fail("archive lacks the Gradle wrapper")
            if DESTINATION.exists():
                import shutil
                shutil.rmtree(DESTINATION)
            archive.extractall(DESTINATION)
    except zipfile.BadZipFile as exc:
        fail(f"invalid ZIP archive: {exc}")

    print(f"Verified {len(PARTS)} source chunks.")
    print(f"Verified archive SHA-256: {actual_archive_hash}")
    print(f"Extracted {len(members)} files to {DESTINATION.relative_to(ROOT)}/")

if __name__ == "__main__":
    main()
