#!/usr/bin/env python3
"""Apply Phase 1 performance safeguards to the reconstructed Verdant OS source."""
from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Performance patch could not find expected source anchor: {label}")
    return text.replace(old, new, 1)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def patch_preferences(project: Path) -> None:
    path = project / "core/data/src/main/java/com/verdant/os/core/data/VerdantPreferences.kt"
    source = path.read_text(encoding="utf-8")
    updated = source.replace("val windLevel: Int = 1,", "val windLevel: Int = 0,")
    updated = updated.replace("windLevel = (pref[Keys.WindLevel] ?: 1).coerceIn(0, 2),",
                              "windLevel = (pref[Keys.WindLevel] ?: 0).coerceIn(0, 2),")
    if "val windLevel: Int = 0," not in updated or "pref[Keys.WindLevel] ?: 0" not in updated:
        raise SystemExit("Performance patch could not set the default wallpaper motion to Calm.")
    path.write_text(updated, encoding="utf-8")


def patch_repository(project: Path) -> None:
    path = project / "core/data/src/main/java/com/verdant/os/core/data/LauncherRepository.kt"
    source = path.read_text(encoding="utf-8")
    source = replace_once(source, "import android.os.Process\n",
                          "import android.os.Process\nimport android.os.SystemClock\n",
                          "repository SystemClock import")
    source = replace_once(source, "import kotlinx.coroutines.withContext\n",
                          "import kotlinx.coroutines.withContext\nimport kotlinx.coroutines.sync.Mutex\nimport kotlinx.coroutines.sync.withLock\n",
                          "repository Mutex imports")
    start = source.find("object LauncherRepository {")
    if start < 0:
        raise SystemExit("LauncherRepository object declaration not found.")
    launch_start = source.find("    fun launch(context:", start)
    if launch_start < 0:
        raise SystemExit("LauncherRepository.launch declaration not found.")
    prefix = source[:start]
    launch_body = source[launch_start:]
    repository_head = r'''
object LauncherRepository {
    private const val CACHE_TTL_MS = 20_000L
    private val cacheMutex = Mutex()

    @Volatile
    private var cachedApps: List<LaunchableApp>? = null

    @Volatile
    private var cacheUpdatedAt: Long = 0L

    /** Reuses the recent app scan on Home re-entry; package queries stay off the UI thread. */
    suspend fun loadApps(
        context: Context,
        forceRefresh: Boolean = false,
    ): AppResult<List<LaunchableApp>> = withContext(Dispatchers.IO) {
        val now = SystemClock.elapsedRealtime()
        val current = cachedApps
        if (!forceRefresh && current != null && now - cacheUpdatedAt < CACHE_TTL_MS) {
            return@withContext AppResult.Success(current)
        }

        cacheMutex.withLock {
            val lockedNow = SystemClock.elapsedRealtime()
            val latest = cachedApps
            if (!forceRefresh && latest != null && lockedNow - cacheUpdatedAt < CACHE_TTL_MS) {
                return@withLock AppResult.Success(latest)
            }

            try {
                val launcherApps = context.getSystemService(LauncherApps::class.java)
                val discovered = if (launcherApps != null) {
                    launcherApps.getActivityList(null, Process.myUserHandle()).map { info ->
                        LaunchableApp(
                            info.label?.toString()?.ifBlank { info.name } ?: info.name,
                            info.applicationInfo.packageName,
                            info.componentName.className,
                        )
                    }
                } else {
                    val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
                    context.packageManager.queryIntentActivities(intent, 0).map { info ->
                        LaunchableApp(
                            info.loadLabel(context.packageManager).toString(),
                            info.activityInfo.packageName,
                            info.activityInfo.name,
                        )
                    }
                }
                val result = discovered.distinctBy { it.stableId }
                    .sortedBy { it.title.lowercase() }
                cachedApps = result
                cacheUpdatedAt = SystemClock.elapsedRealtime()
                AppResult.Success(result)
            } catch (error: SecurityException) {
                cachedApps?.let { AppResult.Success(it) } ?: AppResult.Failure(
                    ErrorCode.PERMISSION_DENIED,
                    "Android did not allow the app list to be read.",
                    "Open app settings and allow app discovery, or keep using the safe grid.",
                )
            } catch (error: RuntimeException) {
                cachedApps?.let { AppResult.Success(it) } ?: AppResult.Failure(
                    ErrorCode.UNKNOWN,
                    "The app list could not be loaded.",
                    "Reopen Verdant. Your saved settings remain on this device.",
                )
            }
        }
    }

    /** Invalidates cached package metadata after a failed launch. */
    fun invalidateCache() {
        cachedApps = null
        cacheUpdatedAt = 0L
    }

'''
    source = prefix + repository_head + launch_body
    source = source.replace(
        "        } catch (error: ActivityNotFoundException) {\n            AppResult.Failure(",
        "        } catch (error: ActivityNotFoundException) {\n            invalidateCache()\n            AppResult.Failure(",
        1,
    )
    path.write_text(source, encoding="utf-8")


