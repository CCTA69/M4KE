"""Package CN v2 artifacts, truthful procurement gates and beginner instructions."""
from pathlib import Path
import csv, hashlib, html, json, math, shutil, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'printing'))
from build_handbook import enrich_document
OUT=ROOT/'builds/echo-f1-cn-v2'
M=json.loads((OUT/'manifest.json').read_text(encoding='utf8'))
plan_path=OUT/'plates/print-plan.json'
if plan_path.exists():
    M['printPlan']=json.loads(plan_path.read_text(encoding='utf8'))
    expected={p['id']:p['sha256'] for p in M['printParts']}
    expected['fit_coupon']=hashlib.sha256((OUT/'print/00_fit_coupon.stl').read_bytes()).hexdigest()
    assert M['printPlan']['sourcePrintHashes']==expected, 'Regenerate plates after changing any print mesh'
assert not M['checks']['interferenceConflicts'], 'Fix intersections first'
P={p['id']:p for p in M['parts']}
for part in M['printParts']:
    pid=part['id']
    if pid.startswith('chassis_'):
        part['orientation']='底板平面朝下；0.20mm、4壁、35%填充；轴孔/螺母侧槽检查短桥接，必要时局部支撑。'
    elif pid.startswith('splice_'):
        part['orientation']='平面朝下；0.20mm、4壁、100%填充；沉头孔需试配，不要让螺钉头突出底面。'
    elif pid.startswith('front_wheel_'):
        part['orientation']='文件已将轮圈放平，轴孔竖直；0.20mm、4壁、40%填充，先试693ZZ孔配合。'
    elif pid.startswith('bearing_spacer_'):
        part['orientation']='文件已将轴孔竖直；100%填充，量6mm长度；拧紧后轮必须自由转。'
    elif pid.startswith('motor_'):
        part['orientation']='平面朝下；0.20mm、4壁、50%填充；螺钉松紧以不压坏电机为准。'
    elif pid=='rear_wing':
        part['orientation']='文件已翻转，尾翼上表面贴床、支柱向上；0.20mm、4壁、35%填充，底脚悬挑用局部支撑。'
    elif pid=='canopy':
        part['orientation']='保持文件方向，底部随车壳曲面成形，需树状支撑；0.16mm、4壁、25%填充，可省略此装饰件。'
B=[]
def buy(name,qty,spec,cost,url='',status='SPECIFIED_NOT_ORDERED'):
    B.append(dict(name=name,qty=qty,spec=spec,budgetCny=cost,url=url,
        priceStatus='BUDGET_ALLOCATION_NOT_LIVE_QUOTE',procurementStatus=status))
buy('DFRobot Romeo mini DFR1063',1,'ESP32-C3集成双路驱动；成品已焊排针/螺丝端子；47×38.5 mm。购物车已有，勿重复。',145,'https://wiki.dfrobot.com/dfr1063/')
buy('带接口N20电机 6V / 50:1',2,'必须带预焊抑噪接口板+PH2.0转已剥皮/压端子引线。参考440rpm、堵转0.35A；12×10截面，本体26–32mm，3mm D轴有效长9.27mm。裸FIT0094不等于这个版本。',45,'https://wiki.dfrobot.com.cn/026_%E9%87%91%E5%B1%9E%E5%87%8F%E9%80%9F%E7%94%B5%E6%9C%BA','SELLER_MATCH_REQUIRED')
buy('42×19 mm 橡胶驱动轮',2,'和上行N20同店配套，3mm D孔，有效咬合至少5mm；轮内侧到电机端面留4mm；带轮芯无需Pololu轮毂。',15,'','SELLER_MATCH_REQUIRED')
buy('Gravity DFR0034 V2 声音模块',1,'仅买支持3.3V版本，22×30mm；成品带Gravity转2.54母头线，不买待焊排针。用于相对强度，不是校准分贝计。',35,'https://wiki.dfrobot.com/dfr0034/')
buy('DFRobot DFR0379 降压模块',1,'LM2596S带显示/螺丝端子；空载设5.5V；本体和接头须在66×40×20mm包络内，超出先改托位。不可省略稳压。',25,'https://www.dfrobot.com.cn/goods-1351.html','DIMENSIONS_TO_CONFIRM')
buy('AA镍氢电池',8,'同品牌同容量1.2V、1900–2500mAh；不要14500锂电池，不混新旧电池。',8)
buy('镍氢专用充电器',1,'支持8节所购AA NiMH（或分两批充），电池取出充电。',40)
buy('8×AA串联平铺带线电池盒',1,'最大120×65×20mm，端部已剥皮/压冷压端头；必须确认外尺寸。不能买双层盒。',8,'','DIMENSIONS_TO_CONFIRM')
buy('成品带线总开关/保险线束',1,'开关≥2A/12VDC，本体≤18×10×12mm；1A慢熔保险座近电池正极，配2只备用；端头已加工，螺丝或拨杆端子连接。',20,'','PREASSEMBLED_ONLY')
buy('免焊常开按键模块',1,'干接点型，已焊排针，GPIO6至GND；≤15×12×7mm，不买输出5V的有源按键板。',8)
buy('免焊线材/端子包',1,'电源/电机22AWG多股软线，预剥皮/预压端头；信号26AWG母头。2.54母母15–20cm、绝缘双线拨杆端子≥4个；不用细杜邦线供电机。',25)
buy('M3紧固件与前轴包',1,'M3×12沉头:4，M3×10:12，M3×30:6；螺母/垫片各20，尼龙锁紧螺母2；前轴另配内径3.2/外径≤5/长3mm隔套2。前轴优先有效光杆覆盖轴承。',20)
buy('693ZZ 3×8×4mm轴承',4,'沿用购物车的4只；不要按旧稿MR83ZZ名称买错。',1.5)
buy('NBR70 O形圈一包10只',1,'内径40×线径3mm；车上前轮共4条，其余备用。沿用已有规格。',3)
buy('白/灰烬红PLA耗材份额' if M.get('appearance') else '红/黑PLA耗材份额',1,
    '当前配色：A4白色PLA Basic至少300g，A1灰烬红PLA Silk至少250g；丝绸料仅外壳，含支撑余量，最终看实际切片。预算是用量份额，不是两整卷价格。' if M.get('appearance') else 'H2C建议黑PLA至少300g、红PLA至少250g；含试片/支撑余量，最终看实际切片；预算是用量份额，不是两整卷价格。',35)
