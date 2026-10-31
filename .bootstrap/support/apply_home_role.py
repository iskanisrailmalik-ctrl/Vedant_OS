#!/usr/bin/env python3
"""Make Verdant OS a user-selectable Android HOME launcher with an in-launcher setup action."""
from __future__ import annotations
import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"HOME-role patch could not find expected source anchor: {label}")
    return text.replace(old, new, 1)


def main(project: Path) -> None:
    project = project.resolve()
    root = project / "app/src/main/java/com/verdant/os/VerdantAppRoot.kt"
    home = project / "feature/home/src/main/java/com/verdant/os/feature/home/HomeScreen.kt"
    manifest = project / "app/src/main/AndroidManifest.xml"

    root_text = root.read_text(encoding="utf-8")
    root_text = replace_once(
        root_text,
        "import android.app.WallpaperManager\n",
        "import android.app.WallpaperManager\nimport android.app.role.RoleManager\n",
        "RoleManager import",
    )
    root_text = replace_once(
        root_text,
        "import androidx.compose.runtime.*\n",
        "import androidx.compose.runtime.*\n"
        "import androidx.lifecycle.Lifecycle\n"
        "import androidx.lifecycle.LifecycleEventObserver\n"
        "import androidx.lifecycle.compose.LocalLifecycleOwner\n",
        "launcher lifecycle imports",
    )
    root_text = replace_once(
        root_text,
        "import androidx.compose.animation.AnimatedContent\n",
        "import androidx.activity.compose.BackHandler\n"
        "import androidx.activity.compose.rememberLauncherForActivityResult\n"
        "import androidx.activity.result.contract.ActivityResultContracts\n"
        "import androidx.compose.animation.AnimatedContent\n",
        "activity-result imports",
    )
    root_text = replace_once(
        root_text,
        "    fun VerdantAppRoot() {",
        "    fun VerdantAppRoot(homeIntentToken: Int = 0) {",
        "Home-intent reset token parameter",
    )
    root_text = replace_once(
        root_text,
        "    val snackbar = remember { SnackbarHostState() }\n",
        "    val snackbar = remember { SnackbarHostState() }\n"
        "    val roleManager = remember(context) { context.getSystemService(RoleManager::class.java) }\n"
        "    var isDefaultHome by remember(roleManager) {\n"
        "        mutableStateOf(roleManager?.isRoleHeld(RoleManager.ROLE_HOME) == true)\n"
        "    }\n",
        "HOME role state",
    )
    root_text = replace_once(
        root_text,
        "    var destination by remember { mutableStateOf(Destination.HOME) }\n",
        "    var destination by remember { mutableStateOf(Destination.HOME) }\n"
        "    LaunchedEffect(homeIntentToken) {\n"
        "        if (homeIntentToken > 0) destination = Destination.HOME\n"
        "    }\n",
        "return to home when Android invokes the HOME activity",
    )
    root_text = replace_once(
        root_text,
        '    var localEventLog by remember { mutableStateOf("No recorded runtime errors.") }\n',
        '    var localEventLog by remember { mutableStateOf("No recorded runtime errors.") }\n'
        '    val lifecycleOwner = LocalLifecycleOwner.current\n',
        "launcher lifecycle owner",
    )
    role_actions = '''    val homeRoleRequest = rememberLauncherForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        isDefaultHome = roleManager?.isRoleHeld(RoleManager.ROLE_HOME) == true
        report(
            if (isDefaultHome) "Verdant OS is now your default Home launcher."
            else "Verdant OS was not selected as your Home launcher."
        )
    }
    fun requestDefaultHome() {
        val manager = roleManager
        if (manager == null || !manager.isRoleAvailable(RoleManager.ROLE_HOME)) {
            runCatching { context.startActivity(Intent(Settings.ACTION_HOME_SETTINGS)) }
                .onFailure {
                    report("Open Android Settings → Apps → Default apps → Home app and choose Verdant OS Launcher.")
                }
        } else if (manager.isRoleHeld(RoleManager.ROLE_HOME)) {
            isDefaultHome = true
            report("Verdant OS is already your default Home launcher.")
        } else {
            homeRoleRequest.launch(manager.createRequestRoleIntent(RoleManager.ROLE_HOME))
        }
    }
'''
    root_text = replace_once(
        root_text,
        "    fun report(message: String) { scope.launch { snackbar.showSnackbar(message, withDismissAction=true) } }\n",
        "    fun report(message: String) { scope.launch { snackbar.showSnackbar(message, withDismissAction=true) } }\n" + role_actions,
        "HOME role request action",
    )
    root_text = replace_once(
        root_text,
        "highContrast=settings.highContrast,\n                            onLaunch={ target -> launchApp(context, target, ::report, app) },",
        "highContrast=settings.highContrast, isDefaultHome=isDefaultHome,\n"
        "                            onLaunch={ target -> launchApp(context, target, ::report, app) },\n"
        "                            onSetAsDefault={ requestDefaultHome() },",
        "HomeScreen HOME-role arguments",
    )
    lifecycle_and_back = '''    DisposableEffect(lifecycleOwner, roleManager) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                isDefaultHome = roleManager?.isRoleHeld(RoleManager.ROLE_HOME) == true
                scope.launch { reloadApps() }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    BackHandler(enabled = destination != Destination.HOME) {
        destination = when (destination) {
            Destination.DIAGNOSTICS -> Destination.SETTINGS
            Destination.HOME -> Destination.HOME
            else -> Destination.HOME
        }
    }
'''
    root_text = replace_once(
        root_text,
        "    LaunchedEffect(Unit) { reloadApps() }",
        lifecycle_and_back,
        "refresh app list and launcher navigation on resume",
    )
    root.write_text(root_text, encoding="utf-8")

    main_activity = project / "app/src/main/java/com/verdant/os/MainActivity.kt"
    main_activity_text = """package com.verdant.os

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.mutableIntStateOf
import androidx.core.view.WindowCompat
import com.verdant.os.core.design.VerdantTheme

class MainActivity : ComponentActivity() {
    private val homeIntentToken = mutableIntStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent {
            val token = homeIntentToken.intValue
            VerdantTheme { VerdantAppRoot(homeIntentToken = token) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        homeIntentToken.intValue++
    }
}
"""
    main_activity.write_text(main_activity_text, encoding="utf-8")

    home_text = home.read_text(encoding="utf-8")
    home_text = replace_once(
        home_text,
        "import androidx.compose.foundation.layout.*\n",
        "import androidx.compose.foundation.layout.*\n"
        "import androidx.compose.foundation.gestures.detectVerticalDragGestures\n"
        "import androidx.compose.ui.input.pointer.pointerInput\n",
        "launcher swipe gesture imports",
    )
    home_text = replace_once(
        home_text,
        "    highContrast: Boolean,\n    onLaunch:",
        "    highContrast: Boolean,\n    isDefaultHome: Boolean,\n    onSetAsDefault: () -> Unit,\n    onLaunch:",
        "HomeScreen HOME-role parameters",
    )
    home_text = replace_once(
        home_text,
        '            MiniStatusPill("LOCAL GARDEN")',
        '''            if (isDefaultHome) {
                    MiniStatusPill("DEFAULT HOME")
                } else {
                    androidx.compose.material3.TextButton(onClick=onSetAsDefault) {
                        Text("SET AS HOME", color=VerdantColors.NewGrowth, fontSize=10.sp)
                    }
                }''',
        "default-home status/action",
    )
    home_text = replace_once(
        home_text,
        "    Box(Modifier.fillMaxSize()) {\n",
        """    Box(
        Modifier.fillMaxSize().pointerInput(onOpenDrawer, onOpenShade) {
            var totalDrag = 0f
            detectVerticalDragGestures(
                onDragStart = { totalDrag = 0f },
                onVerticalDrag = { _, amount -> totalDrag += amount },
                onDragEnd = {
                    when {
                        totalDrag < -72f -> onOpenDrawer()
                        totalDrag > 96f -> onOpenShade()
                    }
                },
            )
        },
    ) {
""",
        "swipe-up drawer and swipe-down shade gestures",
    )
    home.write_text(home_text, encoding="utf-8")

    manifest_text = manifest.read_text(encoding="utf-8")
    required = ("android.intent.category.HOME", "android.intent.category.DEFAULT")
    for value in required:
        if value not in manifest_text:
            raise SystemExit(f"AndroidManifest.xml is missing required launcher category: {value}")
    manifest_text = manifest_text.replace(
        'android:label="Verdant OS"', 'android:label="Verdant OS Launcher"', 1
    )
    if 'android:launchMode="singleTask"' not in manifest_text:
        activity_anchor = 'android:name=".MainActivity" android:exported="true"'
        if activity_anchor not in manifest_text:
            raise SystemExit("AndroidManifest.xml lacks the MainActivity launcher declaration.")
        manifest_text = manifest_text.replace(
            activity_anchor,
            activity_anchor + ' android:launchMode="singleTask"',
            1,
        )
    manifest.write_text(manifest_text, encoding="utf-8")

    readme = project / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        note = (
            "\n\n## Set Verdant OS as your Android Home launcher\n\n"
            "Open Verdant OS and tap **SET AS HOME** in the top bar. Android will show its "
            "system Home-role chooser; select Verdant OS Launcher and confirm. After that, "
            "pressing the device Home gesture/button returns to Verdant OS. Android still "
            "installs third-party launchers as APK packages; this project replaces the "
            "Home experience, not the phone firmware or protected system UI.\n"
        )
        if "## Set Verdant OS as your Android Home launcher" not in text:
            readme.write_text(text + note, encoding="utf-8")

    print("Applied Android HOME-role registration and in-launcher default-Home setup action.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_home_role.py PROJECT_DIR")
    main(Path(sys.argv[1]))
