"""ECHO F1 v1: authored, parametric, millimetre-scale prototype.

Run from repository root: .venv-car/Scripts/python cad/designs/echo_f1.py
No inference, network access, imported supplier solids or code evaluation.
Purchased items are dimensioned reference geometry, not supplier CAD.
"""
from __future__ import annotations
import os, sys, json, math, hashlib, zipfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".setup/cache"))
DLL_HANDLES = []
if os.name == "nt" and (ROOT / ".setup/runtime-dlls").exists():
    DLL_HANDLES.append(os.add_dll_directory(str(ROOT / ".setup/runtime-dlls")))
import cadquery as cq
import trimesh
import numpy as np

OUT = ROOT / "builds/echo-f1-v1"
OUT.mkdir(parents=True, exist_ok=True)
for d in ["print", "step", "assembly-parts", "firmware", "checks"]:
    (OUT/d).mkdir(exist_ok=True)
AXLE_Z = 23.4
FRONT_X, REAR_X = -60, 66
WHEEL_INNER = 50.3
WALL = 2.4
MOUNTS = [(-36,-33),(-36,33),(40,-30),(40,30)]
PARTS, CAD, SHAPES, PRINTS = [], [], {}, []

def box(x,y,z,at=(0,0,0)):
    return cq.Workplane("XY").box(x,y,z).val().translate(at)

def cyl(r,h,at=(0,0,0),axis=(0,0,1)):
    return cq.Solid.makeCylinder(r,h,cq.Vector(*at),cq.Vector(*axis))

def fuse(*shapes):
    return shapes[0].fuse(*shapes[1:]).clean()

def holes_z(shape, points, d, bottom=-10, h=100):
    for x,y in points: shape=shape.cut(cyl(d/2,h,(x,y,bottom)))
    return shape.clean()

def polygon(points,z,h):
    return cq.Workplane("XY",origin=(0,0,z)).polyline(points).close().extrude(h).val()

def bnd(s):
    b=s.BoundingBox()
    return {"min":[b.xmin,b.ymin,b.zmin],"max":[b.xmax,b.ymax,b.zmax]}

def export_mesh(s,p):
    cq.exporters.export(s,str(p),tolerance=.045,angularTolerance=.1)
    m=trimesh.load_mesh(p,process=True)
    # Remove only exporter-degenerate triangles, no geometry repair / hole filling.
    keep=m.nondegenerate_faces(height=1e-7)
    removed=int((~keep).sum())
    if removed:
        m.update_faces(keep); m.remove_unreferenced_vertices(); m.export(p)
        m=trimesh.load_mesh(p,process=True)
    assert m.is_watertight, f"Non-watertight: {p.name}"
    assert m.is_winding_consistent and m.volume>0, f"Bad winding: {p.name}"
    err=abs(m.volume-s.Volume())/s.Volume()
    assert err<.01, f"Volume mismatch: {p.name}: {err}"
    return {"triangles":len(m.faces),"watertight":bool(m.is_watertight),"windingConsistent":bool(m.is_winding_consistent),"meshVolumeMm3":float(m.volume),"volumeRelativeError":err,"removedDegenerateFaces":removed}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def add(pid,name,s,color,role,why,kind="printed",source="M4KE authored geometry",material="PLA",print_rotation=None,print_note="平面朝下；0.20 mm 层高、4 壁、25% 填充。"):
    assert s.isValid() and s.Volume()>0, f"Invalid BRep {pid}"
    if kind=="printed": assert len(s.Solids())==1, f"Disconnected printed part {pid}"
    bounds=bnd(s); center=[(a+b)/2 for a,b in zip(bounds['min'],bounds['max'])]
    local=s.translate(tuple(-x for x in center))
    stl=OUT/"assembly-parts"/(pid+".stl")
    stats=export_mesh(local,stl)
    step=OUT/"step"/(pid+".step"); cq.exporters.export(local,str(step))
    re=cq.importers.importStep(str(step)).val()
    assert re.isValid() and abs(re.Volume()-local.Volume())/local.Volume()<1e-5
    size=[round(b-a,3) for a,b in zip(bounds['min'],bounds['max'])]
    PARTS.append({"id":pid,"name":name,"kind":kind,"material":material,"color":color,"shape":{"type":"box","size":size},"position":center,"rotation":[0,0,0],"source":source,"explanation":{"what":name,"role":role,"whyHere":why,"whyThis":"打印件：可重复生成的实体 CAD；先做公差试片。" if kind=="printed" else "按标注型号选购；此处为尺寸参考模型，不是厂家精细 CAD。"}})
    CAD.append({"id":pid,"valid":True,"solidCount":len(s.Solids()),"volumeMm3":s.Volume(),"bounds":bnd(local),"position":center,"rotation":[0,0,0],"stlUrl":f"/api/authored-builds/{OUT.name}/files/assembly-parts/{pid}.stl","stepUrl":f"/api/authored-builds/{OUT.name}/files/step/{pid}.step","sha256":{"stl":sha(stl),"step":sha(step)},"meshChecks":stats})
    SHAPES[pid]=s
    if kind=="printed":
        p=s
        if print_rotation: p=p.rotate((0,0,0),print_rotation[0],print_rotation[1])
        bb=bnd(p); p=p.translate((-(bb['min'][0]+bb['max'][0])/2,-(bb['min'][1]+bb['max'][1])/2,-bb['min'][2]))
        dest=OUT/"print"/(pid+".stl"); ms=export_mesh(p,dest)
        dims=[round(b-a,3) for a,b in zip(bnd(p)['min'],bnd(p)['max'])]
        PRINTS.append({"id":pid,"name":name,"file":f"print/{pid}.stl","sha256":sha(dest),"sizeMm":dims,"volumeMm3":p.Volume(),"solidEquivalentPlaGrams":round(p.Volume()*.00124,2),"orientation":print_note,"meshChecks":ms})
    print(f"OK {pid}: {size} mm",flush=True)