buy('绝缘泡棉/扎带/双面胶',1,'2mm闭孔泡棉；2.5mm宽扎带≥20；不要导电双面胶。',4)
buy('USB-C数据线',1,'支持数据，不能只充电；仅烧录时接入，外部电池需拔下。',8)
total=sum(x['qty']*x['budgetCny'] for x in B)
assert total<=600

W=[]
def wire(a,at,b,bt,kind,color,awg,note):
    W.append({'id':f'W{len(W)+1:02d}','from':{'partId':a,'terminal':at},'to':{'partId':b,'terminal':bt},
              'kind':kind,'color':color,'wireAwg':awg,'note':note,'routingStatus':'MISSING_ANCHORS'})
wire('battery_holder','+ → 1A慢熔保险座','power_switch','IN','power','#f65f70',22,'买完整带线保险座和开关。保险尽量靠近电池；接头绝缘。')
wire('power_switch','OUT','regulator','IN+','power','#ed6558',22,'预剥皮/压端头线进螺丝端子，拉一下确认牢固，不露长铜线。')
wire('battery_holder','−','regulator','IN−','ground','#9baabf',22,'电池负极不用穿过开关。按模块实际丝印确认正负。')
wire('regulator','OUT+ / 5.5V','esp32','VIN+','power','#ffa65b',22,'先单独用万用表量到5.5V再接主板；不是3V3针。8节电池绝不能直接6V电机。')
wire('regulator','OUT−','esp32','GND / VIN−','ground','#9baabf',22,'主板同一个地；USB烧录前拔外部电池。')
wire('esp32','模拟排针 3V3','microphone','VCC 红线','power','#ffc579',26,'只接模拟区3.3V，不接数字区默认5V排针；确认所购传感器支持3.3V。')
wire('esp32','GND','microphone','GND 黑线','ground','#99aec5',26,'Gravity转母头成品线；引脚位置以丝印而非线序猜测。')
wire('microphone','模拟 OUT 蓝线','esp32','GPIO3 / A3','signal','#60d9ba',26,'相对声音强度，固件取均值；模拟线与电机线分开。')
wire('esp32','M1 OUT+','motor_L','PH2.0 导线1','motor','#f6ad69',22,'成品带线电机；不用把杜邦母头塞裸焊孔，不要求你焊电容。')
wire('esp32','M1 OUT−','motor_L','PH2.0 导线2','motor','#b98c60',22,'M1内部用DIR=GPIO1、PWM=GPIO0；先架空确认方向。')
wire('esp32','M2 OUT+','motor_R','PH2.0 导线1','motor','#b392e9',22,'M2内部用DIR=GPIO10、PWM=GPIO2；镜像方向在config.py中校正。')
wire('esp32','M2 OUT−','motor_R','PH2.0 导线2','motor','#8364b1',22,'GPIO2涉及启动配置；实机必须检查上电/复位时无意外转动。')
wire('esp32','GPIO6','arm_button','常开触点A','signal','#74bafa',26,'只接干接点；固件内部上拉。按一次解锁，再按一次停。')
wire('arm_button','常开触点B','esp32','GND','ground','#a0b2c6',26,'不接5V或3V3，先断电用蜂鸣档核对两触点。')

