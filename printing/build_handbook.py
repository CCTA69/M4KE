"""Beginner-facing, offline printable instructions shared by the build package."""
import html

def printing_section(plan):
    cards=[]
    for project in plan['projects']:
        plates=''.join(f'<article class="plate"><h3>{html.escape(p["title"])}</h3><img src="{p["preview"]}" alt="该盘零件占位示意"><small>俯视占位示意，不是切片预览</small><ol>'+''.join(f'<li>{html.escape(x["name"])} ×1 <code>{x["id"]}</code></li>' for x in p['parts'])+'</ol><p>□ 已打印　□ 已清点　□ 已试配</p></article>' for p in project['plates'])
        cards.append(f'<details><summary><b>{html.escape(project["label"])}</b> · {len(project["plates"])}盘 · 0.4mm / PLA / 纹理PEI</summary><p><a class="button" href="{project["file"]}">下载整套排盘 3MF</a></p><div class="plates">{plates}</div></details>')
    return '''<section id="printing"><span>从零开始 / PRINTING</span><h2>不要一个一个导入 STL。打开整套排盘工程。</h2>
<p>先按你的打印机选择下方工程。切片器内使用英文零件ID以避免系统乱码，上方盘号和下方清单提供中文对应。所有零件已经保留1:1毫米尺寸、摆放方向、分盘和每件参数，包含18个打印件及1个公差试片。只打印工程里的打印件，不打印电机、主板等采购参考模型。</p>
<p><b>请使用文件名含 -r2.3mf 的修订版。</b>旧版的耗材变体索引不完整，可能出现“配置文件无效 / 此文件没有任何几何数据”；R2修正映射及填充图案枚举。不是缺少STL，也不需要手动逐个导入。</p>
<div class="notice"><b>这是可编辑、未切片的3MF项目，不是直接执行的打印代码。</b>没有连接打印机、没有发起打印。实际机型、喷嘴、耗材、热床和支撑必须在你自己的切片器中确认。采购件尺寸不确定时，只先打试片。</div>
<p>H2C当前预设切片估算约419g（含试片、支撑和裙边），建议预留黑色PLA至少300g、红色至少250g；不是两整卷用量承诺，其他机型以实际切片为准。</p><h3>第一次操作，逐步照着做</h3><ol>
<li><b>准备打印机。</b>确认喷嘴是0.4mm、热床是纹理PEI板、耗材是1.75mm PLA。红黑分别单盘打印，不需要AMS。若实际配置不同，必须先修改切片器预设；不要使用别的机型的G-code。</li>
<li><b>安装 Bambu Studio。</b>从<a href="https://bambulab.com/zh-cn/download/studio">官方页面</a>安装；启动向导勾选实际机型。不需要为了打开项目购买云服务。</li>
<li><b>只下载一个对应机型的3MF。</b>在 Studio 选择“文件 → 打开项目”。若出现“导入几何 / 打开项目”选择，选“打开项目”；这样保留盘号和参数，不是把整车合成一个块。</li>
<li><b>检查左侧设置。</b>机型、0.4mm喷嘴、热床必须与实物一致；耗材替换成你手中的PLA预设。项目只有1个料槽，每盘手动装对应颜色。不会在同一盘内自动换红黑。</li>
<li><b>别再点自动朝向，也别缩放。</b>文件已按打印朝向放平；上方显示100%比例、单位mm。每件已指定4壁、5层顶底及25–100%填充；需要的件设了自动树状支撑与4mm外侧裙边。</li>
<li><b>先只切第1盘“公差试片”。</b>选择该盘，点“切片单盘”。在预览拖动层高滑块检查首层和顶部；不能有“超出热床 / 空层 / 悬空 / 冲突”等未处理警告。正常切片的估计时间和克数不是实测结果。</li>
<li><b>你确认后才开始打印。</b>装黑PLA，清空热床，按打印机手册清洁、校准。根据你的设备采用官方发送或存储卡方式。注意热床、喷嘴温度；查看首层是否粘牢，失败就停止。</li>
<li><b>冷却后试配。</b>试片孔径为3.2/3.3/3.4/8.1/8.2mm。M3螺钉应能穿过合适的孔，693ZZ轴承应可手压就位、不明显晃动。过紧不敲击轴承；先处理毛刺、校准挤出或孔补偿，并重打试片。不要缩放整车。</li>
<li><b>确认采购件，再按盘打印。</b>电机、配套轮、降压板、电池盒和按钮实际尺寸与BOM一致才继续。每盘打印前确认颜色，取走上一盘的成品、支撑和废料；红色盘换红PLA，黑色盘换黑PLA。</li>
<li><b>拆支撑、清点、分袋。</b>等冷却后轻拆支撑；远离眼睛操作，必要时戴护目镜。孔和装配面清理平整。两只小轴承隔套不是废料，不要丢；按下方盘号和装配步骤放好。</li>
</ol>'''+''.join(cards)+'''<h3>打印不顺利，先处理什么？</h3><table><tr><th>现象</th><th>处理方式</th></tr>
<tr><td>模型出现在盘外 / 所有件挤一盘</td><td>关闭但不要保存错误导入，重新“打开项目”，不要只导入几何。确认你下载的是对应机型，不点缩放适配。</td></tr>
<tr><td>零件粘在一起 / 裙边接触</td><td>先看切片预览。有支撑或裙边越界就暂停；减小裙边、拆分该盘或重新排盘后再切片。模型间距检查不代表支撑也已通过。</td></tr>
<tr><td>首层不粘 / 翘边</td><td>停止该盘，按厂商说明清洁热床，核对耗材预设、板型及首层校准，先重打试片，不靠继续堆料补救。</td></tr>
<tr><td>孔太紧 / 螺母槽不合</td><td>只先打印试片，去毛刺并测量；需要修配或孔补偿时保留外形尺寸，不把整个工程缩小或放大。</td></tr>
<tr><td>外壳底部悬空</td><td>确认支撑开关及“树状自动 / 仅接触热床”；逐层预览。若仍有无法承托的区域，停止并调整支撑，不把警告当通过。</td></tr></table></section>'''


