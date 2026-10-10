"""ECHO F1 mainland procurement redesign. Units: mm.

Independent build; NEVER overwrites v1 or teammate library. Purchased parts are
reference envelopes, not supplier CAD. Run from the repository root.
"""
import json
from datetime import datetime, timezone
import echo_f1 as g
from echo_f1 import cq, box, cyl, fuse, holes_z, polygon, bnd, add, export_mesh

BUILD_ID = 'echo-f1-cn-v2'
g.OUT = g.ROOT / 'builds' / BUILD_ID
OUT = g.OUT
for d in ['', 'print', 'step', 'assembly-parts', 'firmware', 'checks']:
    (OUT/d).mkdir(parents=True, exist_ok=True)
RED, BLACK = '#e5293e', '#242832'
FRONT, REAR = -85, 92
MOTOR_Z, FRONT_Z = 21, 23.4
MOUNT = [(-50,-66),(-50,66),(50,-66),(50,66)]
JOIN = [(-10,-43),(10,-43),(-10,43),(10,43)]
LEGS = [(-55,-41),(-55,41),(73,-41),(73,41)]
MOTOR_SOURCE = 'https://wiki.dfrobot.com.cn/026_%E9%87%91%E5%B1%9E%E5%87%8F%E9%80%9F%E7%94%B5%E6%9C%BA'