S=[]
def step(title,ids,text,checks,tools):
    i=len(S)+1;S.append(dict(id=f'S{i}',title=title,partIds=ids,requires=[f'S{i-1}'] if i>1 else [],text=text,checks=checks,tools=tools))
step('先核对实物，打印公差试片',[],
     '先确认带线N20及配套轮、电池盒、降压模块的尺寸。不要买旧12V/500rpm电机替代。只打印00_fit_coupon，试M3螺钉、693ZZ轴承；通过后才整套打印。',
     ['电机确为免焊6V版本，不是裸焊片','轮轴尺寸与配套轮咬合深度确认','盒与模块在清单包络内','试片轴承孔能手压安装且不过松'], '游标卡尺、M3螺钉、693ZZ')
step('拼接底盘和前翼',['chassis_front','chassis_rear','splice_L','splice_R','front_wing'],
     '两块拼接桥放底盘中缝下方，用4枚M3×12沉头螺钉从下向上装，配垫片螺母；头部不得突出桥板底面。前翼置鼻锥下，用两条扎带绕鼻梁并穿过前翼槽固定。不要缩放任何STL。',
     ['中缝约0.4mm，两半在同一平面','拼接螺母不碰电池盒','前翼不刮地，线扣不拖地'], 'M3×12×4，扎带×2')
step('安装自由前轮',['front_wheel_L','front_wheel_R','bearing_L_0','bearing_L_1','bearing_R_0','bearing_R_1','bearing_spacer_L','bearing_spacer_R','tire_front_L_0','tire_front_L_1','tire_front_R_0','tire_front_R_1'],
     '每个前轮两侧各放一只693ZZ，中间放6mm隔套；M3×30作固定轴。支架与轮内轴承之间放3mm小外径隔套，外侧垫片只压轴承内圈，用锁紧螺母。每轮装两条40×3橡胶圈。',
     ['拧好后轮仍顺滑自由转','每侧2轴承+1内隔套，内圈承受夹紧','四条橡胶圈均坐入槽，无翘起'], 'M3×30×2，锁紧螺母，3mm外隔套，垫片')
step('装预接线电机和成品后轮',['motor_saddle_L','motor_saddle_R','motor_L','motor_R','motor_clamp_L','motor_clamp_R','rear_tire_L','rear_tire_R','rear_hub_L','rear_hub_R'],
     '电机平放N20鞍座，3mm D轴朝外；薄绝缘软垫消隙，压条用每侧两枚M3×30从底盘向上穿，螺母在压条上，避免长螺纹朝地面。后轮买与电机配套的42×19成品轮，支撑齿轮箱前端后轻压安装，切勿敲轴。',
     ['轮内侧在距中线72mm左右且不擦支架','D轴至少5mm插入轮芯且不能打滑','电机本体和插座不受夹压','两侧输出轴平行，线头没有裸露'], 'M3×30×4，薄泡棉；不需要焊锡')
step('装电池、调5.5V电源',['battery_holder','regulator','power_switch'],
     '电池盒下放2mm绝缘泡棉，用两条扎带穿底盘槽固定。8节NiMH经成品保险开关线束接降压IN。先不接主板；按模块说明用电位器设OUT为5.5V，用万用表独立核对，然后断电。',
     ['电池是8节1.2V NiMH，不是锂电','输出5.5V且极性正确','开关关断后输出下降为0','预剥皮线牢固，绝缘线束不碰转轮'], '万用表、小螺丝刀、成品线束；不需要焊接')
step('装主控、声音模块与ARM键',['electronics_bridge','esp32','microphone','arm_button'],
     '先把M3螺母放支柱侧槽，再用4枚M3×10固定托架。Romeo和声音模块用非导电泡棉与扎带固定，排针下方留空；麦克风朝上对准前半壳声孔。按键用约4mm厚绝缘泡棉固定在车尾开关左侧，与翼脚留间隙。',
     ['主板47×38.5mm且型号DFR1063','Gravity声音板支持3.3V并带成品线','开关和按钮能从尾部伸手操作','USB口与电池均可拔出'], 'M3×10×4，绝缘泡棉，扎带')
step('按编号免焊接线', ['esp32','microphone','motor_L','motor_R','regulator','arm_button'],
     '保持断电，按W01–W14逐条接。电源和电机线用预压端头进接线端子，不能用松动细杜邦线供电机；传感器只用模拟区3.3V。每接一条拉线检查，完成后核对短路和极性。',
     ['W01–W14逐条比对实物丝印','没有铜丝散开或露在相邻端子间','电机电源不经过GPIO','所有未使用的导线端已绝缘'], 'connections.csv，螺丝刀，万用表')