def firmware_section():
    return '''<section id="firmware"><span>FIRMWARE / 不需要写程序</span><h2>把程序放进主板：一次只接一种电源。</h2>
<div class="notice">当前主板是DFR1063 / ESP32-C3，不是旧版WROOM-32。烧录时拔掉电池，用USB供电；试转时拔USB再接电池。不要同时接入两路电源。下面的程序为本版已有文件，不需要复制聊天里的代码。</div>
<h3>A. 准备电脑和主板</h3><ol><li>在<a href="https://thonny.org/">Thonny官网</a>安装Thonny。在下方下载三个.py文件，放在同一个电脑文件夹，保持文件名不变。</li><li>拔掉车上的外部电池。USB-C数据线接主板和电脑。如果没有识别，先换一根确认能传数据的线，不购买新板解决线材问题。</li><li>Thonny里打开“工具 → 选项 → 解释器”，选择 MicroPython (ESP32)，选择新出现的串口。不同版本界面措辞可能略有不同。</li><li>点击安装或更新MicroPython，目标必须选 <b>ESP32_GENERIC_C3</b>；官方固件在<a href="https://micropython.org/download/ESP32_GENERIC_C3/">这里</a>。刷写会覆盖主板现有程序，有其他程序先备份。</li><li>如果连接失败，按住主板BOOT，轻按RST，再松开BOOT，重新选串口；不要在电池连接时这样操作。</li></ol>
<h3>B. 保存三个文件到设备</h3><p><a href="firmware/config.py">config.py</a> · <a href="firmware/controller.py">controller.py</a> · <a href="firmware/main.py">main.py</a>（网页打开成文本时，右键“链接另存为”，不要保存成.py.txt。）</p><ol><li>在Thonny打开 config.py，选择“文件 → 另存为 → MicroPython设备”，文件名设为 <code>/config.py</code>。</li><li>同样保存 <code>/controller.py</code> 和 <code>/main.py</code>。不是只保存在电脑里；在“查看 → 文件”里的设备根目录检查三个文件都在。</li><li>先不改默认保护：<code>PROFILE='commissioning'</code>、<code>HARDWARE_CHECKED=False</code>、<code>PWM_DUTY=0.45</code>。这时还不允许持续运行。</li><li>在USB供电状态下复位，终端应看到 <code>ECHO F1 CN V2</code> 和 <code>INTENSITY=</code> 输出；缺少模块时检查三个文件名及保存位置。</li></ol>
<h3>C. 先采声音，再架空试转</h3><ol><li>仍只接USB，不接电池。在安静房间记录 INTENSITY 的波动，再从你预计的距离发声，记录发声范围。不要把这些计数当成分贝。</li><li>在config.py中把 <code>THRESHOLD_ON</code> 设到“高于安静最大值、低于目标声音最小值”的位置；<code>THRESHOLD_OFF</code> 要小于ON且高于安静噪声。没有分离范围就先换位置或隔振，不强凑阈值。原5000/3000只是示例。</li><li>保存config.py到设备，断电。把驱动轮架空，确保头发、手和线束离开车轮；拔USB，再接经过5.5V降压的电池。</li><li>打开总开关，车应保持停止。按ARM一次，先安静，再发声；声音达到门槛才转。再次按ARM或关总开关应停止。默认持续响声触发约5秒后停机；先安静再发声可重新触发，按ARM可解除使能。</li><li>若某侧向后转：关总开关、拔电池，之后再接USB。只在config.py里把对应 <code>LEFT_FORWARD</code> 或 <code>RIGHT_FORWARD</code> 在0和1之间切换，保存后重新架空测试。不要带电换线。</li><li>检查静音后能停、电机声音不会不断触发自己。当前程序会短暂关电机采样，所以运动有停顿；这不是恒速车。调试无法避免自激时先停用，改善隔振或降低PWM再试。</li></ol>
<h3>D. 通过实测后，才解除短时限制</h3><p>完成后面的20次启停、20次复位、停车距离和温升记录，确认没有自激、复位和夹线，才将 <code>PROFILE='continuous_while_loud'</code>、<code>HARDWARE_CHECKED=True</code> 保存到设备。这个开关是你对实际检查的确认，不是软件自动给的合格证。</p>
<table><tr><th>故障</th><th>先做什么</th></tr><tr><td>USB能连，电机不转</td><td>USB本来不提供电机VIN。断USB后接经过降压的电池；确认ARM、先安静再发声和5秒限制。断电后检查M1/M2与VIN接线。</td></tr><tr><td>安静时还转</td><td>立即关总开关。检查阈值、噪声和传感器接地；把麦克风与电机振动隔开，降低PWM。不要用持续模式掩盖故障。</td></tr><tr><td>一启动就重启</td><td>停止测试，检查电池、5.5V输出、接触不良、电机堵转或短路。别增大保险丝或直接旁路降压。</td></tr><tr><td>主板烫 / 有气味 / 线发热</td><td>立即断开电池，等待冷却后检查。不要继续反复上电试运气。</td></tr></table></section>'''