def make_design():
    # Split floor with separate underside splice plates, not a cosmetic seam.
    pts=[(-132,-13),(-113,-24),(-71,-37),(-59,-59),(-30,-62),(52,-64),
         (79,-53),(107,-37),(132,-22),(132,22),(107,37),(79,53),(52,64),
         (-30,62),(-59,59),(-71,37),(-113,24),(-132,13)]
    floor=polygon(pts,8,3)
    for x,y in MOUNT:
        floor=fuse(floor,box(18,18,3,(x,y,9.5)))
    # Fixed front axle brackets with triangular reinforcement.
    floor=fuse(floor,box(16,122,3,(FRONT,0,9.5)))
    for side in [-1,1]:
        upright=box(16,6,22,(FRONT,side*58,22))
        upright=upright.cut(cyl(1.65,15,(FRONT,side*50,FRONT_Z),(0,side,0)))
        rib=cq.Workplane('YZ',origin=(FRONT-5,0,0)).polyline([(side*26,11),(side*55,11),(side*55,26)]).close().extrude(10).val()
        floor=fuse(floor,upright,rib)
        # Through the rib as well as the upright; clear the inside screw head.
        floor=floor.cut(cyl(1.65,40,(FRONT,side*40,FRONT_Z),(0,side,0)))
        floor=floor.cut(cyl(3.4,15,(FRONT,side*40,FRONT_Z),(0,side,0)))
    # Battery maximum envelope 120 x 65 x 20, on foam at z=13.
    for y in [-34.5,34.5]:floor=fuse(floor,box(124,2,4,(18,y,13)))
    for x in [-44,80]:floor=fuse(floor,box(2,71,4,(x,0,13)))
    for x in [-10,40]:
        for y in [-37,37]:floor=floor.cut(box(7,3,12,(x,y,10)))
    # Four struts carry the removable electronics bridge above the batteries.
    for x,y in LEGS:
        p=cyl(4.5,28,(x,y,11))
        p=p.cut(cyl(1.65,40,(x,y,6)))
        nut=cq.Workplane('XY',origin=(x,y,34.5)).polygon(6,6.7).extrude(2.7).val()
        p=p.cut(fuse(nut,box(11,5.9,2.7,(x+(-4 if x<0 else 4),y,35.85))))
        floor=fuse(floor,p)
    # Motor bracket bolt rails are outside the battery area.
    for side in [-1,1]:floor=fuse(floor,box(34,34,3,(REAR,side*54,9.5)))
    motor_holes=[(REAR+dx,side*54) for dx in [-10,10] for side in [-1,1]]
    floor=holes_z(floor,JOIN+MOUNT+motor_holes+[(124,-18),(124,18)],3.4)
    # Cable-tie windows for the buck and control button; no PCB hole assumptions.
    for x in [-102,-68]:
        for y in [-24,24]:floor=floor.cut(box(4,3,12,(x,y,10)))
    for x in [112,126]:floor=floor.cut(box(3,9,12,(x,0,10)))
    for label,x in [('front',-160.2),('rear',160.2)]:
        half=floor.intersect(box(320,400,140,(x,0,40)))
        add('chassis_'+label,'01 · 分体底盘 '+('前' if label=='front' else '后'),half,BLACK,
            '承力底盘；中缝 0.4 mm，下方两块桥板用 M3 螺钉连接。','分成两件，保持实际比例，避免把整车缩小来迁就热床。')
    for y,label in [(-43,'L'),(43,'R')]:
        plate=holes_z(box(32,18,4,(0,y,6)),[(-10,y),(10,y)],3.4)
        for x in [-10,10]:plate=plate.cut(cq.Solid.makeCone(3.4,1.7,1.7,cq.Vector(x,y,4),cq.Vector(0,0,1)))
        add('splice_'+label,'02 · 底盘拼接桥 '+label,plate,BLACK,'4 mm 厚连接板；底部沉头孔用 M3×12 沉头螺钉。','位于电池两侧，螺母不会顶住电池盒；沉头不应突出到地面。')
    bridge=cq.Workplane('XY').box(138,92,3).edges('|Z').fillet(5).val().translate((9,0,40.5))
    bridge=holes_z(bridge,LEGS,3.4,bottom=35,h=10)
    # Open slots accommodate unknown header underside and elastic fixing straps.
    for y in [-18,18]:bridge=bridge.cut(box(53,6,8,(16,y,41)))
    for x in [-46,0,32,60]:
        for y in [-30,30]:bridge=bridge.cut(box(4,12,8,(x,y,41)))
    add('electronics_bridge','03 · 通用免焊电子托架',bridge,BLACK,
        '主板与声音模块用绝缘垫、扎带固定；不假定第三方板子的安装孔一致。','取下 4 枚 M3×10 可换电池；排针下方留空。')

    for side,label in [(-1,'L'),(1,'R')]:
        saddle=box(28,34,15.5,(REAR,side*54,18.75))
        saddle=saddle.cut(box(12.8,40,22,(REAR,side*54,27)))
        saddle=holes_z(saddle,[(REAR-10,side*54),(REAR+10,side*54)],3.4)
        clamp=holes_z(box(28,9,3,(REAR,side*54,28)),[(REAR-10,side*54),(REAR+10,side*54)],3.4)
        add('motor_saddle_'+label,'04 · N20 通用鞍座 '+label,saddle,BLACK,
            '12.8 mm 宽槽适配 12×10 mm N20，开口允许 26–32 mm 本体长度；薄泡棉消隙。','不用型号不明的齿轮箱螺纹，也不需要焊电机端子。')
        add('motor_clamp_'+label,'05 · 电机压条 '+label,clamp,RED,'两枚 M3×30 贯穿底盘固定。','只夹电机壳，不挤压轴与插座；支架不是任意电机通用件。')
        motor=fuse(box(12,28,10,(REAR,side*54,MOTOR_Z)),
                   cyl(1.5,9.27,(REAR,side*68,MOTOR_Z),(0,side,0)))
        add('motor_'+label,'6V · 带 PH2.0 接口 N20 '+label,motor,'#b8b39a',
            '参考 DFRobot 带接口 50:1 / 440 rpm / 堵转 0.35 A 版本；不能将参数套到同名裸电机。',
            '3 mm D 轴直接配 42×19 mm 成品轮；卖家须确认带引线和抑噪电路。','purchased',MOTOR_SOURCE,'钢 / 黄铜')
        # Purchased rear wheel pair: tire + hub reference, no imported set-screw hub.
        axis=(0,side,0); origin=(REAR,side*72,MOTOR_Z)
        tire=cyl(21,19,origin,axis).cut(cyl(17.5,19,origin,axis))
        hub=cyl(17.5,19,origin,axis).cut(cyl(1.6,19,origin,axis))
        for angle in range(0,360,60):
            x=REAR+11*__import__('math').cos(__import__('math').radians(angle))
            z=MOTOR_Z+11*__import__('math').sin(__import__('math').radians(angle))
            hub=hub.cut(cyl(3.2,19,(x,side*72,z),axis))
        add('rear_tire_'+label,'42×19 成品驱动轮 · 橡胶 '+label,tire,'#131820','采购成品轮组的一部分，不打印。','轮、3 mm D 轴和孔深必须配套购买，禁止强敲轴。','purchased','采购规格：N20 配套 42×19 mm 橡胶轮，3 mm D 孔，至少 5 mm 有效轴配合。','橡胶')
        add('rear_hub_'+label,'42×19 成品驱动轮 · 轮芯 '+label,hub,'#414857','成品轮自带轮芯，不再购买 Pololu 金属轮毂。','图形为配套轮尺寸参考，不代表某家店的实际辐条。','purchased','与驱动电机同店配套确认；轮宽≤19，直径42，内侧不得擦支架。','ABS')

    # Retain already-selected 693ZZ and 40x3 O rings, only at the free front wheels.
    for side,label in [(-1,'L'),(1,'R')]:
        w=cyl(22,14).cut(cyl(18.2,14))
        for z in [3.5,10.5]:w=w.cut(cyl(24,3.4,(0,0,z-1.7)).cut(cyl(20.4,3.4,(0,0,z-1.7))))
        center=cyl(9.5,14)
        for a in range(0,360,60):w=fuse(w,box(15,3.5,3,(12,0,1.5)).rotate((0,0,0),(0,0,1),a))
        w=fuse(w,center).cut(cyl(2.6,16,(0,0,-1))).cut(cyl(4.1,4)).cut(cyl(4.1,4,(0,0,10)))
        world=w.rotate((0,0,0),(1,0,0),-90*side).translate((FRONT,side*64,FRONT_Z))
        add('front_wheel_'+label,'06 · 前轮圈 '+label,world,RED,'双 693ZZ 轴承；两条 40×3 mm NBR 圈接地。','已有规格可沿用，前轮轴心比后轮高 2.4 mm，使四轮接地。',print_rotation=((1,0,0),90*side))
        for j,off in enumerate([3.5,10.5]):
            tire=cq.Solid.makeTorus(21.9,1.5,cq.Vector(FRONT,side*(64+off),FRONT_Z),cq.Vector(0,1,0))
            add(f'tire_front_{label}_{j}','NBR · 内径40×线径3',tire,'#131820','前轮防滑圈；每轮2条。','沿用购物车规格，10只一包有余量。','purchased','NBR70，内径40×线径3 mm。','NBR')
        for j,off in enumerate([0,10]):
            bearing=cyl(4,4,(FRONT,side*(64+off),FRONT_Z),(0,side,0)).cut(cyl(1.5,4,(FRONT,side*(64+off),FRONT_Z),(0,side,0)))
            add(f'bearing_{label}_{j}','693ZZ · 3×8×4 mm',bearing,'#b4bcc7','两只轴承支承每个前轮。','按尺寸选 693ZZ；旧稿 MR83ZZ 名称不适用于 3×8×4。','purchased','693ZZ 3×8×4 mm；已有购物车规格。','轴承钢')
        spacer=cyl(2.4,6,(FRONT,side*68,FRONT_Z),(0,side,0)).cut(cyl(1.7,6,(FRONT,side*68,FRONT_Z),(0,side,0)))
        add('bearing_spacer_'+label,'07 · 前轮内隔套 '+label,spacer,'#bcc6d4','仅压内圈；长6 mm。','装后若发紧，按实际轴承堆叠调整，不能强行拧紧。',print_rotation=((1,0,0),90))

    sections=[(-134,9,23),(-120,20,36),(-90,32,44),(-70,44,52),(-51,60,60),
              (-30,65,63),(20,69,64),(55,64,61),(80,57,53),(107,31,40),(130,22,36)]
    def loft(rows,inner=False):
        wires=[]
        for x,w,h in rows:
            if inner:w-=2.4;h-=2.4
            base=10.8 if inner else 11.8
            points=[(-w,base),(-w,base+5),(-w*.88,h-7),(-w*.55,h),(w*.55,h),(w*.88,h-7),(w,base+5),(w,base)]
            wires.append(cq.Workplane('YZ',origin=(x,0,0)).polyline(points).close().val())
        return cq.Solid.makeLoft(wires,ruled=True)
    shell=loft(sections).cut(loft([(-131,11,26),*sections[1:-1],(127,23,41)],True))
    for x,y in MOUNT:
        shell=fuse(shell,box(16,18,3,(x,y,13.3)))
    shell=holes_z(shell,MOUNT,3.4)
    for side in [-1,1]:
        shell=shell.cut(box(46,72,32,(REAR,side*56,21)))
        # Front axle must pass freely through shell; not hidden interpenetration.
        shell=shell.cut(box(20,134,26,(FRONT,0,23)))
        for x in [15,27,39]:shell=shell.cut(box(4,32,9,(x,side*61,48)))
    for x in [-54,-48,-42]:shell=shell.cut(box(2.5,16,60,(x,0,68)))
    shell=shell.cut(box(200,400,160,(208,0,50))) # rear finger access / loom exit
    for label,x in [('front',-160.25),('rear',160.25)]:
        part=shell.intersect(box(320,400,160,(x,0,50)))
        add('shell_'+label,'08 · 红色分段外壳 '+('前' if label=='front' else '后'),part,RED,
            '约2.4 mm 壳壁、可拆侧耳、真实轴孔和通风口。','红黑 F1 风格；不声称空气动力收益。两段独立安装，不遮挡传感器声孔。',
            print_note='开口向下；0.16–0.20 mm 层高，4壁；树状支撑仅接触热床，拆支撑后试配。')
    canopy=cq.Solid.makeLoft([cq.Workplane('YZ',origin=(x,0,0)).polyline([(-w,b),(-w*.55,h),(w*.55,h),(w,b)]).close().val() for x,w,b,h in [(-20,3,55,66),(0,14,55,76),(30,13,55,75),(49,2,55,65)]],ruled=True)
    # Conforming underside, not a floating showpiece requiring thick mystery pads.
    canopy=canopy.cut(loft(sections).translate((0,0,.5)))
    add('canopy','09 · 黑色座舱盖',canopy,'#121823','可选外观饰件，薄双面胶固定，不是承力件。','远离声孔和后部手指入口；不影响换电池。',print_note='切片选最大平面贴床，使用少量树状支撑；可省略此装饰件。')
    wing=box(27,146,3,(-135,0,6.5))
    wing=fuse(wing,box(14,22,2,(-127,0,9)))
    for s in [-1,1]:wing=fuse(wing,box(27,2.5,13,(-135,s*71.75,12)))
    wing=wing.cut(box(16,24,3,(-127,0,9.5)))
    # Front wing clips/ties to the nose through real paired slots.
    for y in [-6,6]:wing=wing.cut(box(3,2.8,12,(-129,y,7)))
    add('front_wing','10 · 前翼',wing,BLACK,'扎带固定在鼻锥下方；碰撞后可单独更换。','翼底距地5 mm，切勿缩放；不是护栏。')
    rear=box(23,134,3,(126,0,65.5))
    for s in [-1,1]:
        rear=fuse(rear,box(23,2.5,14,(126,s*65.75,60)),box(4,4,53,(125,s*18,37.5)),box(17,12,3,(124,s*18,12.5)))
    rear=holes_z(rear,[(124,-18),(124,18)],3.4,bottom=7,h=10)
    add('rear_wing','11 · 尾翼',rear,BLACK,'两枚 M3×10 固定底盘；翼柱与翼面一体。','车尾预留总开关和手动停机入口。',print_rotation=((0,1,0),180))

    battery=box(120,65,20,(18,0,23))
    add('battery_holder','8×AA · 带线电池盒',battery,'#242b34','8节同型号NiMH，标称9.6V，成品串联平铺盒≤120×65×20。','用2 mm绝缘泡棉与扎带固定；电池取出充电。','purchased','采购最大包络条件，不是通用8AA盒的保证尺寸。','ABS / NiMH')
    regulator=fuse(box(66,40,1.6,(-80,0,15.8)),box(46,31,16,(-80,0,24.6)))
    add('regulator','DFR0379 · 5.5V 降压模块',regulator,'#23483e','LM2596S带电压显示与接线端子；先空载调到5.5V，再接主板。','放在电池前方，留通风空间。此66×40×20为保守采购包络，非已核对板图。','purchased','https://www.dfrobot.com.cn/goods-1351.html','FR4')
    pcb=fuse(box(47,38.5,1.6,(16,0,46)),box(16,18,3,(23,0,48.3)),box(8,20,10,(-3.5,0,51.8)))
    for y in [-17,17]:pcb=fuse(pcb,box(34,2.5,8,(16,y,45)))
    add('esp32','DFR1063 · Romeo mini ESP32-C3',pcb,'#17625a','集成双路电机驱动，1.7A/路；GPIO3采样，1/0与10/2控制电机。','沿用已入购物车的主板；不再购买独立ESP32和DRI0044。','purchased','https://wiki.dfrobot.com/dfr1063/','FR4')
    mic=fuse(box(30,22,1.6,(-47,0,44.8)),cyl(4.9,7,(-51,0,45.6)),box(5,9,5,(-34.5,0,48.1)))
    add('microphone','DFR0034 · Gravity 声音强度',mic,'#246251','买支持3.3V的V2成品板及Gravity转杜邦母头线；不是裸麦克风。','上层托架前端隔振安装，软件读强度，不沿用MAX4466波形RMS算法。','purchased','https://wiki.dfrobot.com/dfr0034/','FR4')
    switch=box(18,10,12,(116,0,19))
    add('power_switch','带线总开关 + 串联保险座',switch,'#202b35','成品带线开关；电源线中预接1A慢熔保险座，接线端子拼接。','尾部直接操作，不使用待焊开关；包络≤18×10×12，若更大可外置固定。','purchased','采购包络条件：开关≥2A/12V DC；保险座可放电池前方空隙，未单独建模。','ABS')
    button=box(15,12,7,(111,-11,18.5))
    add('arm_button','免焊常开按键模块',button,'#305d52','已焊2.54排针常开干接点；只连接GPIO6和GND。','板件用绝缘双面胶固定在车尾，留手指空间。','purchased','采购包络≤15×12×7；只要干接点型，不接5V模块输出。','FR4')

    coupon=box(62,25,4,(0,0,2))
    for x,d in [(-22,3.2),(-12,3.3),(-2,3.4),(11,8.1),(24,8.2)]:coupon=coupon.cut(cyl(d/2,8,(x,0,-2)))
    export_mesh(coupon,OUT/'print/00_fit_coupon.stl')

