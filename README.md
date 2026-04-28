# airband-monitor

民航 VHF 频段异常音频（音乐/广播）自动监听、检测与取证系统。

## 背景

民航 ATC 通话频率上出现音乐或广播声是严重的违规干扰现象。本项目构建一套低成本、可独立部署的监听管道，自动检测此类事件并留存完整证据链（IQ 原始数据、解调音频、频谱图、元数据）。

## 系统架构

```
SDR 硬件（RTL-SDR）
  └─> rtl_fm / rtl_airband（AM 解调，输出 WAV）
        └─> 分类器（YAMNet 或启发式回退）
              └─> 时序评分器（持续时间 + 冷却窗口）
                    └─> 取证记录器（音频 / 频谱 PNG / 元数据 JSON）
                          └─> WeCom 告警 + SQLite 事件库
```

**PoC 阶段**使用 `rtl_fm`（librtlsdr 自带）做单信道解调验证；  
**生产阶段**切换至 `rtl_airband` 实现 118–137 MHz 全频段多信道并行解调。

## 硬件需求

| 组件 | 型号 / 规格 |
|------|------------|
| SDR | RTL-SDR（PoC）；Airspy Mini 或 SDRplay RSP1A（生产） |
| 前端滤波 | 118–137 MHz 航空段带通滤波器 + 低噪放 |
| 天线 | Diamond D-130 宽带 discone 或 118–137 MHz 专调垂直天线 |
| 主机 | macOS / Linux x86_64（N100 小主机）；后期支持 ARM64（香橙派） |

## 环境搭建

### macOS（开发 / 验证）

```bash
# 1. 系统依赖
brew install librtlsdr sox python@3.12

# 2. 验证 RTL-SDR 识别
rtl_test -t

# 3. 克隆项目
git clone https://github.com/VaneEcho/airband-monitor
cd airband-monitor

# 4. Python 环境
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pyyaml numpy scipy          # 基础依赖（启发式分类器）
pip install tensorflow tensorflow-hub   # 可选：YAMNet 后端
```

### Linux（部署目标）

```bash
apt install rtl-sdr sox python3.12 python3.12-venv
# 克隆、venv、pip 步骤同 macOS
```

## 快速开始

```bash
source .venv/bin/activate

# 1. 冒烟测试（无需 SDR 硬件）
python -m airband_monitor.main --simulate

# 2. 录制测试音频（需要 RTL-SDR 已连接）
./scripts/capture_macos.sh 121.5 60 test_audio/live         # 录 60s 航空 AM
./scripts/capture_macos.sh 89.0  30 test_audio/music_inject  # 录 30s FM 广播（模拟干扰注入）

# 3. Watch 模式持续分类（启发式，无需 TensorFlow）
python -m airband_monitor.main \
    --config configs/poc_macos.yaml \
    --input-wav-dir test_audio/live \
    --wav-freq 121.5 \
    --watch --poll-interval 2 \
    --classifier-backend heuristic

# 4. 切换为 YAMNet 后端（需已安装 tensorflow tensorflow-hub）
python -m airband_monitor.main \
    --config configs/poc_macos.yaml \
    --input-wav-dir test_audio/live \
    --wav-freq 121.5 \
    --watch \
    --classifier-backend yamnet

# 5. 从 JSONL 文件回放推理帧
python -m airband_monitor.main --input-jsonl examples/frames.jsonl

# 6. 查看已记录事件
python -m airband_monitor.main --list-events 10

# 7. 阈值评估
python -m airband_monitor.main \
    --evaluate-jsonl examples/eval_samples.jsonl \
    --eval-thresholds 0.5,0.6,0.7,0.8,0.9
```

事件数据库：`data/events.db`；取证文件：`data/artifacts/`。

## 配置文件

| 文件 | 用途 |
|------|------|
| `configs/default.yaml` | 生产默认配置 |
| `configs/poc_macos.yaml` | macOS PoC 验证（低阈值、dry_run=true）|

`WECOM_WEBHOOK` 环境变量会自动覆盖配置文件中的 webhook 地址。

## 分类器后端

| `--classifier-backend` | 依赖 | 适用场景 |
|------------------------|------|---------|
| `auto`（默认）| 优先 YAMNet，TF 不可用时回退启发式 | 生产推荐 |
| `yamnet` | tensorflow, tensorflow-hub, scipy | 高准确率 |
| `heuristic` | 无外部依赖 | 快速验证、低算力节点 |

## JSONL 推送接口

外部推理进程可将结果以 JSONL 格式写入 STDIN 或文件，与本系统对接：

```json
{"ts_utc":"2026-04-27T14:30:00+00:00","freq_mhz":121.5,"music_prob":0.83,"labels":{"music":0.83},"audio_path":"/path/chunk.wav","iq_path":""}
```

```bash
some_classifier | python -m airband_monitor.main --stdin-jsonl
```

## rtl_airband 录音目录模式

`--input-rtl-dir` 递归扫描 WAV 录音，从文件名推断频率：

- 小数 MHz 格式：`121.500`
- 整数 Hz 格式：`121500000`

无法推断时使用 `--rtl-default-freq` 指定回退频率。

Watch 模式细节：
- `--watch` 与 `--input-wav-dir` 或 `--input-rtl-dir` 配合使用
- 每次轮询只处理新文件，重启后不重复处理（状态持久化至 `--watch-state-file`）
- `--max-loops N` 用于测试场景的有界运行

## 证据策略

- **IQ 环形缓冲**：120 秒滚动窗口
- **事件截取**：触发前 30 秒 + 触发后 90 秒
- **落盘内容**：`audio.wav`、`capture.iq`、`spectrum.png`、`meta.json`
- **磁盘清理**：超过 85% 开始删最旧事件，降至 75% 停止

## 检测参数（生产默认值）

| 参数 | 值 | 说明 |
|------|----|------|
| `music_prob_threshold` | 0.70 | 触发阈值 |
| `min_duration_sec` | 5 | 持续达阈值才确认事件 |
| `duplicate_cooldown_sec` | 120 | 同频点冷却窗口 |

设计原则：**宁可多报，不可漏报**——存储廉价，漏掉证据代价不可挽回。

## 路线图

| 版本 | 目标 |
|------|------|
| v0.1 | RTL-SDR + rtl_fm/rtl_airband + YAMNet + WeCom + 取证存储 ✓ |
| v0.2 | 载波频偏检测 + 占空比分析（信号级二次判据） |
| v0.3 | FM 广播相关性匹配（直接定位干扰源电台） |
| v1.0 | 多节点部署 + TDoA 粗定位 + 事件联邦 |

详细实施计划见 [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)。

## 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/capture_macos.sh` | rtl_fm 录音封装（频点 / 时长 / 输出目录） |
| `scripts/verify_pipeline.sh` | 分阶段验证（硬件 → 依赖 → 分类器 → 管道） |
| `scripts/run_demo.sh` | 快速演示 |

## 提交前检查

```bash
pytest -q
python -m airband_monitor.main --simulate --classifier-backend heuristic
python -m airband_monitor.main --evaluate-jsonl examples/eval_samples.jsonl \
    --eval-thresholds 0.5,0.6,0.7,0.8,0.9
```