def enrich_document(doc, manifest):
    plan=manifest.get('printPlan')
    extra='''<style>.plates{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}.plate{padding:18px;background:#eef1f6;border-radius:12px}.plate img{height:190px;object-fit:contain}.plate small{display:block;text-align:center}.plate ol{font-size:12px}details{border:1px solid #d3dae6;padding:16px;margin:15px 0;border-radius:12px}summary{cursor:pointer}.button{display:inline-block;background:#be2948;color:white;padding:9px 15px;border-radius:8px;text-decoration:none}nav{display:flex;gap:14px;flex-wrap:wrap;background:white;padding:18px;border-radius:12px}li{margin-bottom:8px}code{overflow-wrap:anywhere}@media print{details:not([open])>*:not(summary){display:block!important}.plates{display:block}.plate{break-inside:avoid}}@media(max-width:600px){h1{font-size:36px}main{padding:20px 16px}table{font-size:10px}td,th{padding:6px}}</style>'''
    doc=doc.replace('</style><main>','</style>'+extra+'<main>',1)
    doc=doc.replace('</header>','</header><nav aria-label="教程目录"><a href="#printing">① 排盘打印</a><a href="#assembly">② 装配动画与步骤</a><a href="#wiring">③ 接线</a><a href="#firmware">④ 烧录与调试</a><a href="#acceptance">⑤ 实测记录</a></nav>',1)
    if plan:
        a=doc.index('<section><h2>打印件</h2>');b=doc.index('<section><h2>线路：',a)
        backup=doc[a:b].replace('<section><h2>打印件</h2>','<details><summary>高级备用：单件STL和方向说明</summary>').replace('</section>','</details>')
        doc=doc[:a]+printing_section(plan)+backup+doc[b:]
    doc=doc.replace('<section><h2>线路：','<section id="wiring"><h2>线路：',1)
    doc=doc.replace('<section><span>STEP 01','<section id="assembly"><h2>逐步装配</h2><p>在本机已启动的M4KE中打开 <a href="http://127.0.0.1:4176/?build=echo-f1-cn-v2&amp;view=assemble">3D装配动画</a>。离线时按下面11步，核对采购件和打印件名称；动画是装配示意，不证明手或工具一定可达。</p></section><section><span>STEP 01',1)
    a=doc.index('<section><h2>固件，不能沿用V1文件');b=doc.index('<section><h2>计算依据',a)
    doc=doc[:a]+firmware_section()+doc[b:]
    return doc.replace('<section><h2>你装完后填写的验收表','<section id="acceptance"><h2>你装完后填写的验收表',1)

