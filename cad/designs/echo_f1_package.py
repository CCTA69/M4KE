"""Add the reproducible build handbook, BOM, wiring, calculations and firmware.
Only run after echo_f1.py completed successfully. Does not bless physical tests.
"""
from pathlib import Path
import csv,hashlib,html,json,math,shutil,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'builds/echo-f1-v1'
M=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
assert not M['checks']['interferenceConflicts'], 'Resolve CAD conflicts before packaging.'

BOM=[]
def buy(name,qty,spec,budget,url=''):
    BOM.append(dict(name=name,qty=qty,spec=spec,budgetCny=budget,url=url,priceStatus='BUDGET_ALLOCATION_NOT_LIVE_QUOTE'))
buy('ESP32-DevKitC V4',1,'乐鑫 WROOM-32E / 4 MB / 38 针，已焊排针；不是裸模组或 C3/S3',45,'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html')
buy('DFRobot DRI0044',1,'TB6612FNG 双路驱动，20×19.5 mm；DIR/PWM 四控制线版本',25,'https://wiki.dfrobot.com/dri0044/')
buy('Adafruit #1063',1,'MAX4466 可调增益；不是 MAX9814 自动增益',60,'https://www.adafruit.com/product/1063')
buy('DFRobot FIT0094',2,'6 V / 50:1 / 400 rpm / 3 mm D 轴；电机本体先核对 12×10 mm 截面、约 26 mm 长',26,'https://www.dfrobot.com.cn/goods-896.html')
buy('DFRobot DFR0569',1,'3–15 V 输入，固定 5 V，600 mA 上限；17×13 mm；仅供主控',20,'https://www.dfrobot.com/product-1766.html')
buy('Pololu #1996 轮毂（2只装）',1,'3 mm 轴，四个 M3 孔半径 6.35 mm，外径17.5 / 厚5 mm；含顶丝',80,'https://www.pololu.com/product/1996/resources')
buy('NBR O形圈',10,'内径40 mm × 线径3 mm，约70A；车上8条、备用2条',1)
buy('MR83ZZ 轴承',4,'3×8×4 mm，不是 MR83 开口或 MR83 法兰型',2)
buy('AA 镍氢电池',4,'同品牌同容量1.2 V，建议1900–2500 mAh；不用14500锂电池',10)
buy('镍氢专用充电器',1,'支持所购AA NiMH；电池取出充电，车上无充电电路',35)
buy('4×AA 串联平铺电池盒',1,'最大60×64×17 mm，带线；先让商家确认外尺寸，不买双层盒',8)
buy('电源开关',1,'M6面板螺纹，有效安装长度≥5mm；含焊脚≤16深×9宽×12高mm，≥2 A/12 V DC；按商家图纸，不仅按MTS名称购买',5)
buy('ARM 常开按钮',1,'M7面板螺纹，有效安装长度≥5mm；含焊脚≤Ø9×16深mm，常开自复位；买前核对图纸',5)
buy('保险丝及绝缘座',1,'1 A慢熔，串在电池正极近电池处；额外买2只备用',7)
buy('电阻电容 / 小洞洞板',1,'10 kΩ×2，100 kΩ×1，100 nF×2，470 µF/10 V×1，100 µF/10 V×1；洞洞板≤12×12 mm或绝缘线束',8)
buy('多股软线与接插件',1,'22 AWG电源/电机，26 AWG信号；2.54 mm母头、JST或同等防反插接头；不得用松动杜邦线供电机',15)
buy('M3 紧固件套装',1,'M3×6:8；×8:4；×10:6；×12:4；×30:6；M3螺母/尼龙锁紧螺母/垫片各20；前翼底部优先低头螺钉；前轴小外径垫片',20)
buy('前轴外隔套',2,'内径3.2 / 外径≤5 / 长2 mm，尼龙或金属；夹轴承内圈',1)
buy('扎带、热缩管与绝缘胶带',1,'2.5 mm扎带≥10，热缩管，非导电双面胶',8)
buy('PLA 红/黑耗材份额',1,'建议备料300 g（含支撑、试片和余量，并非预测用量）；实际以切片器为准',25)
buy('Micro-USB数据线',1,'数据线，不是仅充电线',6)
buy('闭孔软泡棉',1,'2–3 mm、非导电；麦克风隔振/电路板垫高，勿封声孔',4)
total=sum(p['qty']*p['budgetCny'] for p in BOM)