step('烧录并进行架空测试',['esp32','arm_button','motor_L','motor_R'],
     '拔下电池，再接USB-C；在Thonny选择ESP32-C3官方MicroPython固件，上传config.py、controller.py、main.py。烧录后拔USB再接电池，保持两轮架空，ARM后先安静再发声。',
     ['使用ESP32_GENERIC_C3而不是旧WROOM固件','默认5秒试车上限有效','双轮向前，按钮可立刻停机','重复20次上电/复位无意外转动'], 'USB-C数据线、Thonny、架空支撑')
step('标定响度并检测自激',['microphone','esp32'],
     '串口查看INTENSITY，分别记录安静、外部发声和电机停转后的余响。设ON高于安静/余响且低于目标声，OFF比ON低。无法拉开时必须改善隔振或降低电机速度，不能把失效值当通过。',
     ['不是60dB校准数值','停止发声后停车，没有电机噪声自激','拔传感器/故障行为已测试，浮空检测有局限','默认慢速限时模式先通过'], '安静空间、软垫、串口')
step('装可拆外壳与尾翼',['shell_front','shell_rear','canopy','rear_wing'],
     '先让电源线走底盘侧面，信号线走上层，所有线离轮与翼柱至少3mm并用扎带固定。分段外壳各侧耳用M3×10固定，耳与底盘间垫0.8–1mm绝缘垫片，避免拧弯；尾翼2枚M3×10。座舱盖用薄双面胶固定。',
     ['盖壳时没有夹线或遮住声孔','尾部开关和ARM按钮可操作','轮转动和电池更换无干涉','打印变形或孔偏需修配/重出CAD，不强压'], 'M3×10×6，薄垫片，双面胶，扎带')
step('地面验收后再启用持续模式',[],
     '只在平整地面成人监督测试。记录20次响/静启停、1m用时、撤声停车距离及5分钟温升/掉电。全部通过才把PROFILE设continuous_while_loud、HARDWARE_CHECKED设True。仍有静音采样顿挫，不是恒速车。',
     ['20次可靠启停，无脱线/自激/主板复位','实测速度与停车距离记录','电池、模块、电机不过热，无异味','轮子和螺钉不松，清楚总开关位置'], '地面、卷尺、秒表、温度计（可选）')

mass_print=sum(p['solidEquivalentPlaGrams'] for p in M['printParts'])/1000
mass_bound=max(.90,mass_print+.45)  # design allowance, not a measured or guaranteed upper bound
rr=.03;accel=.25;radius=.021
force=mass_bound*(9.81*rr+accel)
torque=force*radius/2
no_load=440*(5.5/6)*2*math.pi*radius/60
current_per=.35*(5.5/6)
ELECTRICAL={'motorReference':'DFRobot PH2.0 6V 50:1 only; substitute current must be independently checked',
  'supplyV':5.5,'driverContinuousAperChannel':1.7,'referenceStallAperChannelAt5_5V':round(current_per,3),
  'controllerAllowanceA':.30,'outputPeakEstimateA':round(2*current_per+.30,3),'status':'CALCULATED_FROM_REFERENCE_NOT_MEASURED'}
summary=[
 f'整车外包络 {"×".join(map(str,M["dimensionsMm"]))} mm；轴距177 mm，前轮46.8 mm、后轮42 mm。分段打印，不按比例缩小。',
 f'全实心PLA等效质量 {mass_print:.3f} kg；计算按{mass_bound:.3f}kg整车设计质量假设（留采购件余量）。这不是保证上限，实际必须称重并重算。',
 f'平地假设滚阻系数0.03、加速度0.25m/s²：F=m(gCrr+a)={force:.3f}N；每后轮需求转矩F×0.021/2={torque:.5f}N·m。未包含斜坡、轴不平行或轮子打滑。',
 f'参考电机6V堵转扭矩0.39kg·cm，5.5V线性估计0.0351N·m；堵转扭矩不是允许持续转矩，PWM和负载曲线需实测。不能据此宣称物理通过。',
 f'5.5V参考空载轮速上界约{no_load:.2f}m/s。默认45%PWM且每轮停转采样，平均速度明显更低；不承诺0.5m/s，验收按实测记录。',
 f'参考电机每路堵转约{current_per:.3f}A，低于DFR1063标称1.7A/路；两个电机加0.30A控制预算约{ELECTRICAL["outputPeakEstimateA"]}A。不能给未知12V电机借用这个结论。',
 '8节NiMH经降压5.5V供VIN与内置电机驱动；电池电压必须比输出至少高1.5V。USB与外部电源不同时使用；上电/复位瞬态待测试。',
 '强度均值+迟滞+先安静再启用+默认5秒保护；停驱250ms后采样约64ms，再驱动160ms。软件周期约474ms加开销；不是实测停车时间。',
 '免焊指购买成品排针、带抑噪接口板的预接线电机、加工端头线束；需要螺丝刀、卡尺、万用表，不能把裸线插PCB焊孔。',
 '当前采购闭环仍待：预接线电机具体在售SKU/配套轮、降压外尺寸、电池盒外尺寸、开关/按钮成品包络；未确认前不要下单整套或打印全部。',
]
engineering={'status':'PROTOTYPE_AWAITING_PROCUREMENT_FIT_AND_PHYSICAL_TEST','summary':summary,
 'massDesignAssumptionKg':mass_bound,'rollingCoefficientAssumption':rr,'accelerationTargetMps2':accel,
 'forceRequiredN':force,'torquePerMotorNm':torque,'noLoadWheelSpeedMps':no_load,'electrical':ELECTRICAL,
 'physicalTests':{'sound':'NOT_RUN','temperature':'NOT_RUN','startup':'NOT_RUN','stoppingDistance':'NOT_RUN','fit':'NOT_RUN'},
 'sources':[{'url':p['source'],'purpose':p['name']} for p in M['parts'] if p['source'].startswith('https://')]}