def finalize():
    assembly=cq.Assembly(name='ECHO_F1_CN_V2')
    for p in g.PARTS:
        rgb=[int(p['color'][i:i+2],16)/255 for i in (1,3,5)]
        assembly.add(g.SHAPES[p['id']],name=p['id'],color=cq.Color(*rgb))
    assembly.save(str(OUT/'ECHO-F1-assembly.step'))
    conflicts=[];intentional=[]
    items=list(g.SHAPES.items())
    for i,(a,sa) in enumerate(items):
        ba=bnd(sa)
        for b,sb in items[i+1:]:
            bb=bnd(sb)
            if any(ba['max'][k]<=bb['min'][k]+1e-5 or bb['max'][k]<=ba['min'][k]+1e-5 for k in range(3)):continue
            v=sa.intersect(sb).Volume()
            if v>.02:
                row={'a':a,'b':b,'overlapMm3':round(v,4)}
                elastic=a.startswith('front_wheel_') and b.startswith('tire_front_'+a[-1]+'_')
                (intentional if elastic else conflicts).append(row)
    checks={'generatedAt':datetime.now(timezone.utc).isoformat(),'cadquery':cq.__version__,'units':'mm','brepAndStl':'PASS',
        'physicalTest':'NOT_RUN','interferenceConflicts':conflicts,'elasticTireSeating':intentional,
        'limitations':['Purchased geometry is a reference envelope, not measured stock.','Fasteners, foam, connector bodies and complete wire harness require fit checks.','No physical, fatigue, acoustic or slicing test is implied.']}
    (OUT/'checks/geometry.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    bb=bnd(cq.Compound.makeCompound(list(g.SHAPES.values())))
    dims=[round(b-a,2) for a,b in zip(bb['min'],bb['max'])]
    m={'schemaVersion':1,'id':BUILD_ID,'title':'ECHO F1 · 大陆易装版 V2','authoring':'Authored parametric CAD; not an inference benchmark',
       'units':'mm','parts':g.PARTS,'cadParts':g.CAD,'printParts':g.PRINTS,'checks':checks,'generatedAt':checks['generatedAt'],
       'coverPartIds':['shell_front','shell_rear','canopy'],'dimensionsMm':dims,'packageStatus':'CAD_GENERATED_NOT_PACKAGED'}
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
    print('DIMENSIONS',dims,'INTERFERENCE',json.dumps(conflicts),flush=True)
    if conflicts:raise RuntimeError('Resolve CAD interference before packaging')

if __name__=='__main__':make_design();finalize()