P={p['id']:p for p in M['parts']}
WIRES=[]
def wire(pid,a,ta,b,tb,kind,color,awg,note=''):
    # Logical connections only. Display routing has separate CAD-bound evidence;
    # unknown real pin locations must never fall back to component centres.
    WIRES.append(dict(id=pid,from_={'partId':a,'terminal':ta},to={'partId':b,'terminal':tb},kind=kind,color=color,wireAwg=awg,routingStatus='MISSING_ANCHORS',note=note))
wire('W01','battery_holder','+ → F1 1A慢熔','power_switch','COM 中脚','power','#ff5264',22,'保险丝尽量靠近电池，所有裸接头热缩绝缘。')
wire('W02','power_switch','ON 外脚','driver','VM','power','#ff5264',22,'另一外脚不接并绝缘；万用表确认ON/OFF。')
wire('W03','power_switch','ON 外脚','regulator','Vi+','power','#ff5264',22)
wire('W04','battery_holder','−','driver','GND（功率）','ground','#8091a8',22)
wire('W05','battery_holder','−','regulator','Vi−','ground','#8091a8',22)
wire('W06','regulator','Vo+ / 5V','esp32','5V','power','#ff8369',22,'先用万用表测到约5V，再接主板。USB与此供电互斥。')
wire('W07','regulator','Vo−','esp32','GND','ground','#8091a8',22)
wire('W08','esp32','3V3','driver','VCC','power','#ffb56b',26,'逻辑VCC，不是电机VM。')
wire('W09','esp32','GND','driver','GND（逻辑）','ground','#8091a8',26)
wire('W10','esp32','3V3','microphone','VCC','power','#ffb56b',26,'禁止给麦克风5V后把OUT直接送ESP32。')
wire('W11','esp32','GND','microphone','GND','ground','#8091a8',26,'OUT与GND并行或轻绞，远离电机线。')
wire('W12','microphone','OUT','esp32','GPIO34','signal','#60d1bc',26,'GPIO34对地接100kΩ；断开传感器时降低悬空误触发风险。')
wire('W13','esp32','GPIO25','driver','DIR1','signal','#709dff',26)
wire('W14','esp32','GPIO26','driver','PWM1','signal','#ffc35d',26,'PWM1对地10kΩ，保证复位时输出低。')
wire('W15','esp32','GPIO27','driver','DIR2','signal','#c999ff',26)
wire('W16','esp32','GPIO14','driver','PWM2','signal','#65cfe0',26,'PWM2对地10kΩ，保证复位时输出低。')
wire('W17','driver','M1+','motor_L','+','motor','#f8a56a',22,'在电机两个端子间焊100nF；引脚尽量短。')
wire('W18','driver','M1−','motor_L','−','motor','#bf864d',22)
wire('W19','driver','M2+','motor_R','+','motor','#daa4e9',22,'在电机两个端子间焊100nF；先抬轮确认方向。')
wire('W20','driver','M2−','motor_R','−','motor','#8e68ba',22)
wire('W21','esp32','GPIO32','arm_button','A','signal','#e9d47b',26)
wire('W22','arm_button','B','esp32','GND','ground','#8091a8',26)
for w in WIRES:w['from']=w.pop('from_')

STEPS=[]
def step(title,ids,text,checks,tools):
    i=len(STEPS)+1
    STEPS.append(dict(id=f'S{i}',title=title,partIds=ids,requires=[f'S{i-1}'] if i>1 else [],text=text,checks=checks,tools=tools))
step('先试公差，再打印',['chassis'],
     '先打印00_fit_coupon：M3孔为3.2/3.3/3.4 mm，轴承孔为8.1/8.2 mm。挑能装入且不过松的尺寸；轴承不能用锤子硬敲。正式件用PLA、0.4 mm喷嘴、4道壁。核对打印底盘长199 mm，不能自动缩放。',
     ['M3螺钉能穿过3.3 mm孔','8 mm轴承与8.2 mm孔试配完成','整车长件适合实际热床，所有零件按100%打印'], '游标卡尺、M3螺钉、MR83ZZ轴承')
