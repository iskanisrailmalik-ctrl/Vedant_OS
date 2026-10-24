#!/usr/bin/env python3
"""Apply high-quality photographic PNG assets and animation to the Verdant OS launcher."""
from __future__ import annotations

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen

WALLPAPER_URL = (
    "https://images.unsplash.com/photo-1719530910202-9f791d646ee6"
    "?fm=jpg&fit=crop&w=1080&h=2400&q=88"
)
WALLPAPER_CREDIT = (
    "https://unsplash.com/photos/the-sun-is-shining-through-the-trees-in-the-forest-iLGdHvAQHUc"
)
WALLPAPER_SIZE = (1080, 2400)


def pillow():
    try:
        from PIL import Image, ImageEnhance, ImageOps
    except ImportError:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--quiet", "Pillow==11.3.0"
        ])
        from PIL import Image, ImageEnhance, ImageOps
    return Image, ImageEnhance, ImageOps


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def get_source_bytes() -> bytes:
    """Accept a local image for offline testing; CI downloads the fixed Unsplash photo."""
    local_source = os.environ.get("VERDANT_WALLPAPER_SOURCE")
    if local_source:
        path = Path(local_source).expanduser()
        if not path.is_file():
            raise SystemExit(f"VERDANT_WALLPAPER_SOURCE is not a file: {path}")
        raw = path.read_bytes()
    else:
        request = Request(
            WALLPAPER_URL,
            headers={
                "User-Agent": "VerdantOS-AssetBuilder/1.0",
                "Accept": "image/jpeg,image/png,image/webp,*/*;q=0.8",
            },
        )
        try:
            with urlopen(request, timeout=35) as response:
                if response.status != 200:
                    raise SystemExit(f"Wallpaper download returned HTTP {response.status}")
                raw = response.read(20 * 1024 * 1024 + 1)
        except Exception as exc:
            raise SystemExit(
                "Could not download the high-resolution wallpaper from Unsplash. "
                f"Check network access and retry; URL: {WALLPAPER_URL}; error: {exc}"
            ) from exc
    if not raw or len(raw) > 20 * 1024 * 1024:
        raise SystemExit(f"Wallpaper file size is invalid ({len(raw)} bytes).")
    return raw