def patch_app_root(project: Path) -> None:
    path = project / "app/src/main/java/com/verdant/os/VerdantAppRoot.kt"
    source = path.read_text(encoding="utf-8")
    source = replace_once(source, "    suspend fun reloadApps() {\n",
                          "    suspend fun reloadApps(forceRefresh: Boolean = false) {\n",
                          "reloadApps force-refresh parameter")
    source = replace_once(source, "when (val result = LauncherRepository.loadApps(context)) {",
                          "when (val result = LauncherRepository.loadApps(context, forceRefresh)) {",
                          "loadApps force-refresh argument")
    source = replace_once(source, "onRetry={scope.launch { reloadApps(); report(",
                          "onRetry={scope.launch { reloadApps(forceRefresh=true); report(",
                          "drawer explicit refresh")
    path.write_text(source, encoding="utf-8")


def patch_drawer_search(project: Path) -> None:
    path = project / "feature/drawer/src/main/java/com/verdant/os/feature/drawer/DrawerScreen.kt"
    source = path.read_text(encoding="utf-8")
    source = replace_once(
        source,
        "    val filtered = remember(apps, query) { apps.filter { it.title.contains(query.trim(), ignoreCase=true) }.sortedBy { it.title.lowercase() } }",
        "    val normalizedQuery = query.trim()\n"
        "    val filtered = remember(apps, normalizedQuery) {\n"
        "        if (normalizedQuery.isBlank()) apps else apps.filter { it.title.contains(normalizedQuery, ignoreCase=true) }\n"
        "    }",
        "avoid sorting the full app list on every search keystroke",
    )
    path.write_text(source, encoding="utf-8")


def write_icon_component(project: Path) -> None:
    path = project / "core/design/src/main/java/com/verdant/os/core/design/LauncherAppIcon.kt"
    source = r'''
package com.verdant.os.core.design

import android.content.ComponentName
import android.content.Context
import android.graphics.Bitmap
import android.graphics.drawable.Drawable
import android.util.LruCache
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.graphics.drawable.toBitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Bounded memory cache; PackageManager calls and drawable decoding never run in composition. */
private object LauncherIconCache {
    private const val MAX_CACHE_KB = 4 * 1024
    private const val ICON_SIZE_PX = 128

    private val bitmaps = object : LruCache<String, Bitmap>(MAX_CACHE_KB) {
        override fun sizeOf(key: String, value: Bitmap): Int =
            (value.allocationByteCount / 1024).coerceAtLeast(1)
    }

    suspend fun load(context: Context, packageName: String, activityName: String): ImageBitmap? =
        withContext(Dispatchers.IO) {
            val key = "$packageName/$activityName"
            bitmaps.get(key)?.let { return@withContext it.asImageBitmap() }

            val packageManager = context.packageManager
            val drawable: Drawable = runCatching {
                packageManager.getActivityIcon(ComponentName(packageName, activityName))
            }.recoverCatching {
                packageManager.getApplicationIcon(packageName)
            }.getOrElse {
                packageManager.defaultActivityIcon
            }

            runCatching {
                drawable.toBitmap(ICON_SIZE_PX, ICON_SIZE_PX, Bitmap.Config.ARGB_8888)
            }.getOrNull()?.let { bitmap ->
                bitmaps.put(key, bitmap)
                bitmap.asImageBitmap()
            }
        }
}

@Composable
fun LauncherAppIcon(
    title: String,
    packageName: String,
    activityName: String,
    badgeCount: Int = 0,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    val context = LocalContext.current.applicationContext
    val icon = produceState<ImageBitmap?>(
        initialValue = null,
        key1 = packageName,
        key2 = activityName,
    ) {
        value = LauncherIconCache.load(context, packageName, activityName)
    }.value

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(5.dp),
    ) {
        Box(
            modifier = Modifier
                .size(60.dp)
                .clip(RoundedCornerShape(18.dp))
                .background(Color(0x4D10251B)),
            contentAlignment = Alignment.Center,
        ) {
            if (icon != null) {
                Image(
                    bitmap = icon,
                    contentDescription = title,
                    contentScale = ContentScale.Fit,
                    modifier = Modifier.size(48.dp),
                )
            } else {
                Text(
                    text = title.firstOrNull()?.uppercase() ?: "?",
                    color = VerdantColors.TextPrimary,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }
        }
        Text(
            text = title,
            color = VerdantColors.TextPrimary,
            fontSize = 10.sp,
            lineHeight = 12.sp,
            maxLines = 1,
            textAlign = TextAlign.Center,
        )
    }
}
'''
    write(path, source)