step('底盘、前翼与尾部骨架',['front_wing','rear_wing','control_bracket'],
     '前翼从底盘下方装，2×M3×10配螺母；尾翼底脚放在底盘上，2×M3×10由下向上配螺母，螺母位于柱子前方。尾部控制面板同样用2×M3×10由下向上配螺母。螺钉先松装后均匀拧紧，不让PLA变白开裂。',
     ['底盘平直，前翼打印面设计间隙4.2 mm；螺钉头会再降低间隙，装好后实测不得刮地','尾翼与后轴区域不相碰'], 'M3×10×6、M3螺母×6、匹配螺丝刀、小扳手')
step('安装后轴电机',['motor_saddle_L','motor_saddle_R','motor_L','motor_R','motor_clamp_L','motor_clamp_R'],
     '两个电机轴朝外，电机端面在距中心线44 mm处。先放鞍座再放电机，垫薄软片消除松动；压条用4×M3×30贯穿底盘并配螺母。不要压坏齿轮箱或堵住电机散热孔。',
     ['两根轴平行，轴心设计高度23.4 mm','电机固定后轴仍可轻松转动','端子与底盘、金属螺钉不接触'], 'M3×30×4、M3螺母×4、薄绝缘软垫')
step('后轮与金属轮毂',['hub_L','hub_R','rear_wheel_L','rear_wheel_R',*[p for p in P if p.startswith('tire_rear')]],
     '每个轮圈装两条40×3 mm橡胶圈。四枚M3×6将轮圈3 mm厚中心盘锁到#1996轮毂；螺钉进入铝件约3 mm。轮毂先装在电机轴上，内侧距车中心45.3 mm，顶丝顶在D轴平面，确认不擦电机面后锁紧。',
     ['橡胶圈坐在两条槽内，不扭曲','轮毂顶丝牢固，轮圈不打滑','两后轮旋转不擦车壳/支架'], 'M3×6×8、轮毂附带1.5 mm扳手')
step('前轮：轴承与隔套',['front_wheel_L','front_wheel_R',*[p for p in P if p.startswith(('bearing_','tire_front'))]],
     '每个前轮从两侧装入MR83ZZ，中间夹6 mm隔套；每轮两条橡胶圈。用M3×30螺钉作固定轴，配小外径垫片、约2 mm外隔套与尼龙锁紧螺母。只压轴承内圈；拧紧后若轮圈变涩，停止并修配隔套，不能靠完全松开螺母凑合。',
     ['前轮能自由旋转，四轮均接地','内外隔套仅接触轴承内圈','前轮端隙很小但没有被夹死'], 'M3×30×2、锁紧螺母×2、垫片、2 mm外隔套')
step('固定电池与电路',['battery_holder','electronics_bridge','esp32','driver','regulator','microphone','power_switch','arm_button'],
     '断开电池。电池盒扎带固定，ESP32用3 mm绝缘泡棉固定在电子托架上，向下排针穿过开槽；托架4×M3×8锁入支柱侧装螺母。驱动在后部，升降压在前部，麦克风用软泡棉隔振并对准声孔。尾部装总开关与ARM按钮；采购尺寸不符先改支架。',
     ['所有电路底面绝缘，无裸焊点碰金属','USB可在拆壳后插入；电池可取出充电','麦克风未被泡棉堵住，电线不碰轮子'], '泡棉、扎带、M3×8×4、M3螺母×4')
step('按编号逐线接线',[],
     '切到“电气接线”，逐条完成W01–W22。电池正极先串1 A慢熔保险再到总开关，VM与5V逻辑分开。PWM1/PWM2各对地10kΩ，ADC34对地100kΩ；电机端各并100nF。驱动VM/GND并470µF/10V、稳压5V/GND并100µF/10V，注意极性并绝缘。',
     ['万用表检查正负间无短路，电解电容极性正确','主板断开时先测5V输出正常','总开关关闭后电池供电断开','没有同时连接USB和电池5V'], '电烙铁、热缩管、万用表；新手请由会焊接的人协助')
