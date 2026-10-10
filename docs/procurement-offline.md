# 中国采购候选与离线价格快照

## 2026-10-10 China car price observations

The existing `sound-car-v1` reference uses one headerless Pico, one Adafruit
#1063 microphone, one Pololu #2130 driver, two #1098 motors, two #1420 wheels,
two #1086 brackets and one #950 caster. Wheels and brackets are sold as pairs.
This is a reference-kit comparison, not the active project's generated BOM.
Power/control candidates, wiring, fasteners and printed-material consumption still
need their own revision-matched purchase list. No hardware was substituted.

| Exact model | China-market observation | Limitation |
| --- | --- | --- |
| Pico / element14 3643332 | CNY 29.25 before tax; displayed 33.0525 including tax | Web extraction, not a successful direct refresh; exact R3 revision unknown |
| Adafruit 1063 / DigiKey 1528-1013-ND | CNY 57.48 at quantity 1, including 13% VAT | Opened-page extraction; an older search result said 57.47; not a live quote |
| Pololu 2130 / LCSC C6661942 | CNY 65.88 advertised in structured metadata | Out of stock; quantity tiers and tax unconfirmed |
| Pololu 1098, 1420, 1086, 950 | No verified CNY quantity price found | USD/JPY prices and lookalike products excluded |

