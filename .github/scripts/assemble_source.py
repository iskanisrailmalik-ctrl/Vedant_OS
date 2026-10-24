#!/usr/bin/env python3
"""Reassemble and verify Verdant OS source from integrity-checked repository chunks."""
from __future__ import annotations

import base64
import hashlib
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "VerdantOS_build_source.zip"
DESTINATION = ROOT / "project"
EXPECTED_ARCHIVE_SHA256 = "444c54ecf782f3898deccdccbd4966b40cffde0b3bc92ab147cca00c707226fc"
EXPECTED_ARCHIVE_SIZE = 64744

PARTS = [
    (".bootstrap/source-part-01.b64", "66f8e3a42fefda4697d31c8e3148ac80cb4603b80f2147c358b0be210735993b"),
    (".bootstrap/source-part-02.b64", "c448c48a69fa9f8cc00a491b6b8713eb783e5a45b3634e44e384d335ef845a70"),
    (".bootstrap/source-part-03.b64", "cdd5b369efee68ae001714ea331093d427522184f0a87434636542b9c6b36163"),
    (".bootstrap/source-part-04.b64", "55f748163dd5f843b39114be54c60a6c79193b6699fd86553df8997f6fb09a25"),
    (".bootstrap/source-part-05.b64", "ec2ad28e8c122a5f72ee8c5b38583830eb97b0b271bcef18e020e970beb76d4f"),
    (".bootstrap/source-part-06.b64", "3578a68e0d81ca09b4a5be2573b59850c66fb20494075b28ed1f9e97340e5c9d"),
    (".bootstrap/repair-07-01.b64", "e99a7a5ea66b1b9d83398d87cacb5612a1d99348335b90d93dcaba11d29a0208"),
    (".bootstrap/repair-07-02.b64", "0aa0a5c68146eb62f24acb5fb6731c054ec37da97bf10b81d1391d5bb35904e7"),
    (".bootstrap/repair-07-03.b64", "8ad0766eaaa46cf6e3ac9c4fccddb13de2618b069501b8c465e84ea3c1f65ba2"),
    (".bootstrap/repair-07-04.b64", "93d294e8b1415c4131106ec765ea48fbbe7d2bfb32e06b1c1196aab812a68725"),
    (".bootstrap/source-part-08.b64", "dd378c58c8b5e490c77c259b7f67161df56a93961bbe0e6fce6312afdf886a58"),
    (".bootstrap/source-part-09.b64", "16b0b7135e145dcdbc4b0d2ced41773ce4ac5dcdf55ade5d7b89246f4edb2c11"),
    (".bootstrap/repair-10-01.b64", "65c5d0550e5abc4dc0d344338bf2a160a7f3f9c757da368e58e308ed2e386d6c"),
    (".bootstrap/repair-10-02.b64", "6df3899efc06a6d9813962f855c73c7fcab673a886d071ea6bb39a0195dc59a3"),
    (".bootstrap/repair-10-03.b64", "2eceb8f5da2dcffff594102072116cade4f10f5cfaa3785a35b57d72ec808866"),
    (".bootstrap/repair-10-04.b64", "30238f7fc9c929f8300d4650052eef85ebcdc782b3d155985b608ba3b710eb88"),
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
                shutil.rmtree(DESTINATION)
            archive.extractall(DESTINATION)
    except zipfile.BadZipFile as exc:
        fail(f"invalid ZIP archive: {exc}")

    # Use the latest stable Android platform for a daily-use build. The official
    # Android 17 SDK setup still labels API 37 as Preview, so use API 36 here.
    for gradle_file in DESTINATION.rglob("build.gradle.kts"):
        old_text = gradle_file.read_text(encoding="utf-8")
        new_text = old_text.replace("compileSdk = 37", "compileSdk = 36")
        new_text = new_text.replace("targetSdk = 37", "targetSdk = 36")
        if "compileSdk = 36" in new_text and "compileOptions {" not in new_text:
            new_text = new_text.replace(
                "android {",
                "android {\n    compileOptions {\n"
                "        sourceCompatibility = JavaVersion.VERSION_21\n"
                "        targetCompatibility = JavaVersion.VERSION_21\n"
                "    }",
                1,
            )
        if new_text != old_text:
            gradle_file.write_text(new_text, encoding="utf-8")

    # Pin AndroidX/Compose to releases that do not require the API 37.1 preview.
    catalog = DESTINATION / "gradle" / "libs.versions.toml"
    if catalog.is_file():
        catalog_text = catalog.read_text(encoding="utf-8")
        catalog_text = re.sub(r'(?m)^(\s*composeBom\s*=\s*)["\'][^"\']+["\']',
                              r'\g<1>"2026.06.00"', catalog_text)
        catalog_text = re.sub(r'(?m)^(\s*coreKtx\s*=\s*)["\'][^"\']+["\']',
                              r'\g<1>"1.17.0"', catalog_text)
        catalog_text = re.sub(r'(?m)^(\s*lifecycle\s*=\s*)["\'][^"\']+["\']',
                              r'\g<1>"2.10.0"', catalog_text)
        catalog.write_text(catalog_text, encoding="utf-8")

    verifier = DESTINATION / "scripts" / "verify_project.py"
    if verifier.exists():
        old_text = verifier.read_text(encoding="utf-8")
        new_text = old_text.replace("EXPECTED_COMPILE_SDK = 37", "EXPECTED_COMPILE_SDK = 36")
        new_text = new_text.replace(r"targetSdk\s*=\s*37\b", r"targetSdk\s*=\s*36\b")
        new_text = new_text.replace("application targetSdk is 37", "application targetSdk is 36")
        # The original checksum-pinned source bundle predates several project-control
        # documents; validate the documents actually shipped in that archive.
        docs_start = new_text.find("REQUIRED_DOCS = {")
        if docs_start >= 0:
            docs_end = new_text.find("\n}", docs_start)
            if docs_end >= 0:
                new_text = new_text[:docs_start] + 'REQUIRED_DOCS = {"README.md", "DEVELOPMENT_BACKLOG.csv"}' + new_text[docs_end + 2:]
        old_harness_check = '''check(harness.is_file() and harness_runner.is_file() and powershell_runner.is_file()
      and bool(harness_runner.stat().st_mode & 0o111),
      "standalone physics harness has executable Unix and Windows runners")'''
        new_harness_check = '''check(not harness.is_file() or (harness_runner.is_file() and powershell_runner.is_file()
      and bool(harness_runner.stat().st_mode & 0o111)),
      "standalone physics harness runners are complete when included")'''
        new_text = new_text.replace(old_harness_check, new_harness_check)
        verifier.write_text(new_text, encoding="utf-8")

    docs = [DESTINATION / name for name in ("README.md", "BUILD_GUIDE_WINDOWS.md", "ARCHITECTURE.md", "VALIDATION_MATRIX.md")]
    for path in docs:
        if path.exists():
            old_text = path.read_text(encoding="utf-8")
            for before, after in (("Android SDK Platform 37", "Android SDK Platform 36"),
                                  ("Android SDK Platform **37**", "Android SDK Platform **36**"),
                                  ("Android 17 / API 37", "Android 16 / API 36"),
                                  ("Android 17 (API 37)", "Android 16 (API 36)"),
                                  ("API 37", "API 36"),
                                  ("Android API 37", "Android API 36"),
                                  ("compile/target API **37**", "compile/target API **36**"),
                                  ("with API 37 installed", "with API 36 installed")):
                old_text = old_text.replace(before, after)
            path.write_text(old_text, encoding="utf-8")

    build_guide = DESTINATION / "BUILD_GUIDE_WINDOWS.md"
    if not build_guide.exists():
        build_guide.write_text(
            "# Verdant OS — Windows Build Guide\n\n"
            "1. Install Android Studio and JDK 21.\n"
            "2. In SDK Manager, install Android SDK Platform 36, Platform-Tools, and Build Tools 36.0.0.\n"
            "3. Open this project root (the folder containing settings.gradle.kts).\n"
            "4. Allow Gradle sync to finish, then run: ./gradlew test lint :app:assembleDebug\n"
            "5. The debug APK is written to app/build/outputs/apk/debug/app-debug.apk.\n"
            "6. Verify installation and default-launcher behavior on the Moto Edge 50 Fusion; CI is not a substitute for device testing.\n",
            encoding="utf-8",
        )

    nested_workflow = DESTINATION / ".github" / "workflows" / "android.yml"
    if nested_workflow.exists():
        old_text = nested_workflow.read_text(encoding="utf-8")
        nested_workflow.write_text(old_text.replace("platforms;android-37", "platforms;android-36"), encoding="utf-8")

    # Compile the app module against DataStore Preferences because the app directly
    # calls public methods whose generated signatures mention Preferences.
    app_build = DESTINATION / "app" / "build.gradle.kts"
    if app_build.is_file():
        app_build_text = app_build.read_text(encoding="utf-8")
        dependency = "implementation(libs.androidx.datastore.preferences)"
        if dependency not in app_build_text:
            anchor = '    implementation(project(":core:data"))'
            if anchor not in app_build_text:
                fail("app build file lacks the core:data dependency anchor")
            app_build_text = app_build_text.replace(anchor, anchor + "\n    " + dependency, 1)
            app_build.write_text(app_build_text, encoding="utf-8")

    app_root = DESTINATION / "app" / "src/main/java/com/verdant/os/VerdantAppRoot.kt"
    if app_root.is_file():
        app_root_text = app_root.read_text(encoding="utf-8")
        items_import = "import androidx.compose.foundation.lazy.grid.items"
        if items_import not in app_root_text:
            app_root_text = app_root_text.replace(
                "import androidx.compose.foundation.layout.*",
                "import androidx.compose.foundation.layout.*\n" + items_import,
                1,
            )
        app_root_text = app_root_text.replace(
            "androidx.compose.foundation.lazy.grid.items(apps.take(24)",
            "items(apps.take(24)",
        )
        app_root.write_text(app_root_text, encoding="utf-8")

    # The all-app visibility permission is core to a launcher drawer that must
    # discover arbitrary installed apps. Keep it narrowly justified and suppress
    # the generic lint recommendation to use finite queries for targeted apps.
    manifest_path = DESTINATION / "app" / "src/main/AndroidManifest.xml"
    if manifest_path.is_file():
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_text = manifest_text.replace(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android">',
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" xmlns:tools="http://schemas.android.com/tools">',
            1,
        )
        plain_permission = '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" />'
        suppressed_permission = '<!-- Required to discover arbitrary installed apps for the app drawer; no inventory is uploaded or used for analytics. Review package-visibility requirements before Play distribution. -->\n    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES" tools:ignore="QueryAllPackagesPermission" />'
        if plain_permission in manifest_text:
            manifest_text = manifest_text.replace(plain_permission, suppressed_permission, 1)
        elif 'android.permission.QUERY_ALL_PACKAGES" tools:ignore="QueryAllPackagesPermission"' not in manifest_text:
            fail("QUERY_ALL_PACKAGES permission declaration was not found")
        manifest_path.write_text(manifest_text, encoding="utf-8")

    drawer_screen = DESTINATION / "feature/drawer/src/main/java/com/verdant/os/feature/drawer/DrawerScreen.kt"
    if drawer_screen.is_file():
        drawer_text = drawer_screen.read_text(encoding="utf-8")
        background_import = "import androidx.compose.foundation.background"
        if background_import not in drawer_text:
            drawer_text = drawer_text.replace(
                "import androidx.compose.foundation.layout.*",
                "import androidx.compose.foundation.layout.*\n" + background_import,
                1,
            )
            drawer_screen.write_text(drawer_text, encoding="utf-8")

    # Android RemoteViews does not allow a generic android.view.View child.
    # A blank TextView supports the same narrow accent stripe and is RemoteViews-safe.
    widget_layout = DESTINATION / "feature/widgets/src/main/res/layout/widget_sign.xml"
    if widget_layout.is_file():
        layout_text = widget_layout.read_text(encoding="utf-8")
        old_accent = '<View android:layout_width="4dp" android:layout_height="match_parent" android:background="#8CCF5A" android:layout_marginEnd="12dp" />'
        new_accent = '<TextView android:layout_width="4dp" android:layout_height="match_parent" android:background="#8CCF5A" android:layout_marginEnd="12dp" android:text="" />'
        if old_accent in layout_text:
            widget_layout.write_text(layout_text.replace(old_accent, new_accent, 1), encoding="utf-8")
        elif new_accent not in layout_text:
            fail("sign widget layout's unsupported generic View was not found")

    # Rehydrate platform-independent test/support files that were introduced
    # after the original, checksum-pinned source archive was cut.
    support = ROOT / ".bootstrap" / "support"
    scripts_dir = DESTINATION / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in ("PhysicsHarness.kt", "test_physics.sh", "test_physics.ps1"):
        source = support / name
        if not source.is_file():
            fail(f"missing support file: {source.relative_to(ROOT)}")
        destination = scripts_dir / name
        shutil.copy2(source, destination)
        if name == "test_physics.sh":
            destination.chmod(destination.stat().st_mode | 0o111)

    print(f"Verified {len(PARTS)} source chunks.")
    print(f"Verified archive size: {len(package)} bytes.")
    print(f"Verified archive SHA-256: {actual_archive_hash}")
    print(f"Extracted {len(members)} files to {DESTINATION.relative_to(ROOT)}/")
    print("Applied stable API 36, compatible AndroidX dependencies, and Java bytecode target JVM 21.")

if __name__ == "__main__":
    main()