step('刷固件与抬轮试车',[],
     '先拔掉电池插头，再接USB。安装ESP32_GENERIC的MicroPython，用Thonny把controller.py、config.py、main.py复制到板子。断USB后接电池，轮子架空开电源；默认不转。按ARM，先保持安静，再发声；方向不对先断电交换对应电机两根线。',
     ['通电和复位时不会自行转动','ARM之前发声不转；ARM后先安静再发声才能启动','停止发声后输出停止，按ARM可撤销使能','默认低速5秒保护会停，安静后才可再启动'], 'USB数据线、Thonny、稳定抬轮支架')
step('调整门槛，排除自噪声',[],
     '先仅用USB、断开电池，观察安静与目标声音的串口RMS，调整ON/OFF（OFF小于ON）。需要带电机看串口时，必须先拔掉稳压Vo+到主板5V的接线并绝缘，保持共地，再接USB；电池仅供电机VM，不能与USB并接主板5V。固件停转90 ms后采样约40 ms，降低自触发但可能顿挫。安静时不停车则先隔振/走线/门槛排查，不可上地。调完断开USB和电池，恢复Vo+接线。',
     ['至少20次响/静切换可靠，电机自己不能维持启动','拔麦克风/压ARM能停止；断开检测不是安全认证','驱动和稳压不过热，主板没有重启'], '串口监视器、观察记录；没有校准声级计也不显示60dB')
step('合上外壳',['body_shell','canopy'],
     '在壳内四个六角槽放入M3螺母并少量可拆胶临时固定，从底盘下方用4×M3×12锁壳。线束沿内部边缘扎好，转轮检查不夹线。黑色座舱用薄双面胶粘在壳顶，是可选装饰件。',
     ['四个壳螺钉牢固且没有顶住电池或电路板','外壳与四轮保留间隙','声孔畅通，总开关与ARM按钮都能触及'], 'M3×12×4、M3螺母×4、薄双面胶')
step('地面调试与完整演示',[],
     '在有边界的光滑地面低速试车，不在桌沿。记录1 m用时、停止响应和偏航，使用LEFT_TRIM/RIGHT_TRIM微调；没有编码器不能保证绝对直行。完成检查后才将PROFILE改为continuous_while_loud并把HARDWARE_CHECKED设为True；此模式取消5秒上限，但仍先ARM、安静解锁、听音采样。',
     ['安静时可靠停车，连续重复演示至少20轮','实测速度、运行温升和停车距离已记录','全程有人可断总电源，未靠近台阶/桌沿/宠物'], '卷尺、秒表、记录表；成人监督')

# Analytical checks, all assumptions explicit. No invented CFD / FEA / test results.
m=.45;radius=.0234;crr=.025;acc=.25;voltage=4.5
force=m*(9.81*crr+acc);torque=force*radius/2
stall=.39*.0980665*(voltage/6);design_limit=stall*.25
speed_full=400*(voltage/6)*2*math.pi*radius/60
engineering={
 'status':'ANALYTICAL_ESTIMATE_NOT_PHYSICAL_PASS',
 'assumptions':{'massKg':m,'wheelRadiusM':radius,'rollingResistanceCoefficient':crr,'levelFloor':True,'accelerationMps2':acc,'loadedMotorSupplyV':voltage,'motorRpm6V':400,'stallTorqueKgCm6V':.39,'stallCurrentA6V':.35},
 'calculations':{'requiredForceN':force,'torquePerMotorNm':torque,'quarterStallTorquePerMotorNm':design_limit,'torqueMargin':design_limit/torque,'fullDutyNoLoadMps':speed_full,'commissioningDuty':.45,'commissioningNoLoadUpperMps':speed_full*.45,'twoMotorStallCurrentAAt6V':.70,'driverRatedAEach':1.2,'driverCurrentRatingToMotorStallRatio':1.2/.35,'quietMeasurementCycleMsApprox':290,'onCommandElectricalStopLatencyMsApprox':310,'groundClearanceMm':4.2,'nominalWheelDiameterMm':46.8,'nominalWheelbaseMm':126,'nominalTrackMm':114.6},
 'summary':[
  f'按0.45 kg、水平光滑地面、滚阻0.025及0.25 m/s²加速度估算，每电机需{torque:.4f} N·m；对照4.5V下1/4堵转转矩的估算余量约{design_limit/torque:.1f}倍。不是持续转矩实测。实际整车需称重。',
  f'4.5V下全占空比空载速度估算{speed_full:.2f} m/s；默认45%低速试车上界约{speed_full*.45:.2f} m/s，负载和停转听音会更慢。0.5 m/s仍是待实测目标，不是本版承诺。',
  '额定6V下两电机合计堵转电流约0.70A；DRI0044标称每路1.2A不代表安装后可无限时堵转，禁止用手长时间卡轮测试。',
  '主控5V独立升降压，电机走电池VM；ESP32 Wi-Fi关闭。必须实测启动压降、棕断和温升。',
  '声音为相对RMS门槛，不是60dB SPL。停转90ms后听音降低自噪声反馈，不能保证所有环境下消除误触发。',
  '一次声音变化到电机指令停止约0.31s上界估计（正常循环）；机械停车距离、惯性和声音反射仍需实测。',
  '外壳和悬臂未做结构FEA、跌落或儿童安全认证。只用于成人监督下的低速原型演示。'
 ]}