(OUT/'checks/engineering.json').write_text(json.dumps(engineering,ensure_ascii=False,indent=2),encoding='utf8')
M.update(assembly=S,connections=W,bom=B,engineering=engineering,budgetAllocationCny=total,
  procurementStatus='CONFIRM_LISTED_VARIANTS_BEFORE_FULL_PRINT',
  diagramLabels={
    'battery_holder':{'title':'8 × AA 镍氢','sub':'9.6V 标称 · 不直接接电机'},
    'power_switch':{'title':'带线开关 / 保险','sub':'1A 慢熔 · 无需焊接'},
    'regulator':{'title':'DFR0379 降压','sub':'先调5.5V · 螺丝端子'},
    'microphone':{'title':'DFR0034 声音强度','sub':'V2 3.3V · 成品Gravity线'},
    'esp32':{'title':'Romeo mini ESP32-C3','sub':'DFR1063 · 已集成双路驱动'},
    'arm_button':{'title':'免焊 ARM 按键','sub':'干接点 · GPIO6至GND'},
    'motor_L':{'title':'左预接线 N20','sub':'6V / 50:1 · PH2.0'},
    'motor_R':{'title':'右预接线 N20','sub':'6V / 50:1 · 先架空试转'},
  })
M.pop('wireDisplay',None)
report_path=OUT/'checks/wire-display.json'
if report_path.exists():
    report=json.loads(report_path.read_text(encoding='utf8'))
    bindings={p['id']:{'stl':p['sha256']['stl'],'step':p['sha256']['step'],'position':P[p['id']]['position'],'rotation':P[p['id']]['rotation']} for p in M['cadParts']}
    if report.get('modelBindings')==bindings:M['wireDisplay']=report

for filename,columns,rows in [
 ('BOM.csv',['零件','数量','规格/免焊采购条件','预算单价CNY_非报价','厂家参考','采购状态'],[[x['name'],x['qty'],x['spec'],x['budgetCny'],x['url'],x['procurementStatus']] for x in B]),
 ('connections.csv',['编号','起点部件','端子','终点部件','端子','AWG','类别','注意'],[[x['id'],x['from']['partId'],x['from']['terminal'],x['to']['partId'],x['to']['terminal'],x['wireAwg'],x['kind'],x['note']] for x in W])]:
    with (OUT/filename).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(columns);writer.writerows(rows)

escape=html.escape
svgrows=[]
for i,w in enumerate(W):
    y=150+i*62
    a=M['diagramLabels'][w['from']['partId']]['title'];b=M['diagramLabels'][w['to']['partId']]['title']
    svgrows.append(f'<g><text x="24" y="{y}">{w["id"]}</text><text x="85" y="{y}">{escape(a+" / "+w["from"]["terminal"])}</text><path d="M465 {y-4}H650" stroke="{w["color"]}" stroke-width="3"/><text x="505" y="{y-14}" font-size="12">{w["wireAwg"]} AWG</text><text x="675" y="{y}">{escape(b+" / "+w["to"]["terminal"])}</text></g>')