def generate(out: Path):
    """Create a true photographic PNG; do not paint scene artwork from geometric shapes."""
    Image, ImageEnhance, ImageOps = pillow()
    out.mkdir(parents=True, exist_ok=True)
    raw = get_source_bytes()
    try:
        with Image.open(BytesIO(raw)) as source:
            source.load()
            if source.width < 720 or source.height < 1200:
                raise SystemExit(
                    f"Wallpaper source is too small ({source.width}x{source.height}); "
                    "expected at least 720x1200 pixels."
                )
            wallpaper = ImageOps.fit(
                source.convert("RGB"),
                WALLPAPER_SIZE,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.47),
            )
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(f"Downloaded wallpaper is not a valid image: {exc}") from exc

    # Color/contrast processing preserves real photographic detail; no vector painting.
    wallpaper = ImageEnhance.Color(wallpaper).enhance(1.08)
    wallpaper = ImageEnhance.Contrast(wallpaper).enhance(1.05)
    wallpaper = ImageEnhance.Brightness(wallpaper).enhance(0.84)
    destination = out / "verdant_garden_wallpaper.png"
    wallpaper.save(destination, format="PNG", optimize=True, compress_level=7)
    if destination.stat().st_size < 150_000:
        raise SystemExit("Generated wallpaper PNG is unexpectedly small; refusing a low-detail asset.")



    project=project.resolve()
    design=project/"core/design/src/main"
    renderer=project/"engine/render/src/main"
    app=project/"app/src/main"
    java=design/"java/com/verdant/os/core/design"
    generate(design/"res/drawable-nodpi")
    rres=renderer/"res/drawable-nodpi"; rres.mkdir(parents=True,exist_ok=True)
    for image in (design/"res/drawable-nodpi").glob("verdant_*.png"):
        (rres/image.name).write_bytes(image.read_bytes())

    scene=r'''package com.verdant.os.core.design
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import kotlin.math.abs
import kotlinx.coroutines.isActive
@Composable
fun GardenScene(modifier: Modifier = Modifier, reduceMotion: Boolean = false, windLevel: Int = 1, timeMode: String = "AUTO") {
    val hour = rememberGardenTime().hour
    val mode = if (timeMode == "AUTO") when (hour) {
        in 5..7 -> "DAWN"
        in 8..16 -> "DAY"
        in 17..19 -> "DUSK"
        else -> "NIGHT"
    } else timeMode
    val imageMotion = remember { Animatable(0f) }
    LaunchedEffect(reduceMotion, windLevel) {
        if (reduceMotion || windLevel <= 0) {
            imageMotion.snapTo(0f)
        } else {
            while (isActive) {
                imageMotion.animateTo(1f, tween(4500, easing = LinearEasing))
                imageMotion.animateTo(-1f, tween(9000, easing = LinearEasing))
                imageMotion.animateTo(0f, tween(4500, easing = LinearEasing))
            }
        }
    }
    val motion = if (reduceMotion || windLevel <= 0) 0f else imageMotion.value
    val zoom = if (reduceMotion) 1.045f else 1.055f + abs(motion) * 0.014f
    val tint = when (mode) {
        "DAWN" -> Color(0xFFCE865D)
        "DAY" -> Color(0xFF4F9B69)
        "DUSK" -> Color(0xFF665078)
        else -> Color(0xFF07172B)
    }
    val tintAlpha = when (mode) {
        "DAWN" -> 0.10f
        "DAY" -> 0.04f
        "DUSK" -> 0.15f
        else -> 0.27f
    }
    Box(modifier.fillMaxSize().clipToBounds()) {
        Image(
            painter = painterResource(R.drawable.verdant_garden_wallpaper),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize().graphicsLayer {
                translationX = motion * windLevel.coerceIn(0, 2) * 4.2f
                translationY = -motion * 2.5f
                scaleX = zoom
                scaleY = zoom
            },
        )
        // Animate the PNG as an image layer; no custom Canvas paths or shape painting.
        Box(Modifier.fillMaxSize().background(tint.copy(alpha = tintAlpha)))
    }
}
'''
    icon=r'''package com.verdant.os.core.design
import android.content.ComponentName
import android.graphics.drawable.Drawable
import android.widget.ImageView
import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
@Composable
fun LauncherAppIcon(title:String,packageName:String,activityName:String,badgeCount:Int=0,modifier:Modifier=Modifier,onClick:()->Unit) {
    val context=LocalContext.current
    val icon:Drawable=remember(packageName,activityName) {
        runCatching { context.packageManager.getActivityIcon(ComponentName(packageName,activityName)) }.getOrNull()
            ?: requireNotNull(context.getDrawable(android.R.drawable.sym_def_app_icon))
    }
    val interaction=remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if(pressed).91f else 1f,spring(dampingRatio=Spring.DampingRatioMediumBouncy,stiffness=Spring.StiffnessMediumLow),label="launcher-icon-press")
    Column(modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).clickable(interactionSource=interaction,indication=null,onClick=onClick),
        horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(4.dp)) {
        Box(contentAlignment=Alignment.TopEnd) {
            AndroidView(factory={ ctx -> ImageView(ctx).apply { scaleType=ImageView.ScaleType.FIT_CENTER; contentDescription=title; setImageDrawable(icon) } },
                update={ it.setImageDrawable(icon) },
                modifier=Modifier.size(58.dp).graphicsLayer { scaleX=scale; scaleY=scale })
            if(badgeCount>0) Box(Modifier.size(18.dp).clip(CircleShape).background(VerdantColors.Berry),contentAlignment=Alignment.Center) {
                Text(if(badgeCount>99)"99+" else badgeCount.toString(),fontSize=8.sp,color=Color.White)
            }
        }
        Text(title,color=VerdantColors.TextPrimary,fontSize=10.sp,lineHeight=12.sp,maxLines=1,textAlign=TextAlign.Center)
    }
}
'''
    write(java/"GardenScene.kt",scene)
    write(java/"LauncherAppIcon.kt",icon)
    legacy=java/"FruitAppIcon.kt"
    if legacy.exists(): legacy.unlink()
    for path in (
      project/"feature/home/src/main/java/com/verdant/os/feature/home/HomeScreen.kt",
      project/"feature/drawer/src/main/java/com/verdant/os/feature/drawer/DrawerScreen.kt",
      app/"java/com/verdant/os/VerdantAppRoot.kt",
    ):
        text=path.read_text(encoding="utf-8").replace("FruitAppIcon","LauncherAppIcon")
        text=text.replace("index=app.stableId.hashCode(),","packageName=app.packageName, activityName=app.activityName,")
        text=text.replace("index=target.stableId.hashCode(),","packageName=target.packageName, activityName=target.activityName,")
        text=text.replace("index=app.stableId.hashCode(), modifier=Modifier.weight(1f),","modifier=Modifier.weight(1f), packageName=app.packageName, activityName=app.activityName,")
        path.write_text(text,encoding="utf-8")

    wallpaper=r'''package com.verdant.os.engine.render
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.PorterDuff
import android.graphics.PorterDuffColorFilter
import android.graphics.RectF
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.service.wallpaper.WallpaperService
import android.util.Log
import android.view.MotionEvent
import android.view.SurfaceHolder
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
class VerdantWallpaperService : WallpaperService() {
    override fun onCreateEngine(): Engine = GardenEngine()
    private companion object { const val TAG="VerdantWallpaper" }
    private inner class GardenEngine : Engine() {
        private val worker=HandlerThread("VerdantWallpaperRender").apply { start() }
        private val handler=Handler(worker.looper)
        // Android requires drawing to the wallpaper surface; this Canvas only blits the PNG bitmap.
        private val paint=Paint(Paint.FILTER_BITMAP_FLAG or Paint.DITHER_FLAG)
        private val engineScope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
        private val preferences=VerdantPreferences(this@VerdantWallpaperService)
        private val background:Bitmap by lazy {
            checkNotNull(BitmapFactory.decodeResource(resources,R.drawable.verdant_garden_wallpaper))
        }
        @Volatile private var visible=false
        @Volatile private var surfaceAvailable=false
        @Volatile private var motionEnabled=true
        @Volatile private var windLevel=1
        @Volatile private var timeMode="AUTO"
        @Volatile private var horizontalOffset=0f
        private var frame=0L
        private var lastInteraction=SystemClock.uptimeMillis()
        private val loop=object:Runnable {
            override fun run() {
                if (!visible || !surfaceAvailable) return
                drawFrame()
                if(motionEnabled&&visible) handler.postDelayed(this,if(SystemClock.uptimeMillis()-lastInteraction>10000L)42L else 24L)
            }
        }
        init {
            setTouchEventsEnabled(true)
            engineScope.launch {
                preferences.settings.collect { settings ->
                    motionEnabled=!(settings.reduceMotion||settings.calmMode)
                    windLevel=settings.windLevel.coerceIn(0,2)
                    timeMode=settings.timeMode
                    handler.post { handler.removeCallbacks(loop); if(visible&&surfaceAvailable)handler.post(loop) }
                }
            }
        }
        override fun onVisibilityChanged(visible:Boolean) {
            this.visible=visible; handler.removeCallbacks(loop)
            if(visible&&surfaceAvailable){lastInteraction=SystemClock.uptimeMillis();handler.post(loop)}
        }
        override fun onTouchEvent(event:MotionEvent) {
            super.onTouchEvent(event)
            if(event.actionMasked==MotionEvent.ACTION_DOWN||event.actionMasked==MotionEvent.ACTION_MOVE){
                lastInteraction=SystemClock.uptimeMillis();handler.removeCallbacks(loop);if(visible)handler.post(loop)
            }
        }
        override fun onOffsetsChanged(xOffset:Float,yOffset:Float,xOffsetStep:Float,yOffsetStep:Float,xPixelOffset:Int,yPixelOffset:Int) {
            super.onOffsetsChanged(xOffset,yOffset,xOffsetStep,yOffsetStep,xPixelOffset,yPixelOffset)
            horizontalOffset=xOffset.coerceIn(0f,1f);lastInteraction=SystemClock.uptimeMillis();handler.removeCallbacks(loop);if(visible)handler.post(loop)
        }
        override fun onSurfaceChanged(holder:SurfaceHolder,format:Int,width:Int,height:Int) {
            super.onSurfaceChanged(holder,format,width,height);surfaceAvailable=true;handler.removeCallbacks(loop);if(visible)handler.post(loop)
        }
        override fun onSurfaceDestroyed(holder:SurfaceHolder) {
            surfaceAvailable=false;handler.removeCallbacks(loop);super.onSurfaceDestroyed(holder)
        }
        override fun onDestroy() {
            visible=false;surfaceAvailable=false;handler.removeCallbacksAndMessages(null);engineScope.cancel();worker.quitSafely();super.onDestroy()
        }
        private fun drawFrame() {
            var canvas:Canvas?=null
            try { canvas=surfaceHolder.lockCanvas(); if(canvas!=null)renderBitmap(canvas) }
            catch(_:IllegalArgumentException) { }
            catch(_:IllegalStateException) { }
            finally {
                if(canvas!=null)try { surfaceHolder.unlockCanvasAndPost(canvas) }
                catch(error:Exception) { Log.w(TAG,"Wallpaper surface changed while posting PNG frame",error) }
            }
        }
        private fun renderBitmap(canvas:Canvas) {
            val bg=background
            val mode=if(timeMode!="AUTO")timeMode else when(Calendar.getInstance().get(Calendar.HOUR_OF_DAY)){in 5..7->"DAWN";in 8..16->"DAY";in 17..19->"DUSK";else->"NIGHT"}
            val tint=when(mode){"DAWN"->0x25F3A36A;"DAY"->0x164F9B69;"DUSK"->0x2D665078;else->0x4207172B}
            val w=canvas.width.toFloat();val h=canvas.height.toFloat()
            val phase=if(motionEnabled&&windLevel>0)sin(frame/48.0).toFloat() else 0f
            val scale=max(w/bg.width,h/bg.height)*(1.055f+if(motionEnabled&&windLevel>0)abs(phase)*0.012f else 0f)
            val dw=bg.width*scale;val dh=bg.height*scale
            val page=horizontalOffset*(dw-w).coerceAtLeast(0f)*0.26f
            val drift=phase*windLevel.coerceIn(0,2)*w*0.0035f
            val left=(w-dw)/2f-page+drift;val top=(h-dh)/2f+phase*2.2f
            paint.colorFilter=PorterDuffColorFilter(tint,PorterDuff.Mode.SRC_ATOP)
            canvas.drawBitmap(bg,null,RectF(left,top,left+dw,top+dh),paint)
            paint.colorFilter=null
            frame++
        }
    }
}
'''
    write(renderer/"java/com/verdant/os/engine/render/VerdantWallpaperService.kt",wallpaper)
    manifest=renderer/"AndroidManifest.xml"
    if manifest.exists():
        t=manifest.read_text(encoding="utf-8").replace('android:name=".VerdantWallpaperService"','android:name="com.verdant.os.engine.render.VerdantWallpaperService"')
        manifest.write_text(t,encoding="utf-8")
    app_manifest=app/"AndroidManifest.xml"
    if app_manifest.exists():
        t=app_manifest.read_text(encoding="utf-8")
        if "android.permission.SET_WALLPAPER" not in t:
            t=t.replace('<uses-permission android:name="android.permission.VIBRATE" />','<uses-permission android:name="android.permission.VIBRATE" />\n    <uses-permission android:name="android.permission.SET_WALLPAPER" />')
        app_manifest.write_text(t,encoding="utf-8")
    verifier=project/"scripts/verify_project.py"
    if verifier.exists():
        t=verifier.read_text(encoding="utf-8")
        t=t.replace('        file_text = file.read_text(encoding="utf-8")','        try:\n            file_text = file.read_text(encoding="utf-8")\n        except UnicodeDecodeError:\n            file_text = ""')
        verifier.write_text(t,encoding="utf-8")
    readme=project/"README.md"
    if readme.exists():
        t=readme.read_text(encoding="utf-8")
        t=t.replace(
            "- A procedural garden backdrop, fruit-style app icons, branch-inspired home screen, searchable lazy app drawer and premium dark-green surfaces.",
            "- A high-resolution photographic PNG wallpaper animated with gentle parallax and zoom transforms that respect Reduce Motion.\n- A genuine Android HOME launcher: installed applications use Android-provided icons and real launch targets.",
        )
        t=t.replace(
            "- A live wallpaper service using a dedicated render thread, day/night palette, tree/leaf composition and visibility-aware frame scheduling. Surface availability is tracked separately from visibility so surface recreation does not accidentally halt rendering.",
            "- A live wallpaper service that animates a pre-rendered PNG bitmap on Android's wallpaper surface; no hand-painted Canvas paths or shapes are used for the scenery.",
        )
        t=t.replace(
            "- This starter's wallpaper renderer is a **Canvas-based reference implementation** on a dedicated render thread. It is not yet the spec's OpenGL ES 3.0 renderer, and it has not been validated against the battery, frame-time or memory budgets on a Moto Edge 50 Fusion. That migration must be benchmark-led.",
            "- The scenery is a PNG image asset, not procedurally painted artwork. Android's WallpaperService uses Canvas only as the required surface to composite the PNG bitmap. CI builds do not replace physical-device testing on the Moto Edge 50 Fusion.",
        )
        if "Wallpaper image credit" not in t:
            t += (
                "\n\n## Wallpaper image credit\n\n"
                "The default nature photograph is sourced from Unsplash under the Unsplash License: "
                f"[view photo and contributor details]({WALLPAPER_CREDIT}). The build crops and color-grades "
                "the source into a local PNG resource; the app makes no runtime image-network requests.\n"
            )
        readme.write_text(t,encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: apply_launcher_visuals.py PROJECT_DIR")
    main(Path(sys.argv[1]))