(OUT/'checks/engineering.json').write_text(json.dumps(engineering,ensure_ascii=False,indent=2),encoding='utf8')
M.update(assembly=STEPS,connections=WIRES,bom=BOM,engineering=engineering,budgetAllocationCny=total)
M.pop('wireDisplay',None)
route_file=OUT/'checks/wire-display.json'
if route_file.exists():
    report=json.loads(route_file.read_text(encoding='utf8'))
    expected={p['id']:{'stl':p['sha256']['stl'],'step':p['sha256']['step'],'position':P[p['id']]['position'],'rotation':P[p['id']]['rotation']} for p in M['cadParts']}
    if report.get('modelBindings')==expected:
        M['wireDisplay']=report
(OUT/'manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf8')
with (OUT/'BOM.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['零件','数量','接口要求','预算单价CNY（非报价）','来源'])
    for p in BOM:w.writerow([p['name'],p['qty'],p['spec'],p['budgetCny'],p['url']])
with (OUT/'connections.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['编号','起点部件','起点端子','终点部件','终点端子','线径AWG','类别','注意'])
    for x in WIRES:w.writerow([x['id'],x['from']['partId'],x['from']['terminal'],x['to']['partId'],x['to']['terminal'],x['wireAwg'],x['kind'],x['note']])

# Purpose-built readable wiring diagram: each route has exact terminal labels.
E=html.escape
rows=[]
for i,w in enumerate(WIRES):
    y=143+i*50
    a=P[w['from']['partId']]['name'].split('·')[0].strip();b=P[w['to']['partId']]['name'].split('·')[0].strip()
    rows.append(f'<g><text x="35" y="{y+8}" fill="#94a3b8">{w["id"]}</text><rect x="94" y="{y-15}" width="315" height="39" rx="7" fill="#192231"/><text x="109" y="{y+9}">{E(a)} / {E(w["from"]["terminal"])}</text><path d="M 409 {y+4} H 678" stroke="{w["color"]}" stroke-width="3"/><text x="537" y="{y-4}" text-anchor="middle" font-size="11" fill="#a8b7cc">{w["wireAwg"]} AWG</text><circle cx="678" cy="{y+4}" r="4" fill="{w["color"]}"/><rect x="687" y="{y-15}" width="358" height="39" rx="7" fill="#192231"/><text x="701" y="{y+9}">{E(b)} / {E(w["to"]["terminal"])}</text></g>')
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1390" viewBox="0 0 1080 1390"><rect width="1080" height="1390" fill="#0d1420"/><g fill="#e3eaf4" font-family="Microsoft YaHei,Arial,sans-serif" font-size="13"><text x="35" y="48" font-size="26" font-weight="700">ECHO F1 / 逐线接线图</text><text x="35" y="80" fill="#f5bc8c">先断电 · ESP32 5V 与 USB 互斥 · MAX4466 只用 3.3V · 电机不接 GPIO</text><text x="35" y="106" fill="#a6b5c9">接口名称以模块丝印为准；所有 GND 共地。此图不是PCB布线文件。</text>{''.join(rows)}<text x="35" y="1285" fill="#f5bc8c">必须加：PWM1、PWM2 各对地10kΩ；GPIO34 对地100kΩ。</text><text x="35" y="1316">电机端各并100nF；驱动VM并470µF/10V；稳压5V并100µF/10V，注意电解电容极性。</text><text x="35" y="1347" fill="#a6b5c9">W01 必须串1A慢熔保险；主开关另一外脚绝缘。不确定时先让会焊接的人检查。</text></g></svg>'''
(OUT/'wiring.svg').write_text(svg,encoding='utf8')

for f in ['config.py','controller.py','main.py','test_controller.py']:
    shutil.copyfile(ROOT/'firmware/echo-f1'/f,OUT/'firmware'/f)
result=subprocess.run([sys.executable,str(ROOT/'firmware/echo-f1/test_controller.py')],capture_output=True,text=True)
(OUT/'checks/firmware-tests.txt').write_text(result.stdout+result.stderr,encoding='utf8')
assert result.returncode==0

parts_table=''.join(f'<tr><td>{E(p["name"])}</td><td>{p["qty"]}</td><td>{E(p["spec"])}</td><td>{p["budgetCny"]}</td></tr>' for p in BOM)
prints=''.join(f'<tr><td>{E(p["name"])}</td><td>{" × ".join(map(str,p["sizeMm"]))}</td><td>{E(p["orientation"])}</td><td><a href="{p["file"]}">STL</a></td></tr>' for p in M['printParts'])
steps=''.join(f'<section><span class="eyebrow">STEP {i+1:02d}</span><h2>{E(s["title"])}</h2><p>{E(s["text"])}</p><ul>'+''.join(f'<li>□ {E(c)}</li>' for c in s['checks'])+f'</ul><p class="muted">工具：{E(s["tools"])}</p></section>' for i,s in enumerate(STEPS))
calculations=''.join(f'<li>{E(s)}</li>' for s in engineering['summary'])
doc=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ECHO F1 · 制作指南</title><style>
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.9 -apple-system,'Segoe UI','Microsoft YaHei',sans-serif;color:#1c2531;background:#f6f7fa}}main{{max-width:1080px;margin:auto;padding:48px 38px}}header{{padding:48px 0;border-bottom:1px solid #dce0e7}}h1{{font-size:52px;line-height:1.15;letter-spacing:-.05em;margin:15px 0}}h2{{font-size:24px;font-weight:650;margin:12px 0}}h3{{font-size:18px}}.eyebrow{{color:#c42947;font-size:11px;letter-spacing:.15em;font-weight:bold}}.lead{{max-width:730px;font-size:18px;color:#536174}}.badge{{display:inline-block;background:#fff0da;color:#795a1b;padding:5px 12px;border-radius:7px;font-size:12px}}section{{margin:35px 0;padding:25px 0;border-bottom:1px solid #dce0e7}}.notice{{padding:18px 22px;background:#fff1dd;border-left:3px solid #c38430;line-height:1.8}}.muted{{color:#718095;font-size:12px}}table{{width:100%;border-collapse:collapse;font-size:12px}}td,th{{text-align:left;vertical-align:top;padding:10px 8px;border-bottom:1px solid #dce0e7}}td:nth-child(3){{min-width:180px}}a{{color:#b42644}}li{{margin:6px 0}}code,pre{{background:#e7ebf0;border-radius:5px;padding:2px 6px}}pre{{padding:18px;overflow:auto}}img{{max-width:100%;border-radius:14px}}@media print{{body{{background:white}}main{{padding:15px}}section{{break-inside:avoid}}h1{{font-size:38px}}.no-print{{display:none}}}}@media(max-width:700px){{main{{padding:25px 16px}}h1{{font-size:40px}}table{{font-size:10px}}}}
</style><main><header><span class="eyebrow">M4KE / BUILD EDITION 01</span><h1>ECHO F1.<br>把声音变成前进的力量。</h1><p class="lead">红黑 F1 风格声控小车：ESP32、相对响度门槛、可拆 PLA 车壳、双后轮驱动。这里的模型由本次设计直接生成，不作为 Qwen 自动设计成功的证明。</p><span class="badge">可下载原生 CAD / STL · 原型首版，等待装配实测</span></header>
<section><h2>先知道这五件事</h2><ol><li>整车约225×129×66 mm，比原约20 cm目标略长，为电池、接线和可拆安装留空间。轴距126 mm，轮圈44 mm，装橡胶圈后约46.8 mm。</li><li>不是准确的60 dB控制；当前按你确认使用可调相对响度。</li><li>默认是抬轮低速试车：先ARM、再安静、再发声，连续5秒保护停。完成实测后可显式启用持续响时前进模式。</li><li>STL是打印件，assembly-parts中的采购件网格只用来理解装配，不能把电机/PCB打印出来替代实物。</li><li>本包没有厂家公差证明、结构FEA、切片完成记录或实物通过结论。先试片，再打印，再按检查单逐步通电。</li></ol><div class="notice">电池在外部镍氢充电器充电；插USB前拔掉电池插头。禁止同时从USB和5V针脚供电。禁止换成14500锂电池。成人监督，先架空车轮，不在桌沿试车。</div></section>
<section><h2>打印与切片</h2><p>打印机不预设。H2C可以在Bambu Studio选实际机型后导入STL；其它热床也可，只要容纳长件和所需边缘。A1 mini的180 mm热床不适合本版长件，不能通过缩小模型解决。0.4 mm喷嘴、PLA、0.20 mm层高、4道壁、5层顶底；底盘25–35%填充，轮圈40%，隔套100%。外壳树状支撑只接触热床；具体温度、流量与支撑间距使用所购耗材标定。</p><p><a href="print/00_fit_coupon.stl">先下载公差试片</a>。从左到右：3.2、3.3、3.4、8.1、8.2 mm孔；试片长62 mm。试配失败时修改CAD参数重新生成，不要磨坏轴承或强塞。</p><table><tr><th>打印件</th><th>尺寸mm</th><th>方向与建议</th><th>文件</th></tr>{prints}</table></section>
<section><h2>采购清单</h2><p>预算分配合计 ¥{total}。金额不是实时报价，型号/运费/国内现货请下单前核对；尤其金属轮毂与麦克风的国内售价可能使总价超过600元。电池盒、开关存在外形变体，必须符合尺寸要求。焊接工具、卡尺、万用表不计入材料预算。</p><table><tr><th>零件</th><th>数量</th><th>规格</th><th>预算单价¥</th></tr>{parts_table}</table><p><a href="BOM.csv">下载BOM.csv（含厂家链接）</a></p></section>
<section><h2>接线总图</h2><p>颜色是装配建议，不是采购线材自带标准。先核对针脚文字，再接线。3D示意线路按当前原生CAD避开零件，开壳查看只隐藏外壳、不让线路穿透显示。端点是元件表面附近的虚拟接口，不是真实焊脚；真实端子以此表与厂家丝印为准。尚未验证接头体积、弯曲半径与线间距，不能据此直接裁线或认定完整线束可装配。</p><a href="wiring.svg"><img src="wiring.svg" alt="W01到W22逐线接线图"></a><p><a href="connections.csv">下载逐线连接表</a></p></section>
{steps}
<section><h2>固件安装与调参</h2><ol><li>在 <a href="https://micropython.org/download/ESP32_GENERIC/">MicroPython官方ESP32_GENERIC页面</a>下载支持经典ESP32的固件。不要下载C3或S3固件。</li><li>用Thonny选择MicroPython (ESP32)解释器和开发板串口。电池已拔掉；可用Thonny的安装/更新MicroPython功能按官方指引刷固件。</li><li>将firmware目录的config.py、controller.py、main.py保存到设备根目录，重启。</li><li>先从串口读出安静、外部发声、仅电机转动时的RMS；设置THRESHOLD_ON与THRESHOLD_OFF，OFF需小于ON。例如安静100、目标声1500时可试ON1000/OFF700，这不是通用校准值。</li><li>在串口中断程序会进入finally并关闭PWM；退出前仍建议断总电源。外部10kΩ下拉保证重启时PWM不悬空。</li></ol><pre>PROFILE = 'commissioning'  # 默认低速限时试车
PWM_DUTY = 0.45
# 完成所有物理检查后，才可人工改为：
PROFILE = 'continuous_while_loud'
HARDWARE_CHECKED = True
# LEFT_TRIM / RIGHT_TRIM 只允许 0..1 范围内减速校准
</pre><p>持续模式仍有停转听音窗口和可能的轻微顿挫，不是无间断恒速控制。没有编码器，无法保证精确速度/直行；目标0.5 m/s必须实测，当前低速默认值不会达到该目标。</p><p><a href="firmware/main.py">main.py</a> · <a href="firmware/controller.py">controller.py</a> · <a href="firmware/config.py">config.py</a></p></section>
<section><h2>计算、验证与边界</h2><ul>{calculations}</ul><p>原生实体与STL均检查：有效BRep、正体积、单实体打印件、STL封闭/绕向、网格与实体体积差小于1%、STEP重新导入。未解释的零件体积相交必须为0才允许打包。橡胶圈压在轮圈槽中的接触/变形单独记录。</p><p>不包括：螺纹细节、所有接线接头、胶垫变形、完整线束空间、打印变形、连续结构强度、热设计和实际声音反馈。所有采购件是尺寸参考形体，不冒充精细厂家CAD。</p><p><a href="checks/geometry.json">几何检查JSON</a> · <a href="checks/engineering.json">计算JSON</a> · <a href="checks/firmware-tests.txt">固件逻辑测试</a></p></section>
<section><h2>实物验收记录（请你填写）</h2><table><tr><th>项目</th><th>记录</th><th>是否通过</th></tr><tr><td>20次声音启动/停止，无自激</td><td>未测试</td><td>□</td></tr><tr><td>1 m用时 / 平均速度</td><td>未测试</td><td>□</td></tr><tr><td>撤去声音到停稳的时间 / 距离</td><td>未测试</td><td>□</td></tr><tr><td>连续演示5 min温升 / 主板重启</td><td>未测试</td><td>□</td></tr><tr><td>螺钉、轮毂、轮胎没有松脱</td><td>未测试</td><td>□</td></tr></table></section>
<footer class="muted">M4KE · ECHO F1 v1。原创CAD与代码按仓库MIT许可；供应商资料仅链接、不随包复制。生成器：cad/designs/echo_f1.py；说明构建器：cad/designs/echo_f1_package.py。</footer></main></html>'''
if (OUT/'preview.png').exists():
    doc=doc.replace('</header>','</header><figure><img src="preview.png" alt="实际STL视口截图，不是效果图"><figcaption class="muted">应用中的真实装配网格。</figcaption></figure>',1)
(OUT/'instructions.html').write_text(doc,encoding='utf8')
(OUT/'START-HERE.txt').write_text('ECHO F1 v1\n1. Open instructions.html in your browser.\n2. Print only files in print/ at 100% / millimetres. Start with 00_fit_coupon.stl.\n3. Do not print purchased reference meshes from assembly-parts/.\n4. Disconnect battery before USB. Physical testing has NOT been completed.\n5. App: /?build=echo-f1-v1 on your running M4KE server.\n',encoding='utf8')
(OUT/'source').mkdir(exist_ok=True)
for f in ['echo_f1.py','echo_f1_package.py','echo_f1_wiring.py','README.md']:shutil.copyfile(ROOT/'cad/designs'/f,OUT/'source'/f)
(OUT/'source/REGENERATE.txt').write_text('These generators belong in cad/designs/ of the M4KE repository, not in an arbitrary folder. Copy firmware/ back to firmware/echo-f1/. See source/README.md for dependencies and commands.\n',encoding='utf8')
shutil.copyfile(ROOT/'LICENSE',OUT/'LICENSE')
M['packageStatus']='READY_FOR_FIT_CHECK'
(OUT/'manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf8')
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='SHA256SUMS.json']
hashes={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2),encoding='utf8')
with zipfile.ZipFile(OUT/'ECHO-F1-build-package.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[OUT/'SHA256SUMS.json']:z.write(p,'ECHO-F1-v1/'+p.relative_to(OUT).as_posix())
with zipfile.ZipFile(OUT/'ECHO-F1-build-package.zip') as z:assert z.testzip() is None
print(json.dumps({'budgetAllocationCny':total,'printParts':len(M['printParts']),'parts':len(M['parts']),'assemblySteps':len(STEPS),'connections':len(WIRES),'packageBytes':(OUT/'ECHO-F1-build-package.zip').stat().st_size},indent=2))
