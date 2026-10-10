# M4KE：只带 DGX 的本地运行方案

## 运行边界

DGX 必须本机保存并运行：网页静态文件、Node 后端、Ollama/vLLM、模型权重和 tokenizer、Python/CadQuery、Skills、零件元数据及获准缓存的 CAD、项目和导出文件。浏览器可在 DGX 的显示器上打开 `http://127.0.0.1:4173`。不需要开发者 Windows 电脑、SSH 反向隧道、花生壳、GitHub 在线连接或在线模型桥接。

模型下载、依赖安装、1688 元数据和数据手册获取是在有网络时完成的准备工作。公开源码不包含模型权重、用户数据、凭据或未获授权的第三方模型；克隆仓库不等于已经准备好离线环境。队友负责 1688 导入；本功能不修改其爬虫或模型尺寸。

## 联网准备与只读自检

使用项目原有安装流程，在 **DGX 的 ARM64 系统上** 安装依赖，不要拷贝 Windows 的 Python 虚拟环境。先完成 `npm ci`、`npm run build`、CadQuery 和模型缓存准备。固定经过验证的推理引擎版本/容器 digest；不要在临近演示时无条件更新 `latest`。参考 [NVIDIA DGX Spark vLLM 方案](https://build.nvidia.com/spark/vllm)。

```bash
# 在 DGX 项目根目录，使用实际安装 CadQuery 的 Python 环境
python scripts/dgx-preflight.py --output test-results/dgx-preflight.json
```

此命令只读取硬件、剩余空间、构建文件、Skills 和本机已启动模型服务。不会安装、下载、加载模型或重启服务；`offlineAcceptance: NOT_RUN` 不能写成通过。

配置 `.env` 中精确的已安装模型名及本机服务地址，例如端口 `11434`（Ollama）或 `8000`（vLLM）。模型名从服务列表读取，不猜测别名。然后：

```bash
node scripts/start-offline.mjs
```

启动器开启 `M4KE_OFFLINE_ONLY=1`、关闭应用联网检索、关闭 Hugging Face 自动联网，并拒绝在线桥接 provider。前端资源与物理引擎随构建打包，无运行时 CDN。**这不是操作系统防火墙**；要证明完全离线，还必须实际断网测试。配置不会被自动改写。

## 本地模型选择：以任务成功率而非参数量决定

先测现有可用模型，再测试 122B 量化候选，不覆盖现有服务。可评估 [Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) 和 [Intel INT4 AutoRound 量化](https://huggingface.co/Intel/Qwen3.5-122B-A10B-int4-AutoRound)。量化发布者给出 vLLM 示例，但并未保证此应用或此硬件上的成功率。

122B 权重的理想下限：FP16 约 227.2 GiB，INT4 约 56.8 GiB；实际还需量化比例尺、未量化张量、KV cache、推理引擎和 CAD/UI 内存。不能因为“10B 激活”就只为 10B 权重预留内存。先读取实机 MemAvailable；预留至少约 20 GiB 作为初始测试预算（需实测调整），先单并发、小上下文，再逐步增加。内存占满不是优化目标。

[MiniMax M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) 只能作为后续候选；具体权重格式、运行时支持、完整权重大小和许可证需单独核对，不能因 MoE 激活参数少就承诺单机装得下。本次没有宣称任何新模型已经在目标 DGX 通过测试。

## 同一组任务进行评测

关闭其他模型任务，确认队友没有占 GPU，保持本机 Studio 空闲。评测只请求模型的结构化回复，不创建或覆盖生产项目，不执行模型代码，也不修改默认 provider。

```bash
M4KE_BENCH_COORDINATED=1 node scripts/benchmark-local-contracts.mjs \
  --provider=ollama --endpoint=http://127.0.0.1:11434 \
  --studio=http://127.0.0.1:4173 --models=EXACT_INSTALLED_MODEL_ID \
  --repeat=3 --attempts=2 --thinking=false \
  --output=test-results/local-contracts
```

vLLM 使用 `--provider=vllm --endpoint=http://127.0.0.1:8000`。执行前替换 `EXACT_INSTALLED_MODEL_ID`。案例包括需求保持、四项电气错误同时修复、选中外壳修改不破坏底盘接口。每轮把**所有失败条件一次性反馈给模型**；修复答案由模型生成，校验器不会偷偷修补答案。记录首次/修复后结果、延迟、可用吞吐指标和回复哈希；语义检查过关不等于 CAD 成功。继续使用原有 `benchmark-local-models.mjs`、真实项目生成→修改→CAD/电气检查→导出来验证端到端能力。

推荐晋级条件：同一案例重复至少 3 次；保留每次失败；禁止把缺失模型/服务错误计为通过；只有真实原生 CAD 和应用流程无回归，且你确认后，才切换生产配置。还需人工审阅模型回复，不能将这三个小样本称作通用准确率。

## 行驶仿真的准确范围

工作台 3D 模型区有“打开行驶仿真（估算）”。复用当前版本模型，原生 STL 必须通过现有 SHA-256 缓存校验，失败不换成假模型。Three.js 渲染、Rapier 本地 WASM 负责包围盒与路面/障碍物碰撞；思路参考 [Three.js Rapier 车辆示例](https://threejs.org/examples/physics_rapier_vehicle_controller.html) 和 [Rapier 官方入门](https://rapier.rs/docs/user_guides/javascript/getting_started_js/)，并不是该示例的完整车辆控制器。

范围是平路 X 方向直行。响度输入为 **0–100 相对值，不是 dB SPL**。质量、轮径、空载转速、扭矩、PWM 和阻力可调整；修改后复位生效。按电压/PWM 缩放空载轮速，近似线性扭矩–转速关系，再约束抓地与滚动阻力。制动减速度是假设；没有真实固件、声音/电池/电机噪声、轮胎变形、悬挂、热学或实物碰撞验证。参数不会修改设计或打印件，也不生成 PASS 证据。方向沿模型 X 轴；不自动推断任意玩具的机构。

### 轮组滚动与物理边界

轮圈、轮胎按同一轮轴分组，角度由实际位移 `θ = s / r` 得到；转速由实际速度得到，不是固定转圈动画。已知轮组使用明确的部件 ID 和滚动半径；其他设计只对名称与几何相符的 Y 轴圆轮进行推断，并显示“需核对”。没有识别到轮组时明确保留包围盒预演，不能据此宣称传动有效。

前后轮半径不同会产生不同转速；安静制动后停转、撞停后不继续累积圈数、复位清零。接地判断约束驱动冲量，离地不施加牵引力。仿真轮缘标记仅用于观察旋转，不写入 CAD/STL/3MF。电机驱动力仍使用简化扭矩曲线；不是完整轮胎接触、轮轴刚体、打滑、悬挂或真实制动器模型。正式实物判断还需要实测质量、堵转扭矩、摩擦和电流数据。

## 出发前验收

- 保存权重和 tokenizer 的本地路径/哈希、容器镜像 digest、安装依赖及模型库许可证。
- 断开网线/Wi-Fi；关闭开发电脑；在 DGX 重新启动模型和应用。
- 从空白项目提交需求，必要问答、生成、选件问答、候选修改、确认、验证、导出全部实际执行。
- 确认没有 Windows 路径、外部隧道、在线 API 或远程素材依赖；冷启动后仍可加载页面、CAD 和仿真。
- 1688 价格只标注缓存时间，不将离线旧价写成实时价；未缓存组件明确缺失。
- 本地导出到 USB；打印机不随行时不能宣称现场打印可用。
- 备份应用代码和配置；数据/模型目录单独保护。代码通过 PR，部署须确认；回滚应用代码不回滚用户数据。

## 本次未完成的硬件验收

旧 SSH 信任记录属于专用远程服务，不能直接验证现在的直连服务；直连身份尚未确认；未发送登录凭据、未部署、未下载新权重。须在机器本机确认公钥指纹或提供可信的新直连信息，再执行硬件库存和真实模型评测。此状态不影响本地代码/仿真回归，但**不能据此宣称只带 DGX 的全流程已经通过**。