def write_wallpaper_service(project: Path) -> None:
    path = project / "engine/render/src/main/java/com/verdant/os/engine/render/VerdantWallpaperService.kt"
    source = r'''
package com.verdant.os.engine.render

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.RectF
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.service.wallpaper.WallpaperService
import android.util.Log
import android.view.MotionEvent
import android.view.SurfaceHolder
import com.verdant.os.core.data.GardenSettings
import com.verdant.os.core.data.VerdantPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.launch
import java.util.Calendar
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sin

/**
 * Static-by-default PNG wallpaper compositor. Animation is opt-in and capped at 20fps.
 * No frame loop runs while the engine is hidden or motion is disabled.
 */
class VerdantWallpaperService : WallpaperService() {
    override fun onCreateEngine(): Engine = GardenEngine()

    private companion object {
        const val TAG = "VerdantWallpaper"
        const val FRAME_INTERVAL_MS = 50L
        const val EXTRA_ZOOM = 1.035f
    }

    private inner class GardenEngine : Engine() {
        private val worker = HandlerThread("VerdantWallpaperRender").apply { start() }
        private val handler = Handler(worker.looper)
        private val paint = Paint(Paint.FILTER_BITMAP_FLAG or Paint.DITHER_FLAG).apply {
            isAntiAlias = false
            isFilterBitmap = true
        }
        private val destination = RectF()
        private val engineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        private val preferences = VerdantPreferences(this@VerdantWallpaperService)

        @Volatile private var visible = false
        @Volatile private var surfaceAvailable = false
        @Volatile private var motionEnabled = false
        @Volatile private var windLevel = 0
        @Volatile private var horizontalOffset = 0f
        @Volatile private var timeMode = "AUTO"

        private var bitmap: Bitmap? = null
        private var frame = 0L
        private var lastOffsetDrawAt = 0L

        private val loop = object : Runnable {
            override fun run() {
                if (!visible || !surfaceAvailable) return
                drawFrame()
                if (motionEnabled && windLevel > 0 && visible && surfaceAvailable) {
                    handler.postDelayed(this, FRAME_INTERVAL_MS)
                }
            }
        }

        init {
            setTouchEventsEnabled(false)
            engineScope.launch {
                preferences.settings.collect { settings: GardenSettings ->
                    motionEnabled = !(settings.reduceMotion || settings.calmMode) && settings.windLevel > 0
                    windLevel = settings.windLevel.coerceIn(0, 2)
                    timeMode = settings.timeMode
                    handler.post {
                        handler.removeCallbacks(loop)
                        if (visible && surfaceAvailable) handler.post(loop)
                    }
                }
            }
        }

        override fun onVisibilityChanged(isVisible: Boolean) {
            visible = isVisible
            handler.removeCallbacks(loop)
            if (visible && surfaceAvailable) handler.post(loop)
        }

        override fun onTouchEvent(event: MotionEvent) {
            super.onTouchEvent(event)
            if (event.actionMasked == MotionEvent.ACTION_UP) requestSingleFrame()
        }

        override fun onOffsetsChanged(
            xOffset: Float,
            yOffset: Float,
            xOffsetStep: Float,
            yOffsetStep: Float,
            xPixelOffset: Int,
            yPixelOffset: Int,
        ) {
            super.onOffsetsChanged(xOffset, yOffset, xOffsetStep, yOffsetStep, xPixelOffset, yPixelOffset)
            val newOffset = xOffset.coerceIn(0f, 1f)
            if (abs(newOffset - horizontalOffset) < 0.005f) return
            horizontalOffset = newOffset
            val now = SystemClock.uptimeMillis()
            if (motionEnabled || now - lastOffsetDrawAt >= 32L) {
                lastOffsetDrawAt = now
                requestSingleFrame()
            }
        }

        override fun onSurfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
            super.onSurfaceChanged(holder, format, width, height)
            surfaceAvailable = true
            handler.removeCallbacks(loop)
            if (visible) handler.post(loop)
        }

        override fun onSurfaceDestroyed(holder: SurfaceHolder) {
            surfaceAvailable = false
            handler.removeCallbacks(loop)
            super.onSurfaceDestroyed(holder)
        }

        override fun onDestroy() {
            visible = false
            surfaceAvailable = false
            handler.removeCallbacksAndMessages(null)
            engineScope.cancel()
            worker.quitSafely()
            bitmap?.recycle()
            bitmap = null
            super.onDestroy()
        }

        private fun requestSingleFrame() {
            handler.removeCallbacks(loop)
            if (visible && surfaceAvailable) handler.post(loop)
        }

        /** Decode on the render thread in RGB_565, halving bitmap memory for this opaque PNG. */
        private fun wallpaperBitmap(): Bitmap? {
            bitmap?.let { if (!it.isRecycled) return it }
            val options = BitmapFactory.Options().apply {
                inPreferredConfig = Bitmap.Config.RGB_565
                inDither = true
                inScaled = false
            }
            val decoded = BitmapFactory.decodeResource(
                resources,
                R.drawable.verdant_garden_wallpaper,
                options,
            )
            if (decoded == null) {
                Log.e(TAG, "Could not decode the local Verdant wallpaper PNG.")
                return null
            }
            bitmap = decoded
            Log.i(TAG, "Wallpaper bitmap decoded: " + decoded.width + "x" + decoded.height +
                ", " + (decoded.allocationByteCount / 1024) + " KiB")
            return decoded
        }

        private fun drawFrame() {
            var canvas: Canvas? = null
            try {
                canvas = surfaceHolder.lockCanvas()
                if (canvas != null) renderBitmap(canvas)
            } catch (_: IllegalArgumentException) {
                // The surface may disappear between lifecycle callbacks.
            } catch (_: IllegalStateException) {
                // Surface recreation is normal while Android previews/applies wallpaper.
            } finally {
                if (canvas != null) {
                    try {
                        surfaceHolder.unlockCanvasAndPost(canvas)
                    } catch (error: Exception) {
                        Log.w(TAG, "Wallpaper surface changed while posting the PNG frame", error)
                    }
                }
            }
        }

        private fun renderBitmap(canvas: Canvas) {
            val image = wallpaperBitmap() ?: return
            val width = canvas.width.toFloat()
            val height = canvas.height.toFloat()
            val scale = max(width / image.width, height / image.height) * EXTRA_ZOOM
            val renderWidth = image.width * scale
            val renderHeight = image.height * scale
            val horizontalTravel = (renderWidth - width).coerceAtLeast(0f) * 0.22f
            val verticalTravel = (renderHeight - height).coerceAtLeast(0f) * 0.16f
            val phase = if (motionEnabled && windLevel > 0) sin(frame / 180.0).toFloat() else 0f
            val amplitude = if (windLevel >= 2) 1f else 0.4f
            val pageOffset = horizontalOffset * (renderWidth - width).coerceAtLeast(0f) * 0.18f
            val left = (width - renderWidth) / 2f - pageOffset + phase * amplitude * horizontalTravel
            val top = (height - renderHeight) / 2f + phase * amplitude * verticalTravel
            destination.set(left, top, left + renderWidth, top + renderHeight)
            canvas.drawBitmap(image, null, destination, paint)

            val mode = if (timeMode != "AUTO") timeMode else when (
                Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
            ) {
                in 5..7 -> "DAWN"
                in 8..16 -> "DAY"
                in 17..19 -> "DUSK"
                else -> "NIGHT"
            }
            val tint = when (mode) {
                "DAWN" -> 0x14CE865D
                "DAY" -> 0x084F9B69
                "DUSK" -> 0x1B665078
                else -> 0x2807172B
            }.toInt()
            canvas.drawColor(tint, PorterDuff.Mode.SRC_ATOP)
            if (motionEnabled && windLevel > 0) frame++
        }
    }
}
'''
    write(path, source)