Sources: [element14 China](https://www.element14.cn/en-CN/c/raspberry-pi/raspberry-pi-boards/prl/results),
[DigiKey China](https://www.digikey.cn/zh/products/detail/adafruit-industries-llc/1063/4990762),
[LCSC](https://item.szlcsc.com/7616935.html). China-market pricing does not establish
domestic warehouse inventory. These are dated observations, not checkout quotes.

Install the included factual transcriptions locally (no supplier network calls):

```sh
node procurement/install-china-car-observations.mjs
# Set this environment variable before starting both the web server and MCP process:
export M4KE_PROCUREMENT_SNAPSHOT_SHA256=84c83ae3c682b12461bdbe328fd7cdaace328762d1d0b330fb75946910c473e8
npm start
```

PowerShell uses `$env:M4KE_PROCUREMENT_SNAPSHOT_SHA256='84c83ae3c682b12461bdbe328fd7cdaace328762d1d0b330fb75946910c473e8'`.
The installer prints the digest; use that result if the transcription changes.
It preserves incoming bundles and imports idempotently by content hash. It does
not change any running service or copy evidence to the DGX. Apply the same pin
to each deployed process and restart under the deployment owner's control.
Both HTTP and standalone MCP load the project-root `.env` before constructing
their procurement runtime. The selected pin is validated and fixed for that
runtime; later environment changes do not switch search, quote or HTTP sources.
An explicitly set process environment value takes precedence over `.env`.

The three source extracts are deliberately `web-extract`, including the LCSC
metadata transcription: their hashes verify these texts, not original supplier
HTML. They display in the existing procurement panel and cached MCP search, but
freshness remains UNKNOWN and quantity quotes remain UNQUOTABLE. The original
LCSC HTML hash is recorded for audit; the private HTML is not redistributed.
This dataset therefore has **zero currently quotable lines**, three historical
price observations and four missing model prices. It must not display a total
of zero or the three observations added together as the car cost.

The service accepts only a startup-configured SHA256, never a browser-supplied
path or URL. Blank configuration preserves the old historical snapshot. Missing
or modified evidence returns 503 without fetching or silently switching sources.
The UI accepts 1–100 verified entries rather than one hard-coded four-item pin;
the same selected pin is used by MCP cached search and quantity quotes.

`procurement/car-prices.mjs` contains explicit identity/variant and purchase-unit
bindings for the reference, including explicit package descriptions (`One board`,
`One motor`, `One pair`, `One caster`). Import new, reviewed supplier evidence to update
prices. Different supplier names/variants or pack sizes need a reviewed binding
change; catalog association alone is insufficient. Multiple exact candidates
remain ambiguous. Partial subtotals use decimal arithmetic and separate tax
bases; stale, web-extracted, advertised, insufficient-stock, out-of-stock and
unknown-order-rule/tax lines are excluded. Unknown, expired or backorder stock and
stock measured in a different unit are also excluded. Shipping and complete build cost are
always unresolved in this reference comparison.

Validation: `node --test tests/china-car-pricing.test.mjs` covers two motors vs
one wheel pair, wrong identity/currency/unit/market, stale or extracted evidence,
stock, tax separation, ambiguous sources, installation and post-import tampering.
`node tests/procurement-e2e.mjs` renders the real panel and imported observations
in English and Chinese, then verifies that a tampered source clears displayed prices.
`node --test tests/procurement-startup.test.mjs` starts the production server in
an isolated directory with a real `.env`, checks HTTP/MCP pin agreement, and
covers frozen runtime settings, invalid/missing pins and environment precedence.

## 历史记录：2026-09-27 初始离线快照

`procurement/` 是独立、离线、可验证的**供应商观察数据入口**。它不修改现有九项来源目录、不改变车的选型、不连接购物车、不下单，也没有声称已经把嘉立创 MCP 接入应用。review-03 发布包保持原样，本新增目录尚未加入该包。

2026-09-27 08:48:16 UTC，通过无登录的普通 HTTPS GET 取得三个官方页面/PDF，保存原始字节和 SHA256。随后离线读取网页内的 JSON，而不是执行 JavaScript，将四项观察规范化。实际抓取均 HTTP 200，未遇到登录阻断；**缺少普通价格阶梯、库存字段矛盾和未选定 SKU 是数据缺口，不能谎称为权限问题。**

| 候选 | 供应商标识 | 已观察的人民币信息 | 仍未知 / 禁止推断 |
|---|---|---|---|
| Raspberry Pi Pico，无排针 | element14 中国，3643332；MPN `RASPBERRY PI PICO` | 1 个起，CNY 29.25/个，未税；同页含税 33.0525；最小量/增量均 1 | 库存、运费、交期、确切硬件修订；不能自动认定是当前 R3 STEP 对应版本 |
| Pico H，有排针 | element14 中国，3996081；MPN `RASPBERRY PI PICO H` | 1 个起，CNY 36.58/个，未税；同页含税 41.3354 | 与无排针版不同；不替换已生成的 Pico R3 |
| TI DRV8833PWPR 裸芯片 | 立创商城 C50506，TSSOP-16-EP | 页面结构化数据广告价 CNY 7.27 | 普通数量阶梯/税/订购增量未证实；库存字段 8077 与 7328 不同，故规范化库存为 UNKNOWN。不是 Pololu #2130 模块，不能按此给整板报价 |
| Bambu PLA Basic | 制造商 TDS V3.0；未选定颜色/线盘 SKU | 无已取得的 CNY 价格 | 只有材料规格，不能用美元价格换算假装中国报价，不能据典型拉伸试样数值宣布实物强度合格 |

一手来源：[element14 中国列表](https://www.element14.cn/en-CN/c/raspberry-pi/raspberry-pi-boards/prl/results)、[立创 C50506](https://item.szlcsc.com/51516.html)、[Bambu PLA Basic TDS](https://store.bblcdn.com/s7/default/b189de92249a4b9ebed28b8ea1f080f0/Bambu_PLA_Basic_Technical_Data_Sheet.pdf)。价格仅描述捕获时的页面，不是当前承诺；默认 24 小时后不再计算参考小计。

## 可复现的离线使用

在项目根目录执行，无新增 npm/Python 依赖：

```sh
# 原始证据已在本地时：只解析固定 SHA 的 HTML JSON / 人工核对的 PDF 数据
python3 procurement/build-primary-snapshot.py
node procurement/import.mjs import primary-cn-20260927
node procurement/import.mjs verify 10274e8058359c921c6880058ea51f8856e4be409b551abf11d78d1de95a64b4
node --test tests/procurement.test.mjs
```

`incoming/primary-cn-20260927/snapshot.json` 是可读示例；导入后的目录按规范化 JSON 的 SHA256 命名。三个证据文件总计 2,582,820 字节。重复导入同一内容是幂等操作；修改已存 JSON/原始证据后再读取会拒绝。哈希检查证明文件一致性，**不证明网页正确、供应商可信、人工提取无误或工程兼容**。

集成方只能在显式选定快照和精确条目之后调用：

```js
import { quoteImportedSnapshot } from './procurement/import.mjs';
const observation = await quoteImportedSnapshot(snapshotSha256, {
  entryId: 'element14-cn-pico-3643332',
  manufacturer: 'RASPBERRY-PI', mpn: 'RASPBERRY PI PICO', supplierSku: '3643332',
  variant: 'Pico RP2040 without headers; hardware revision unspecified',
  quantity: 1, unit: 'piece', currency: 'CNY',
});
// INDICATIVE_ONLY 或 STALE/UNQUOTABLE；始终 purchaseAuthorized:false。
```

独立只读 API/UI 已实现于 `studio-procurement.mjs` 和 `src/StudioProcurement.tsx`，由主服务与 SourceLibrary 负责接线和部署。API 只有 `GET /api/studio/procurement`，固定读取上面的快照 SHA，每次重新核验三个来源文件，返回四项安全摘要与数量 1 的参考小计；最多两个读取并发，额外请求返回 429。不会返回原始 HTML/本机路径，不提供网页导入、替代选型或下单接口。组件只请求 DGX 同源 API，供应商链接必须由用户明确点击才打开外网。独立模块测试不等于当前服务已部署，须以现场 API/页面验收为准。

MIT 源代码包默认不包含第三方原始网页/PDF。没有整套私有样例时，依赖实际来源的测试明确 SKIP，纯合成协议、越界和 HTTP 边界测试仍运行；存在样例但哈希/文件损坏时必须失败，不会伪装为 SKIP。未安装固定快照的服务返回 503/无价格，不自动联网或换成别的快照。

当前九项 CAD 原始元件仍以原制造商身份存在，任何中国替代件要新建候选版本、匹配尺寸/接口/电压/电流/速度/安装和实际可采购身份，再经设计修订接受。禁止仅凭相似名称或价格低就替换。

## 数据协议和边界

完整字段和约束见 `procurement/SCHEMA.md`，实现以 `snapshot.mjs` 的严格验证器为准。

- 身份必须包含制造商、准确 MPN、供应商 SKU、变体；家族级材料 SKU 缺失就不可报价。
- 阶梯价格必须是正的十进制字符串，明确币种、订购单位、税、运费和来源；BigInt 微单位计算避免浮点误差。不隐式换汇，不把 pack 当 piece，不把数量向 MOQ 自动取整。
- MOQ、订购增量、库存未知时保留 null，而不是 0 或 1。广告价与经过观察的数量阶梯分开；团购/优惠券价格未纳入。
- 捕获时间不等于供应商最近调价时间。`sourceUpdatedAt:null` 保留未知；`web-extract` 无法独立证明价格新鲜度。默认 24 小时只是本地过期策略，并非供应商有效期承诺，最多允许显式设置 720 小时。
- `quoteImportedSnapshot` 先复核来源文件和快照哈希。`validateSnapshot` 只校验结构；低层 `quoteLine` 只做计算，不应替代前者作为应用入口。
- 无 `fetch`/HTTP/购物车/订单/打印接口；导入路径只允许 `incoming` 的直接命名子目录，输出只在 `snapshots/<sha256>`。拒绝路径穿越、符号链接、凭据 URL、查询参数、额外字段、未来或不可能日期、缺失证据和超限文件。原始 HTML 不渲染、不求值。
- 结构规范化 JSON 上限 2 MiB，每份证据 4 MiB，总证据 32 MiB；最多 100 条目 / 30 来源。证据是本地审查用第三方内容，不因此获得再分发许可。
- 硬件实际工作、材料力学裕量、整车总价、交期、实库存与采购许可都不会由价格快照自动获得 PASS。

可选重新获取仅在安装/资料更新阶段，由操作者显式运行 `python3 procurement/capture-official.py --allow-public-network`。该脚本只有三个预置官方 URL，无账号、Cookie 导入或反爬绕过；新的字节产生新的哈希/捕获记录。**旧构建脚本固定本次哈希，不会把新网页默默当作旧证据。** 如供应商要求登录，人工导出可去掉账号/地址等个人信息后制成新的 `operator-export` 包；不要把 Cookie、密码或 API token 放进 JSON。运行时完全离线。

## 提供的 lcsc-part-scraper ZIP 到底是什么

原 ZIP SHA256：`9243fe2a4d11c1be89103cd431d5e0d372e6c5ab7a18eb16c69ba0a4acee9cab`，13,362 字节；已只读检查 `SKILL.md` 与四个 Python 脚本，未执行、安装或启动它们。

它是 Windows Chrome/CDP 浏览器采集 skill，说明了持久化浏览器用户目录和人工扫码登录，再从页面 DOM 读取型号、品牌、封装、编号、现货、价格梯度。它**没有 MCP 服务协议/工具注册，也没有 PCB 编辑器 API**。下载脚本所谓 3D 是 PNG 预览，SVG 是图形预览，不能代替 STEP、可编辑 PCB 或真实可装配几何。

现有解析结果缺少币种、观察时间、来源原文哈希、税/单位、明确 MOQ/增量等采购证据字段；不能原样纳入此协议。若以后适配，应只把人工审查后的固定字段导出到本离线协议，不能把通用 CDP eval/任意路径接口交给模型。当前会话实时工具按 LCSC/嘉立创/EDA/电子元件价格能力检索没有匹配项；这不等于证明整台机器永远没有插件。详细旧审计见 `docs/research/lcsc-package-audit.md`。

## 整车采购完成度：仍是部分，不能伪造总价

当前 `sound-car-v1` 的 #1098 电机、#1420 车轮、#1086 支架、#950 脚轮、#2130 驱动板、Adafruit #1063 麦克风板没有在本次取得对应准确型号的中国 CNY 报价。Pico 的供应商硬件修订尚待核对。打印材料没有准确颜色/线盘 SKU 与价格，消耗量也应取实际选定切片结果，不以原料密度乘包围盒冒充用量。

`docs/car-power-and-wiring.md` 的新增电源、开关、保险丝、线束、紧固件仍是另一个修订候选；本次未为它们宣称中国渠道、实时库存或价格。该候选涉及 5 V 供电等设计变化，不能拼到现有 4.8 V 计算后声称完整闭环。下一步应按真正冻结的 BOM 逐行获取**精确器件/套装单位/数量/税/运费/交期**，对替代件进行接口与电气审查，再算有明确缺项标志的预算。此目录没有完成全车采购报价，也没有采购任何东西。
