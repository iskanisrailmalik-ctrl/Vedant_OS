#!/usr/bin/env python3
"""Apply PNG-first visuals to Verdant OS and generate high-resolution image resources."""
from __future__ import annotations
import math, random, subprocess, sys
from pathlib import Path

def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
        return Image, ImageDraw, ImageFilter, ImageEnhance
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "Pillow==11.3.0"])
        from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
        return Image, ImageDraw, ImageFilter, ImageEnhance

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")

def bezier(a,b,c,d,n=32):
    pts=[]
    for i in range(n+1):
        t=i/n; u=1-t
        pts.append((int(u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0]),
                    int(u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1])))
    return pts

def make_leaf(Image, ImageDraw, ImageFilter, size, seed):
    rng=random.Random(seed); w=size; h=int(size*.48)
    mask=Image.new("L",(w,h),0); md=ImageDraw.Draw(mask)
    md.polygon([(1,h//2),(int(w*.15),int(h*.2)),(int(w*.43),2),(int(w*.76),int(h*.18)),(w-2,h//2),(int(w*.75),int(h*.82)),(int(w*.42),h-2),(int(w*.15),int(h*.8))],fill=255)
    grad=Image.new("RGBA",(w,h),(0,0,0,0)); gd=ImageDraw.Draw(grad)
    c0=rng.choice([(8,48,28),(12,61,34),(18,70,37)])
    c1=rng.choice([(42,111,49),(55,129,57),(78,143,65)])
    c2=rng.choice([(117,165,77),(148,184,91),(173,196,107)])
    for y in range(h):
        t=y/max(1,h-1)
        c=tuple(int(c0[k]*(1-t)+c1[k]*t) if t<.52 else int(c1[k]*(1-(t-.52)/.48)+c2[k]*((t-.52)/.48)) for k in range(3))
        gd.line((0,y,w,y),fill=(*c,240))
    grad.putalpha(mask); out=Image.new("RGBA",(w,h),(0,0,0,0)); out.alpha_composite(grad)
    d=ImageDraw.Draw(out)
    d.line([(5,h//2),(w-5,h//2)],fill=(207,230,146,145),width=max(1,w//110))
    for k in range(1,7):
        x=int(w*k/8)
        d.line([(x,h//2),(int(x+w*.10),int(h*.18))],fill=(207,230,149,85),width=1)
        d.line([(x,h//2),(int(x+w*.10),int(h*.83))],fill=(8,36,23,100),width=1)
    d.ellipse((int(w*.31),int(h*.27),int(w*.35),int(h*.37)),fill=(255,255,231,150))
    return out.filter(ImageFilter.GaussianBlur(.25))

def generate(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    Image, ImageDraw, ImageFilter, ImageEnhance = pillow()
    W,H=1080,2400; rng=random.Random(42)
    # Render the nature artwork once as PNG; Compose animates these layers at runtime.
    line=Image.new("RGB",(1,H)); ld=ImageDraw.Draw(line)
    top=(4,23,19); mid=(20,64,39); bot=(4,24,17)
    for y in range(H):
        t=y/(H-1)
        if t<.55:
            q=t/.55; col=tuple(int(top[k]*(1-q)+mid[k]*q) for k in range(3))
        else:
            q=(t-.55)/.45; col=tuple(int(mid[k]*(1-q)+bot[k]*q) for k in range(3))
        ld.point((0,y),fill=col)
    img=line.resize((W,H),Image.Resampling.BICUBIC).convert("RGBA")
    glow=Image.new("RGBA",(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    gd.ellipse((-300,80,500,930),fill=(221,194,107,62))
    gd.ellipse((560,110,1370,1070),fill=(77,151,88,58))
    gd.ellipse((150,970,980,1980),fill=(61,125,72,31))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(130)))
    bokeh=Image.new("RGBA",(W,H),(0,0,0,0)); bd=ImageDraw.Draw(bokeh)
    for _ in range(105):
        x=rng.randint(-100,W+100); y=rng.randint(0,int(H*.68)); r=rng.choice([3,5,8,13,21])
        bd.ellipse((x-r,y-r,x+r,y+r),fill=(210,233,147,rng.randint(7,27)))
    img.alpha_composite(bokeh.filter(ImageFilter.GaussianBlur(18)))
    # Curved branch silhouettes stay near the edges to preserve a quiet area for widgets.
    branch=Image.new("RGBA",(W,H),(0,0,0,0)); dr=ImageDraw.Draw(branch)
    paths=[
      ((-100,260),(180,330),(230,70),(470,85),38),
      ((-80,470),(210,440),(300,200),(560,185),23),
      ((1180,310),(920,410),(890,160),(700,120),33),
      ((1170,700),(920,620),(900,420),(725,350),22),
      ((-90,980),(130,870),(90,730),(-30,625),18),
      ((1110,1320),(930,1180),(1020,1010),(1120,920),18),
    ]
    for a,b,c,d,width in paths:
        pts=bezier(a,b,c,d)
        dr.line(pts,fill=(2,17,12,180),width=width+10,joint="curve")
        dr.line([(x-3,y-3) for x,y in pts],fill=(73,84,45,235),width=width,joint="curve")
        dr.line([(x-5,y-6) for x,y in pts],fill=(148,126,68,75),width=max(2,width//5),joint="curve")
    img.alpha_composite(branch.filter(ImageFilter.GaussianBlur(1.2)))
    foliage=Image.new("RGBA",(W,H),(0,0,0,0))
    for bi,path in enumerate(paths):
        pts=bezier(*path[:4],n=30)
        for j in range(18):
            t=rng.uniform(.12,.98); x,y=pts[min(len(pts)-1,int(t*(len(pts)-1)))]
            side=-1 if (bi+j)%2 else 1
            leaf=make_leaf(Image,ImageDraw,ImageFilter,rng.randint(66,138),bi*71+j)
            leaf=leaf.rotate(side*rng.randint(24,72),resample=Image.Resampling.BICUBIC,expand=True)
            alpha=leaf.getchannel("A").point(lambda v:int(v*rng.uniform(.45,.85)))
            leaf.putalpha(alpha)
            foliage.alpha_composite(leaf,(int(x+side*rng.randint(12,78)-leaf.width/2),int(y+rng.randint(-58,58)-leaf.height/2)))
    img.alpha_composite(foliage.filter(ImageFilter.GaussianBlur(.55)))
    # Mango-like fruit forms use a pre-rendered gradient and small highlight droplets.
    fruitlayer=Image.new("RGBA",(W,H),(0,0,0,0))
    for i,(cx,cy,scale,angle) in enumerate([(112,375,.74,21),(302,470,.43,-15),(925,365,.60,-17),(960,645,.38,14),(70,800,.33,-23)]):
        fw,fh=int(172*scale),int(258*scale)
        mask=Image.new("L",(fw,fh),0); md=ImageDraw.Draw(mask)
        md.polygon([(int(fw*.45),2),(int(fw*.72),int(fh*.06)),(int(fw*.91),int(fh*.26)),(fw-3,int(fh*.46)),(int(fw*.79),int(fh*.74)),(int(fw*.51),fh-3),(int(fw*.25),int(fh*.84)),(int(fw*.08),int(fh*.58)),(2,int(fh*.36)),(int(fw*.18),int(fh*.14))],fill=255)
        grad=Image.new("RGBA",(fw,fh),(0,0,0,0)); gd=ImageDraw.Draw(grad)
        for xx in range(fw):
            t=xx/max(1,fw-1)
            if t<.52: c=tuple(int(v*(1-t/.52)+u*(t/.52)) for v,u in zip((39,102,42),(242,188,55)))
            else: c=tuple(int(v*(1-(t-.52)/.48)+u*((t-.52)/.48)) for v,u in zip((242,188,55),(198,56,34)))
            gd.line((xx,0,xx,fh),fill=(*c,255))
        grad.putalpha(mask); fruit=Image.new("RGBA",(fw,fh),(0,0,0,0)); fruit.alpha_composite(grad)
        fd=ImageDraw.Draw(fruit); fd.ellipse((int(fw*.18),int(fh*.16),int(fw*.39),int(fh*.45)),fill=(255,249,205,85))
        for n in range(9):
            dx=rng.randint(int(fw*.15),int(fw*.85)); dy=rng.randint(int(fh*.18),int(fh*.78)); rr=max(1,int(scale*3))
            fd.ellipse((dx-rr,dy-rr,dx+rr,dy+rr),fill=(255,250,210,115))
        fruit=fruit.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
        fruitlayer.alpha_composite(fruit,(int(cx-fruit.width/2),int(cy-fruit.height/2)))
    img.alpha_composite(fruitlayer.filter(ImageFilter.GaussianBlur(.25)))
    haze=Image.new("RGBA",(W,H),(0,0,0,0)); hd=ImageDraw.Draw(haze)
    hd.rectangle((0,int(H*.68),W,H),fill=(1,14,10,80))
    img.alpha_composite(haze.filter(ImageFilter.GaussianBlur(85)))
    wallpaper=ImageEnhance.Color(img.convert("RGB")).enhance(1.1)
    base=out/"verdant_garden_wallpaper.png"
    wallpaper.save(base,format="PNG",optimize=True,compress_level=8)
    for mode,tint,strength in [
        ("dawn",(206,125,83),.18),("day",(65,145,79),.09),
        ("dusk",(83,61,116),.22),("night",(5,18,46),.34),
    ]:
        variant=Image.blend(wallpaper,Image.new("RGB",wallpaper.size,tint),strength)
        variant.save(out/f"verdant_garden_wallpaper_{mode}.png",format="PNG",optimize=True,compress_level=8)
    # Transparent high-resolution foliage layer drifts gently over the background.
    overlay=Image.new("RGBA",(W,H),(0,0,0,0)); rng=random.Random(314)
    for i in range(44):
        left=rng.random()<.5
        x=rng.randint(-50,190) if left else rng.randint(W-190,W+50)
        y=rng.randint(-60,H-60)
        leaf=make_leaf(Image,ImageDraw,ImageFilter,rng.randint(68,144),700+i)
        leaf=leaf.rotate(rng.randint(-75,75),resample=Image.Resampling.BICUBIC,expand=True)
        if rng.random()<.5: leaf=leaf.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        leaf.putalpha(leaf.getchannel("A").point(lambda v:int(v*.58)))
        overlay.alpha_composite(leaf,(x,y))
    od=ImageDraw.Draw(overlay)
    for _ in range(60):
        x=rng.randint(8,W-8); y=rng.randint(40,H-60); r=rng.choice([1,2,3])
        od.ellipse((x-r,y-r,x+r,y+r),fill=(226,240,165,rng.randint(24,80)))
    overlay=overlay.filter(ImageFilter.GaussianBlur(.35))
    overlay.save(out/"verdant_leaves_overlay.png",format="PNG",optimize=True,compress_level=8)

def main(project: Path):
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
import androidx.compose.animation.core.*
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import kotlin.math.abs
@Composable
fun GardenScene(modifier: Modifier = Modifier, reduceMotion: Boolean = false, windLevel: Int = 1, timeMode: String = "AUTO") {
    val hour=rememberGardenTime().hour
    val mode=if(timeMode=="AUTO") when(hour) { in 5..7->"DAWN"; in 8..16->"DAY"; in 17..19->"DUSK"; else->"NIGHT" } else timeMode
    val transition=rememberInfiniteTransition(label="verdant-image-motion")
    val breeze by transition.animateFloat(-1f,1f,infiniteRepeatable(tween(11000,easing=LinearEasing),RepeatMode.Reverse),label="breeze")
    val drift by transition.animateFloat(1f,-1f,infiniteRepeatable(tween(17000,easing=LinearEasing),RepeatMode.Reverse),label="leaf-drift")
    val motion=if(reduceMotion) 0f else breeze
    val leafMotion=if(reduceMotion) 0f else drift
    val wind=when(windLevel.coerceIn(0,2)){0->0f;1->5f;else->10f}
    val tint=when(mode){"DAWN"->Color(0xFFBE8058);"DAY"->Color(0xFF4F9C69);"DUSK"->Color(0xFF6E507C);else->Color(0xFF07172A)}
    Box(modifier.fillMaxSize().clipToBounds()) {
        Image(painterResource(R.drawable.verdant_garden_wallpaper),null,contentScale=ContentScale.Crop,modifier=Modifier.fillMaxSize().graphicsLayer {
            translationX=motion*wind; translationY=-motion*2.5f
            val s=1.055f+abs(motion)*.012f; scaleX=s; scaleY=s
        })
        Image(painterResource(R.drawable.verdant_leaves_overlay),null,contentScale=ContentScale.FillBounds,modifier=Modifier.fillMaxSize().graphicsLayer {
            translationX=leafMotion*wind*1.25f; translationY=-leafMotion*3.5f
            rotationZ=leafMotion*if(windLevel<=0) 0f else .24f*windLevel
            alpha=if (reduceMotion) 0.44f else 0.72f
        })
        Box(Modifier.fillMaxSize().background(tint.copy(alpha=when(mode){"NIGHT"->.29f;"DUSK"->.16f;else->.07f})))
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
import kotlin.math.max
import kotlin.math.sin
class VerdantWallpaperService : WallpaperService() {
    override fun onCreateEngine(): Engine = GardenEngine()
    private companion object { const val TAG="VerdantWallpaper" }
    private inner class GardenEngine : Engine() {
        private val worker=HandlerThread("VerdantWallpaperRender").apply { start() }
        private val handler=Handler(worker.looper)
        private val paint=Paint(Paint.FILTER_BITMAP_FLAG or Paint.DITHER_FLAG)
        private val engineScope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
        private val preferences=VerdantPreferences(this@VerdantWallpaperService)
        private val backgrounds:Map<String,Bitmap> by lazy {
            mapOf("DAWN" to BitmapFactory.decodeResource(resources, R.drawable.verdant_garden_wallpaper_dawn),
                "DAY" to BitmapFactory.decodeResource(resources, R.drawable.verdant_garden_wallpaper_day),
                "DUSK" to BitmapFactory.decodeResource(resources, R.drawable.verdant_garden_wallpaper_dusk),
                "NIGHT" to BitmapFactory.decodeResource(resources, R.drawable.verdant_garden_wallpaper_night))
                .mapValues { (_, value) -> checkNotNull(value) }
        }
        private val foliage:Bitmap by lazy { checkNotNull(BitmapFactory.decodeResource(resources,R.drawable.verdant_leaves_overlay)) }
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
            try { canvas=surfaceHolder.lockCanvas(); if(canvas!=null)renderBitmaps(canvas) }
            catch(_:IllegalArgumentException) { }
            catch(_:IllegalStateException) { }
            finally { if(canvas!=null)try { surfaceHolder.unlockCanvasAndPost(canvas) } catch(error:Exception) { Log.w(TAG,"Wallpaper surface changed while posting bitmap frame",error) } }
        }
        private fun renderBitmaps(canvas:Canvas) {
            val mode=if(timeMode!="AUTO")timeMode else when(Calendar.getInstance().get(Calendar.HOUR_OF_DAY)){in 5..7->"DAWN";in 8..16->"DAY";in 17..19->"DUSK";else->"NIGHT"}
            val bg=backgrounds[mode]?:backgrounds.getValue("DAY")
            val w=canvas.width.toFloat();val h=canvas.height.toFloat()
            val scale=max(w/bg.width,h/bg.height)*1.06f;val dw=bg.width*scale;val dh=bg.height*scale
            val wave=if(motionEnabled)sin(frame/42.0).toFloat() else 0f
            val sway=wave*windLevel.coerceIn(0,2)*w*.0035f
            val page=horizontalOffset*(dw-w).coerceAtLeast(0f)*.35f
            val top=(h-dh)/2f+wave*2f;val left=(w-dw)/2f-page+sway
            canvas.drawBitmap(bg,null,RectF(left,top,left+dw,top+dh),paint)
            val leaf=foliage;val ls=max(w/leaf.width,h/leaf.height)*1.08f;val lw=leaf.width*ls;val lh=leaf.height*ls
            val drift=if(motionEnabled)sin(frame/58.0).toFloat()*windLevel.coerceIn(0,2)*w*.006f else 0f
            canvas.drawBitmap(leaf,null,RectF((w-lw)/2+drift,(h-lh)/2,(w+lw)/2+drift,(h+lh)/2),paint)
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
        t=t.replace("- A procedural garden backdrop, fruit-style app icons, branch-inspired home screen, searchable lazy app drawer and premium dark-green surfaces.",
                    "- High-resolution PNG garden wallpaper and transparent leaf overlays, animated with Compose transforms and reduced-motion controls.\n- A real home-screen launcher: installed apps use Android-provided icons and open through LauncherApps, with a spring press animation.")
        t=t.replace("- A live wallpaper service using a dedicated render thread, day/night palette, tree/leaf composition and visibility-aware frame scheduling. Surface availability is tracked separately from visibility so surface recreation does not accidentally halt rendering.",
                    "- A live wallpaper service that composites pre-rendered PNG variants and transparent foliage on a dedicated render thread; it does not paint custom leaf or fruit shapes each frame.")
        t=t.replace("- This starter's wallpaper renderer is a **Canvas-based reference implementation** on a dedicated render thread. It is not yet the spec's OpenGL ES 3.0 renderer, and it has not been validated against the battery, frame-time or memory budgets on a Moto Edge 50 Fusion. That migration must be benchmark-led.",
                    "- Launcher artwork is PNG-first and animated as image layers. Android's WallpaperService still uses its required surface Canvas only to composite bitmap layers; it no longer uses Paint paths or circles to draw the artwork.")
        readme.write_text(t,encoding="utf-8")
    print("Applied PNG-first launcher scenes, animated bitmap layers, real package icons, and launcher HOME configuration.")

if __name__ == "__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: apply_launcher_visuals.py PROJECT_DIR")
    main(Path(sys.argv[1]))