def shell_loft(sections,inner=False):
    wires=[]
    for x,w,h in sections:
        base=10.6
        if inner: w-=WALL; h-=WALL; base=9.5
        pts=[(-w,base),(-w,base+4),(-w*.85,h-4),(-w*.55,h),(w*.55,h),(w*.85,h-4),(w,base+4),(w,base)]
        wires.append(cq.Workplane("YZ",origin=(x,0,0)).polyline(pts).close().val())
    return cq.Solid.makeLoft(wires,ruled=True)

def make_design():
    outline=[(-102,-7),(-90,-11),(-57,-19),(-36,-40),(22,-44),(43,-36),(78,-23),(97,-17),(97,17),(78,23),(43,36),(22,44),(-36,40),(-57,19),(-90,11),(-102,7)]
    chassis=polygon(outline,7,3)
    # Front axle crossmember and uprights: through-bolted non-steering axles.
    chassis=fuse(chassis,box(14,96,3,(-60,0,8.5)))
    for side in [-1,1]:
        up=box(14,6,20,(-60,side*45,20))
        up=up.cut(cyl(1.65,20,(-60,side*35,AXLE_Z),(0,side,0)))
        chassis=fuse(chassis,up)
        # Diagonal reinforcement at the inner face, no ornamental suspension claim.
        rib=cq.Workplane("YZ",origin=(-64,0,0)).polyline([(side*22,10),(side*42,10),(side*42,24)]).close().extrude(8).val()
        chassis=fuse(chassis,rib)
    # Battery tray fences sized for max 60 x 64 x 17 mm holder.
    for y in [-33.5,33.5]: chassis=fuse(chassis,box(63,2,3,(0,y,11.5)))
    for x in [-31.5,31.5]: chassis=fuse(chassis,box(2,69,3,(x,0,11.5)))
    # Printed bridge pillars outside the battery rectangle, bolt from above into captive nuts.
    for x in [-35,35]:
        for y in [-22,22]:
            pillar=cyl(4.5,18,(x,y,10))
            pillar=pillar.cut(cyl(1.65,25,(x,y,7)))
            nut=cq.Workplane("XY",origin=(x,y,23.5)).polygon(6,6.7).extrude(2.6).val()
            # Side loading slot for M3 nut, accessible before shell fitting.
            pillar=pillar.cut(fuse(nut,box(10,5.8,2.6,(x+(-3 if x<0 else 3),y,24.8))))
            chassis=fuse(chassis,pillar)
    screw_pts=MOUNTS+[(66+dx,side*31) for side in [-1,1] for dx in [-9,9]]+[(-96,-4),(-96,4),(83,-18),(83,18),(89,0),(95,0)]
    chassis=holes_z(chassis,screw_pts,3.3)
    for x,y in MOUNTS: chassis=chassis.cut(cyl(5.3,12,(x,y,10)))
    # Battery and electronics cable ties: real accessible slots.
    for x in [-20,20]:
        for y in [-30,30]: chassis=chassis.cut(box(6,2.5,10,(x,y,8)))
    add("chassis","01 · 一体式底盘",chassis,"#22262d","承载电池、轴承座和电机；平整底面是装配基准。","电池位于两轴之间，降低重心；前轴固定方向。",print_note="底板朝下；支柱侧面螺母槽为短桥接；前轴孔横向打印后用 3.3 mm 钻头手动清孔。")

    # Removable electronics bridge, at z28; rectangular windows clear downward male pins.
    tray=box(80,50,2,(0,0,29))
    for y in [-13,13]: tray=tray.cut(box(53,5,5,(0,y,29)))
    for x in [-35,35]:
        for y in [-22,22]: tray=tray.cut(cyl(1.65,10,(x,y,25)))
    for x in [-18,18]: tray=tray.cut(box(3,8,6,(x,0,29)))
    add("electronics_bridge","02 · 可拆电子托架",tray,"#303741","ESP32 位于电池上方，用绝缘泡棉和扎带固定；侧槽让排针悬空。","四个螺钉即可取下换电池，不把主板埋进外壳。")

    for side,label in [(-1,"L"),(1,"R")]:
        saddle=box(24,28,18.5,(66,side*31,19.25))
        saddle=saddle.cut(box(12.6,30,20,(66,side*31,28.4)))
        saddle=holes_z(saddle,[(57,side*31),(75,side*31)],3.3)
        bridge=box(24,9,3,(66,side*31,30))
        bridge=holes_z(bridge,[(57,side*31),(75,side*31)],3.3)
        add("motor_saddle_"+label,"03 · 电机鞍座 "+label,saddle,"#272c35","夹持 FIT0094 金属减速电机，前端齿轮箱伸出。","槽宽 12.6 mm 留装配余量；0.2–0.4 mm 绝缘软垫消除松动。")
        add("motor_clamp_"+label,"04 · 电机压条 "+label,bridge,"#dc243e","用两枚 M3×30 螺钉贯穿鞍座到底盘螺母，防止电机扭动。","不要挤压齿轮箱；先确认轴能自由转动。")
        motor=fuse(box(12,26,10,(66,side*31,23.4)),cyl(1.5,9.27,(66,side*44,AXLE_Z),(0,side,0)))
        add("motor_"+label,"FIT0094 · 6V / 50:1 电机 "+label,motor,"#b8b5aa","6 V、400 rpm、堵转 0.35 A；实际 PWM 和负载速度需标定。","后轴两电机分别驱动；镜像安装在接线上反向。","purchased","https://www.dfrobot.com.cn/goods-896.html","钢 / 黄铜")
        hub=cyl(8.75,5,(66,side*45.3,AXLE_Z),(0,side,0)).cut(cyl(1.5,7,(66,side*44.3,AXLE_Z),(0,side,0)))
        for dx,dz in [(6.35,0),(-6.35,0),(0,6.35),(0,-6.35)]: hub=hub.cut(cyl(1.25,7,(66+dx,side*44.3,AXLE_Z+dz),(0,side,0)))
        add("hub_"+label,"Pololu #1996 · 3 mm / M3 轮毂 "+label,hub,"#adb5c1","金属顶丝锁紧 D 轴；四孔半径 6.35 mm，M3。","把轴的扭矩传给打印轮圈，不依赖 PLA 压配孔。","purchased","https://www.pololu.com/product/1996/resources","铝")

    # Wheel designs in XY, axle on Z, then placed on both sides of the car.
    def wheel(front):
        rim=cyl(22,14).cut(cyl(18.2,16,(0,0,-1)))
        # Flat-bottom grooves: 40.8 mm seat diameter, standard 40 x 3 mm O-rings.
        for z in [3.5,10.5]:
            ring=cyl(24,3.4,(0,0,z-1.7)).cut(cyl(20.4,3.6,(0,0,z-1.8)))
            rim=rim.cut(ring)
        center=cyl(9.5,14 if front else 3)
        for angle in range(0,360,60):
            spoke=box(15,3.5,3,(12,0,1.5)).rotate((0,0,0),(0,0,1),angle)
            rim=fuse(rim,spoke)
        result=fuse(rim,center).cut(cyl(2.6 if front else 1.7,18,(0,0,-1)))
        if front:
            result=result.cut(cyl(4.1,4,(0,0,0))).cut(cyl(4.1,4,(0,0,10)))
        else: result=holes_z(result,[(6.35,0),(-6.35,0),(0,6.35),(0,-6.35)],3.3)
        return result.clean()
    for x,prefix,front in [(FRONT_X,"front",True),(REAR_X,"rear",False)]:
        w=wheel(front)
        for side,label in [(-1,"L"),(1,"R")]:
            world=w.rotate((0,0,0),(1,0,0),-90*side).translate((x,side*WHEEL_INNER,AXLE_Z))
            add(prefix+"_wheel_"+label,("05 · 前轮圈 " if front else "06 · 驱动轮圈 ")+label,world,"#c9253c","六辐打印轮圈；每轮两条 40×3 mm NBR O 形圈作轮胎。","橡胶接地，PLA 只承力；不得省掉轮胎在光滑桌面演示。",print_rotation=((1,0,0),90*side),print_note="轮圈平面朝下，轴孔竖直；4 壁、40% 填充；不要缩放。")
            for j,z in enumerate([3.5,10.5]):
                # Mounted O-ring cross section conservatively held circular for clearance checks.
                tire=cq.Solid.makeTorus(21.9,1.5,cq.Vector(x,side*(WHEEL_INNER+z),AXLE_Z),cq.Vector(0,1,0))
                add(f"tire_{prefix}_{label}_{j}","NBR 橡胶圈 · 40×3 mm",tire,"#14171c","提供抓地力；原始内径 40 mm、线径 3 mm，座径 40.8 mm。","每轮两条；装好后确认不脱槽。","purchased","采购条件：NBR 70A，内径 40 mm × 线径 3 mm；非外径 40 mm。","NBR")
            if front:
                for j,offset in enumerate([0,10]):
                    bearing=cyl(4,4,(x,side*(WHEEL_INNER+offset),AXLE_Z),(0,side,0)).cut(cyl(1.5,4,(x,side*(WHEEL_INNER+offset),AXLE_Z),(0,side,0)))
                    add(f"bearing_{label}_{j}","MR83ZZ · 3×8×4 mm 轴承",bearing,"#a1acb7","两只轴承承托每个前轮；内圈由螺钉和隔套固定。","轮圈转动，螺钉不转；不要把锁紧力压到外圈。","purchased","采购条件：MR83ZZ，内径 3 / 外径 8 / 厚 4 mm。","轴承钢")
                spacer=cyl(2.4,6,(x,side*(WHEEL_INNER+4),AXLE_Z),(0,side,0)).cut(cyl(1.7,6,(x,side*(WHEEL_INNER+4),AXLE_Z),(0,side,0)))
                add("bearing_spacer_"+label,"07 · 前轴承内隔套 "+label,spacer,"#b3bcc8","长度 6 mm，连接两轴承内圈，拧紧后轮圈仍可转。","若尺寸误差造成夹紧，换等尺寸金属隔套或按实物修配。",print_rotation=((1,0,0),90),print_note="轴孔竖直；100% 填充；试装后确认拧紧仍自由转动。")

    sections=[(-102,7,17),(-85,11,23),(-58,18,31),(-36,39,48),(-12,43,55),(25,41,52),(48,30,42),(78,20,34),(96,14,29)]
    outer=shell_loft(sections)
    inner_sections=[(-99,7.5,18),*sections[1:-1],(93,14.8,29.8)]
    shell=outer.cut(shell_loft(inner_sections,True))
    # Mounting bosses with top-loaded nut pockets; accessible from open bottom before closure.
    for x,y in MOUNTS:
        boss=cyl(5,7,(x,y,10.6))
        shell=fuse(shell,boss)
        shell=shell.cut(cyl(1.65,20,(x,y,7)))
        shell=shell.cut(cq.Workplane("XY",origin=(x,y,14.8)).polygon(6,6.7).extrude(4).val())
    # Rear axle clearances through both side walls.
    for side in [-1,1]:
        shell=shell.cut(box(31,46,32,(66,side*39,23.4)))
        # Sidepod cooling gills: through wall, away from battery / board fixings.
        for x in [0,9,18]: shell=shell.cut(box(3.4,18,6,(x,side*38,34)))
    # Microphone sound port over front nose, separate from motor noise at rear.
    shell=shell.cut(cyl(4.3,50,(-78,0,5)))
    # Real switch bodies are not tiny cylinders: reserve terminals and rectangular housing.
    for y in [-8,8]: shell=shell.cut(box(20,11,14,(91,y,20)))
    shell=shell.cut(box(22,12,4.4,(94,0,11.2)))
    for x in [89,95]: shell=shell.cut(cyl(3.7,3.5,(x,0,13)))
    # Wrench/nut access is separate from the collision checks on bare printed solids.
    for y in [-4,4]: shell=shell.cut(cyl(3.7,5,(-96,y,9.8)))
    for y in [-18,18]:
        shell=shell.cut(box(6.4,5.4,70,(89,y,35))).cut(box(18,12,7,(85,y,13)))
    add("body_shell","08 · ECHO 红色整流外壳",shell,"#e52b40","F1 风格鼻锥、侧箱和尾部；壳厚约 2.4 mm，四点可拆。","声孔在前鼻锥，避开后部电机；不是气动性能声明。",print_note="开口朝下；0.16–0.20 mm 层高、4 壁；启用仅接触热床的树状支撑，支撑从底部取出。先切片检查壳顶桥接和轴孔。")
    # Low-profile black dorsal canopy follows loft roof; cosmetic glue-on part, no safety role.
    canopy_wires=[]
    for x,w,b,h in [(-33,3,49,51),(-18,11,55,62),(9,12,55,65),(29,7,51,59),(42,2,47,49)]:
        canopy_wires.append(cq.Workplane("YZ",origin=(x,0,0)).polyline([(-w,b),(-w*.6,h),(w*.6,h),(w,b)]).close().val())
    canopy=cq.Solid.makeLoft(canopy_wires,ruled=True).translate((0,0,1))
    add("canopy","09 · 黑色座舱饰盖",canopy,"#171d27","可选的座舱造型，不承担传感或保护认证功能。","用薄双面胶装在壳顶；不覆盖麦克风孔。",print_rotation=((0,1,0),180),print_note="建议独立打印；切片中选最大平面贴床并少量支撑。饰件可不用，不影响运行。")
    # Front wing clears rotating wheels; through bolts at narrow nose.
    wingpts=[(-114,-51),(-104,-55),(-89,-53),(-86,-21),(-91,-12),(-91,12),(-86,21),(-89,53),(-104,55),(-114,51)]
    frontwing=polygon(wingpts,4.2,2.8)
    for side in [-1,1]:
        frontwing=fuse(frontwing,box(24,2.4,8,(-101,side*52,10.2)))
    frontwing=holes_z(frontwing,[(-96,-4),(-96,4)],3.3)
    add("front_wing","10 · 前翼",frontwing,"#202733","宽前翼明确 F1 轮廓，端板加厚 2.4 mm。","前轮前方留间隙；前翼不是碰撞保险杠。")
    rearwing=box(23,85,3,(99,0,56.5))
    for side in [-1,1]:
        rearwing=fuse(rearwing,box(23,2.4,12,(99,side*41.3,53)),box(4,3,32,(89,side*18,39)))
    # Two feet connect to bottom support, screwed to chassis from below.
    for y in [-18,18]: rearwing=fuse(rearwing,box(14,10,3,(86,y,11.5)))
    # connect posts all the way down to the feet
    for y in [-18,18]: rearwing=fuse(rearwing,box(4,3,12,(89,y,18)))
    rearwing=holes_z(rearwing,[(83,-18),(83,18)],3.3,bottom=7,h=8)
    add("rear_wing","11 · 后翼支架总成",rearwing,"#202733","尾翼与支柱一体；两点螺钉固定，装壳前安装。","轻量装饰翼，无下压力计算声明。",print_rotation=((0,1,0),180),print_note="尾翼上表面贴床，支柱向上；支脚局部需要树状支撑。")

    control=fuse(box(18,10,3,(93,0,11.5)),box(3,32,18,(100,0,19)))
    control=holes_z(control,[(89,0),(95,0)],3.3)
    for y,r in [(-8,3.2),(8,3.6)]: control=control.cut(cyl(r,6,(97,y,20),(1,0,0)))
    add("control_bracket","12 · 尾部电源 / ARM 面板",control,"#282e39","6.4 mm 电源开关孔、7.2 mm 常开按钮孔；在车尾直接操作。","总电源能断开电池；ARM 按钮只管软件使能。先核实开关外形与试片孔。",print_note="底脚朝下；横孔清孔。开关孔若不适合采购型号，修改参数重新导出，不能强行塞入。")
    for pid,y,r,label in [('power_switch',-8,3,'M6 面板式总电源开关'),('arm_button',8,3.5,'M7 面板式 ARM 常开按钮')]:
        body=box(16,9,12,(90.5,y,20)) if y<0 else cyl(4.5,16,(82.5,y,20),(1,0,0))
        s=fuse(body,cyl(r,4,(98.5,y,20),(1,0,0)),cyl(4,3,(102.5,y,20),(1,0,0)))
        add(pid,label,s,'#a3acba' if y<0 else '#d52b49','采购接口约束：本体含焊脚 ≤16深×9宽×12高 mm；M6螺纹，有效安装长度≥5mm；≥2 A / 12 V DC。' if y<0 else '常开自复位；M7螺纹有效安装长度≥5mm，本体≤Ø9×16深mm；GPIO32 与 GND 短接。','车尾外露可操作；按商家尺寸图选型，通用MTS/PBS名字不能保证外形相同。','purchased','采购条件模型，不是厂家 CAD；商家尺寸需核对。','金属 / 塑料')

    # Hex-nut + small washer envelopes, not thread-strength or tool-path certification.
    for label,pts,z in [('front_wing',[(-96,-4),(-96,4)],10),('rear_wing',[(83,-18),(83,18)],13),('control_bracket',[(89,0),(95,0)],13)]:
        for x,y in pts:
            env=cyl(3.4,3.0,(x,y,z)).cut(cyl(1.65,3.0,(x,y,z)))
            for pid in ['body_shell','rear_wing','control_bracket']:
                overlap=env.intersect(SHAPES[pid]).Volume()
                assert overlap<.05, f'Nut access collision {label}/{pid}: {overlap}'

    # Battery holder: dimensioned procurement envelope, not an invented SKU.
    bat=box(60,64,17,(0,0,19))
    add("battery_holder","4×AA 镍氢电池盒（最大 60×64×17 mm）",bat,"#252a32","四节同品牌同容量 NiMH，标称 4.8 V；电机由电池直接供电。","低重心；扎带固定，不依赖未知孔位。","purchased","采购接口条件：4×AA 串联平铺盒，含线，外尺寸不大于 60×64×17 mm；不可换两层盒。","ABS / NiMH")
    pcb=box(48.26,27.94,1.6,(0,0,33.8))
    pcb=fuse(pcb,box(25.4,18,3.1,(10,0,36.15)),box(5.5,8,3.2,(-23,0,36.2)))
    for y in [-12.7,12.7]: pcb=fuse(pcb,box(46,2.54,8,(0,y,32.4)))
    add("esp32","ESP32-DevKitC V4 · WROOM-32E",pcb,"#183e36","主板 48.26×27.94 mm；GPIO34 读声音，GPIO25/26/27/14 控制驱动。","支架上方居中，底部排针从托架窗口穿过，USB 在前端。","purchased","https://dl.espressif.com/dl/schematics/esp32_devkitc_v4_dimensions.pdf","FR4 / 铜")
    driver=fuse(box(20,19.5,1.6,(43,-7,14)),box(8,6,2,(43,-7,15.8)))
    add("driver","DFRobot DRI0044 · TB6612FNG",driver,"#184942","3.3V 逻辑；双路各 1.2 A 连续上限，实际散热依安装。","靠近后轴缩短电机线，与前方麦克风信号线分开。","purchased","https://wiki.dfrobot.com/dri0044/","FR4")
    regulator=fuse(box(17,13,1.6,(-44,0,14)),box(8,8,3,(-44,0,16.3)))
    add("regulator","DFRobot DFR0569 · 5V 升降压",regulator,"#235349","仅给 ESP32 供 5V，不给电机供电；无线功能关闭。","电池电压上下变化时维持主控供电；需实测启动瞬态。","purchased","https://www.dfrobot.com/product-1766.html","FR4")
    mic=fuse(box(20,14,1.6,(-77,0,14)),cyl(3,6.2,(-78,0,14.8)))
    add("microphone","Adafruit #1063 · MAX4466",mic,"#237269","3.3V 供电，OUT 为带偏置的模拟声波；软件去除均值后计算 RMS。","鼻锥内用软泡棉固定、正对声孔，与电机机械隔离。","purchased","https://www.adafruit.com/product/1063","FR4 / 麦克风")

    # Coupon is deliberately not part of car assembly.
    coupon=box(62,25,4,(0,0,2))
    for x,d in [(-22,3.2),(-12,3.3),(-2,3.4),(11,8.1),(24,8.2)]: coupon=coupon.cut(cyl(d/2,8,(x,0,-2)))
    export_mesh(coupon,OUT/"print/00_fit_coupon.stl")