def update_readme(project: Path) -> None:
    path = project / "README.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if "## Phase 1 performance safeguards" not in text:
        text += r'''

## Phase 1 performance safeguards

- Live wallpaper motion defaults to Calm (static) and only schedules animation frames when the user enables Wind.
- The live wallpaper draws only on visibility/surface/offset changes while static; hidden wallpaper engines do not render.
- Opt-in wallpaper animation is capped at 20 frames per second.
- The wallpaper bitmap is decoded on the render thread in RGB_565 format to reduce decoded bitmap memory by approximately half versus ARGB_8888.
- Installed-app icons load asynchronously from PackageManager and use a bounded 4 MiB LRU bitmap cache.
- App discovery is cached for 20 seconds; package queries stay on Dispatchers.IO, manual refresh bypasses the cache, and a stale list remains usable when Android temporarily rejects a scan.

These are code-level safeguards. Frame timing, memory, CPU and battery targets still require Perfetto/Macrobenchmark traces on physical Android hardware.
'''
        path.write_text(text, encoding="utf-8")


def main(project: Path) -> None:
    project = project.resolve()
    patch_preferences(project)
    patch_repository(project)
    patch_app_root(project)
    patch_drawer_search(project)
    write_icon_component(project)
    write_wallpaper_service(project)
    update_readme(project)
    print("Applied Phase 1: static-by-default wallpaper, RGB_565 decode, async cached app icons, and cached app discovery.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_performance.py PROJECT_DIR")
    main(Path(sys.argv[1]))