(OUT/'wiring.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1180" height="1110" viewBox="0 0 1180 1110"><rect width="1180" height="1110" fill="#111824"/><g fill="#e7edf6" font-family="Microsoft YaHei,Arial,sans-serif" font-size="14"><text x="24" y="45" font-size="28">ECHO F1 / CN V2 · 免焊逐线接线图</text><text x="24" y="83">先断电 · 电池先降压到5.5V · 传感器只接3.3V · USB与外部电源互斥</text>{"".join(svgrows)}<text x="24" y="1060" fill="#ffc579">控制电机的GPIO1/0/10/2已在DFR1063板内接好，不再外接驱动板。不把8AA直接接6V电机。</text></g></svg>',encoding='utf8')

for f in ['main.py','config.py','controller.py','test_controller.py']:shutil.copyfile(ROOT/'firmware/echo-f1-cn'/f,OUT/'firmware'/f)
test=subprocess.run([sys.executable,str(ROOT/'firmware/echo-f1-cn/test_controller.py')],capture_output=True,text=True)
(OUT/'checks/firmware-tests.txt').write_text(test.stdout+test.stderr,encoding='utf8');assert test.returncode==0

prints=''.join(f'<tr><td>{escape(p["name"])}</td><td>{" × ".join(map(str,p["sizeMm"]))}</td><td>{escape(p["orientation"])}</td><td><a href="{p["file"]}">STL</a></td></tr>' for p in M['printParts'])
buys=''.join(f'<tr><td>{escape(p["name"])}</td><td>{p["qty"]}</td><td>{escape(p["spec"])}</td><td>{p["budgetCny"]}</td></tr>' for p in B)
steps=''.join(f'<section><span>STEP {i+1:02d}</span><h2>{escape(s["title"])}</h2><p>{escape(s["text"])}</p><ul>'+''.join(f'<li>□ {escape(c)}</li>' for c in s['checks'])+f'</ul><small>工具：{escape(s["tools"])}</small></section>' for i,s in enumerate(S))
doc=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ECHO F1 · 大陆易装版 V2</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f6f7fa;color:#1e2836;font:15px/1.85 -apple-system,'Microsoft YaHei',sans-serif}}main{{max-width:1100px;padding:40px 28px;margin:auto}}h1{{font-size:54px;line-height:1.1;letter-spacing:-.04em}}h2{{font-size:25px}}section{{padding:28px 0;border-bottom:1px solid #dce0e7}}header{{padding:30px 0}}header span,section>span{{color:#bf2846;font-weight:700;font-size:11px;letter-spacing:.13em}}.notice{{background:#fff0db;border-left:4px solid #c7822c;padding:20px}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:10px;border-bottom:1px solid #d8dce4;text-align:left;vertical-align:top}}a{{color:#ac2140}}small{{color:#69778a}}img{{width:100%}}code{{background:#e8eaf0;padding:3px}}@media print{{section{{break-inside:avoid}}body{{background:white}}h1{{font-size:34px}}}}
</style><main><header><span>M4KE / MAINLAND BUILD EDITION 02</span><h1>ECHO F1.<br>少一点焊接，多一点动手。</h1><p>ESP32-C3 · 红黑PLA · 带线电机 · 相对声音强度 · 分段打印</p></header>
<div class="notice"><b>独立新版，旧版保留。可下载打印原型件，不等于整车实测通过。</b><br>尺寸包络约 {" × ".join(map(str,M["dimensionsMm"]))} mm。采购预算分配 ¥{total:g}，不含运费和工具、不是实时成交价。所列预接线电机具体在售SKU、轮子咬合、降压模块和电池盒尺寸仍须核对；不要直接照旧购物车全选结算。</div>
<section><h2>与旧版相比</h2><ul><li>保留ESP32，但换用已入购物车DFR1063一体板，省独立驱动板和四根控制线。</li><li>用3.3V Gravity声音强度模块替代Adafruit裸排针麦克风，固件算法同步更换。</li><li>驱动轮买N20配套42×19成品轮，不再需要进口Pololu轮毂；前轮保留已选693ZZ与O形圈。</li><li>不要购买旧12V/500rpm电机。这里只按6V低电流、工厂预接线带抑噪接口版本设计，同名N20不能盲换。</li><li>8节镍氢先降到5.5V再供一体主板与电机，全部通过成品线和螺丝端子连接。</li><li>约28.6cm长车身，底盘、外壳拆成两段；单件XY均在180mm范围内，仍须在实际切片器检查边裙/支撑余量。</li></ul></section>
<section><h2>先买什么，暂缓什么</h2><p>DFR1063主板、693ZZ轴承、40×3橡胶圈可以沿用已有清单。电机+配套轮要确认成品线接口和电流，电池盒/降压按包络核尺寸再买。没有联系卖家，没有更改购物车或下单。</p><p>淘宝搜索词：<b>DFR1063 Romeo mini；DFR0034 V2 3.3V 带线；N20 6V 50比1 PH2.0 带接口 抗干扰；N20 42x19 3mm D孔配套轮；DFR0379；8节AA平铺电池盒带线。</b>不要只看商品标题，要选择对应SKU和成品线版本。</p><table><tr><th>材料</th><th>数量</th><th>尺寸/版本/免焊要求</th><th>预算单价¥</th></tr>{buys}</table><p><a href="BOM.csv">完整采购表</a>。整套预计¥{total:g}材料预算，现货与运费未核实；数字万用表、卡尺、小螺丝刀需另备。</p></section>
<section><h2>打印件</h2><p>只打印print/目录，不打印采购件参考网格。单位mm，100%缩放。PLA、0.4mm喷嘴、0.20mm层高、4壁、5层顶底，底盘35%填充、隔套100%；外壳树状支撑只接触热床。H2C或其它打印机均可选，未预设机型。</p><p><a href="print/00_fit_coupon.stl">先打公差试片</a>，孔径依次3.2/3.3/3.4/8.1/8.2mm。打印机校准及切片尚未替你完成；每件都要看首层、悬垂和支撑。</p><table><tr><th>件</th><th>打印包络mm</th><th>方向</th><th>文件</th></tr>{prints}</table></section>
<section><h2>线路：一根一根接</h2><p>只使用成品模块和已加工线头，无用户焊接步骤。不得把杜邦线插进裸焊孔；电源电机线用22AWG和接线端子。图是连通关系，针位以厂家丝印为准。</p><a href="wiring.svg"><img src="wiring.svg" alt="14条免焊连接"></a><a href="connections.csv">逐线表</a><p>3D线路只是避碰示意，端点不等于实际针脚；未模拟接头体积、线弯曲半径和所有安装工具。合壳前务必用手确认没有夹线。</p></section>
{steps}
<section><h2>固件，不能沿用V1文件</h2><ol><li>电池断开，USB-C接电脑。在Thonny安装<a href="https://micropython.org/download/ESP32_GENERIC_C3/">ESP32_GENERIC_C3官方MicroPython</a>。</li><li>将本包firmware中的main.py、config.py、controller.py保存到设备根目录；不要装WROOM-32版引脚文件。</li><li>默认commissioning只允许短时架空试车。阈值5000/3000只是示例，必须根据INTENSITY实测重设，不是60dB。</li><li>真实静音测量期间电机会暂停；此方式降低自激风险，但不保证传感器断线被完全识别，仍需成人和总开关监督。</li><li>完成物理清单后才能显式设置PROFILE='continuous_while_loud'和HARDWARE_CHECKED=True。停机不等于瞬间停稳。</li></ol></section>
<section><h2>计算依据与还没证明的事</h2><ul>{''.join('<li>'+escape(s)+'</li>' for s in summary)}</ul><p><a href="checks/geometry.json">几何检查</a> · <a href="checks/engineering.json">计算JSON/来源</a> · <a href="checks/firmware-tests.txt">固件逻辑测试</a></p><p>CAD和固件由本次设计编写，不作为Qwen自主设计成功的证据。</p></section>
<section><h2>你装完后填写的验收表</h2><table><tr><th>项目</th><th>实测记录</th></tr>{''.join('<tr><td>'+x+'</td><td>未测试 / 待填写</td></tr>' for x in ['所有采购包络和安装配合','20次上电/复位，车轮不意外转','20次声控启动/安静停车，无自激','1m用时与平均速度','撤去声音至停稳时间/距离','5分钟温升、主板是否复位','轮、线束和紧固件无松脱'])}</table></section>
<footer><small>原创代码/CAD按项目MIT许可。厂家文档只链接，不复制资产。source/附生成器，可追溯和重新出件。</small></footer></main></html>'''
if M.get('appearance'):
    finish=M['appearance']
    links=''.join(f'<li><a href="{escape(a["file"])}">{escape(a["label"])}</a>：AMS {escape(a["slot"])} / {escape(a["filament"])}。{escape(a["note"])}</li>' for a in finish['artifacts'])
    doc=doc.replace('</header>', '</header><section id="appearance"><h2>'+escape(finish['title'])+'</h2><p>'+escape(finish['summary'])+'</p><p>'+escape(finish['previewNote'])+'</p><ul>'+links+'</ul><p>本机配色用上面两份 H2C 工程，替代下方通用红黑工程。打开后仍须同步 AMS、切片并核对实际料槽。不含 G-code；不启动打印机。所有承力件用白色 PLA Basic，灰烬红 Silk 只用于外壳。原版工程保留，不改尺寸和孔位。</p></section>')
(OUT/'instructions.html').write_text(enrich_document(doc,M),encoding='utf8')
(OUT/'START-HERE.txt').write_text('ECHO F1 CN V2 / 新手从这里开始\n1. 打开 instructions.html，找到排盘打印章节。\n2. 在 plates/ 中只选与你打印机相符的整套3MF，以项目方式打开，不是逐个导入STL。\n3. 0.4mm喷嘴 / PLA / 纹理PEI；保持mm与100%比例。实际配置不同必须修改并重切片。\n4. 先只切片和打印第1盘公差试片，再核对实物采购件，之后依次打剩余各盘。\n5. 红黑分盘，单料槽、手动按盘换色，不需要AMS。工程未切片，不含G-code，不会自动打印。\n6. 跟着教程装配、接线、烧录、架空试车。USB烧录必须断开电池。\n7. 采购配合和物理测试仍待完成。单件STL在print/，仅供补打备用。\nApp: http://127.0.0.1:4176/?build=echo-f1-cn-v2&view=print\n',encoding='utf8')
(OUT/'source').mkdir(exist_ok=True)
for f in ['echo_f1.py','echo_f1_cn.py','echo_f1_cn_package.py','echo_f1_wiring.py','README.md']:shutil.copyfile(ROOT/'cad/designs'/f,OUT/'source'/f)
for f in ['authored_plates.py','build_handbook.py','echo_finish.py']:shutil.copyfile(ROOT/'printing'/f,OUT/'source'/f)
(OUT/'source/REGENERATE.txt').write_text('Run from the M4KE repository, not from the extracted build package:\n1. python cad/designs/echo_f1_cn.py\n2. python printing/authored_plates.py --slicer-root /path/to/official/BambuStudio\n3. python cad/designs/echo_f1_cn_package.py\n4. python cad/designs/echo_f1_wiring.py --build echo-f1-cn-v2\n5. python cad/designs/echo_f1_cn_package.py\n6. python tests/verify-print-plates.py\n7. python tests/verify-cn-build.py\nPlate generation requires official resources/profiles/BBL, and resets native-validation status; do not reuse previous slicing evidence for changed meshes. Optional native checks: tests/slice-print-plates.py. Repackage after checks to include fresh records.\nDependencies and DLL setup: source/README.md. Firmware source: firmware/echo-f1-cn/.\n',encoding='utf8')
shutil.copyfile(ROOT/'LICENSE',OUT/'LICENSE')
if M.get('appearance'):
    start=OUT/'START-HERE.txt'
    start.write_text('本机配色更新：灰烬红 × 冰白。\n先看 instructions.html 的配色章节。第1–3盘用 WHITE-STRUCTURE 工程 / A4白色PLA Basic；第4盘用 EMBER-BODY 工程 / A1灰烬红PLA Silk。\n原版红黑工程保留作备用。配色工程没有发往打印机；已完成的试片无需重打。\n\n'+start.read_text(encoding='utf8'),encoding='utf8')
    regenerate=OUT/'source/REGENERATE.txt'
    regenerate.write_text(regenerate.read_text(encoding='utf8')+'\nOptional current finish: after step 2, run python printing/echo_finish.py --slicer-root /path/to/official/BambuStudio, then package again. Original mesh geometry is preserved.\n',encoding='utf8')
shutil.copyfile(ROOT/'procurement/ECHO-F1-CN-v2-buying-guide.txt',OUT/'BUYING-GUIDE.txt')
M['packageStatus']='READY_FOR_FIT_CHECK'
(OUT/'manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2),encoding='utf8')
# Keep old downloads on disk for diagnosis, but never redistribute obsolete
# broken revisions in the beginner package. Only manifest-listed 3MFs ship.
current_3mfs={p['file'] for p in M.get('printPlan',{}).get('projects',[])}
if not current_3mfs:
    current_3mfs={p['file'] for p in json.loads((OUT/'plates/print-plan.json').read_text(encoding='utf8'))['projects']}
current_3mfs.update(p['file'] for p in M.get('appearance',{}).get('artifacts',[]))
files=[p for p in OUT.rglob('*') if p.is_file() and p.suffix!='.zip' and p.name!='SHA256SUMS.json' and '__pycache__' not in p.parts
       and (p.suffix.lower()!='.3mf' or p.relative_to(OUT).as_posix() in current_3mfs)]
hashes={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(OUT/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2),encoding='utf8')
with zipfile.ZipFile(OUT/'ECHO-F1-build-package.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[OUT/'SHA256SUMS.json']:z.write(p,'ECHO-F1-CN-v2/'+p.relative_to(OUT).as_posix())
with zipfile.ZipFile(OUT/'ECHO-F1-build-package.zip') as z:assert z.testzip() is None
print(json.dumps({'parts':len(M['parts']),'printParts':len(M['printParts']),'budgetCny':total,'connections':len(W),'steps':len(S),'packageBytes':(OUT/'ECHO-F1-build-package.zip').stat().st_size},indent=2))