def finalize():
    assembly=cq.Assembly(name="ECHO_F1_v1")
    for p in PARTS:
        color=p['color']; rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
        assembly.add(SHAPES[p['id']],name=p['id'],color=cq.Color(*rgb))
    assembly.save(str(OUT/"ECHO-F1-assembly.step"))
    # Check actual BRep intersections, not just attractive renders.
    conflicts=[]; intentional=[]
    ids=list(SHAPES)
    allowed=set()
    # tires are elastically stretched into grooves; canopy adhesive contact is simplified.
    for a in ids:
        for b in ids:
            if a.startswith('tire_') and '_wheel_' in b and a.split('_')[1:3]==b.split('_')[0:1]+b.split('_')[2:3]: allowed.add(frozenset((a,b)))
    for i,a in enumerate(ids):
        ba=bnd(SHAPES[a])
        for b in ids[i+1:]:
            bb=bnd(SHAPES[b])
            if any(ba['max'][k]<=bb['min'][k]+1e-5 or bb['max'][k]<=ba['min'][k]+1e-5 for k in range(3)): continue
            v=SHAPES[a].intersect(SHAPES[b]).Volume()
            if v>.02:
                item={"a":a,"b":b,"overlapMm3":round(v,4)}
                (intentional if frozenset((a,b)) in allowed else conflicts).append(item)
    checks={"generatedAt":datetime.now(timezone.utc).isoformat(),"cadquery":cq.__version__,"units":"mm","brepAndStl":"PASS","physicalTest":"NOT_RUN","interferenceConflicts":conflicts,"elasticTireSeating":intentional,"limitations":["Purchased items are source-dimensioned reference geometry, not supplier CAD.","Fasteners, cable ties, foam, connectors and wire bend radii need physical fit checks.","No structural FEA, slicing or physical sound/traction test has been performed by this script."]}
    (OUT/"checks/geometry.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    manifest={"schemaVersion":1,"id":"echo-f1-v1","title":"ECHO F1 · 声控方程式","authoring":"Authored parametric CAD; not a Qwen-generated benchmark","units":"mm","parts":PARTS,"cadParts":CAD,"printParts":PRINTS,"checks":checks,"generatedAt":checks['generatedAt']}
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('INTERFERENCE',json.dumps(conflicts,ensure_ascii=False),flush=True)

if __name__=='__main__':
    make_design(); finalize()
