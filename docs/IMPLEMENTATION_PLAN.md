# airband-monitor 实施计划

## 1. 目标

构建一套实用、可维护的民航 VHF 干扰监听系统，专注于 ATC 通话频率上出现音乐/广播类异常音频的自动检测与取证。

## 2. v0.1 固化决策

| 项目 | 决策 |
|------|------|
| SDR 硬件 | RTL-SDR（PoC）；Airspy Mini / SDRplay RSP1A（生产） |
| 监听频点 | 119.6 / 119.7 / 119.9 / 120.35 / 120.4 / 121.5 MHz |
| 主要异常类型 | 音乐（music） |
| 次要尽力检测 | 广播/电台类（broadcast/radio-like） |
| 告警通道 | WeCom webhook |
| 检测偏向 | 高召回率（宁可多报，不可漏报） |
| IQ 环形缓冲 | 120 秒 |
| 事件截取窗口 | 触发前 30 秒 + 触发后 90 秒 |
| 元数据存储 | SQLite |
| 取证文件存储 | 本地文件系统 |
| 磁盘清理策略 | 水位线清理（>85% 开始，<75% 停止） |
| **开发环境** | **macOS（当前）；Linux x86_64 为部署目标** |
| 部署目标 | N100 Linux 小主机（首选）；香橙派 ARM64（后期） |

> 注：早期方案中曾考虑 WSL，现已改为 macOS 原生开发环境直接验证，避免 USB 透传稳定性问题。

## 3. v0.1 非目标

- 全频段扫描编排
- TDoA 多节点定位
- 高精度干扰源溯源
- 富前端 Dashboard

## 4. 实际代码结构

```
airband-monitor/
├── src/airband_monitor/
│   ├── main.py               # CLI 入口，支持多种运行模式
│   ├── config.py             # YAML 配置加载（支持 PyYAML 或内置极简解析）
│   ├── ingest.py             # InferenceFrame 数据结构 + JSONL 源
│   ├── classifier.py         # 启发式分类器（纯标准库，无 ML 依赖）
│   ├── yamnet.py             # YAMNet 后端（可选，需 tensorflow + tensorflow-hub）
│   ├── classifier_backend.py # 后端选择逻辑（auto / heuristic / yamnet）
│   ├── wav_source.py         # WAV 目录源
│   ├── rtl_airband_source.py # rtl_airband 录音目录源
│   ├── scoring.py            # 时序评分器（持续时间 + 冷却）
│   ├── recorder.py           # 取证文件记录器
│   ├── spectrum.py           # 频谱 PNG 生成（纯标准库）
│   ├── storage.py            # SQLite 事件库
│   ├── alert.py              # WeCom webhook 告警
│   ├── retention.py          # 磁盘水位线清理
│   ├── watch_state.py        # Watch 模式已处理文件持久化
│   └── evaluation.py         # 阈值网格评估工具
├── configs/
│   ├── default.yaml          # 生产默认配置
│   └── poc_macos.yaml        # macOS PoC 验证配置（低阈值、dry_run）
├── scripts/
│   ├── capture_macos.sh      # rtl_fm 录音封装脚本
│   ├── verify_pipeline.sh    # 分阶段验证脚本
│   └── run_demo.sh           # 快速演示
├── tests/                    # 单元测试（pytest）
├── examples/
│   ├── frames.jsonl          # 示例推理帧
│   └── eval_samples.jsonl    # 标注评估样本
└── docs/
    └── IMPLEMENTATION_PLAN.md
```

## 5. 事件状态机

```
idle ──(载波/音频出现)──> candidate ──(music_prob >= 0.7 持续 5s)──> confirmed
                                                                          │
                    ┌─────────────────────────────────────────────────────┘
                    ▼
               recording（落盘 IQ / 音频 / 频谱 / 元数据）
                    │
                    ▼
               alerted（发送 WeCom）
                    │
                    ▼
               cooldown（同频点 120s 内不重复告警）
                    │
                    ▼
                  idle
```

## 6. 数据模型

### SQLite `events` 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | UUID |
| `site_id` | TEXT | 站点标识 |
| `freq_mhz` | REAL | 频率 |
| `start_time_utc` | TEXT | 事件起始时间（ISO 8601） |
| `end_time_utc` | TEXT | 事件结束时间 |
| `duration_sec` | REAL | 持续时长 |
| `music_score_max` | REAL | 最高音乐置信度 |
| `labels_json` | TEXT | 分类器完整标签 |
| `iq_path` | TEXT | IQ 文件路径 |
| `audio_path` | TEXT | 音频文件路径 |
| `spectrum_png_path` | TEXT | 频谱图路径 |
| `meta_json_path` | TEXT | 元数据 JSON 路径 |
| `alert_status` | TEXT | 告警状态 |

## 7. 里程碑进度

### Milestone A：采集接入 ✓

- [x] WAV 目录源（`WavDirectorySource`）
- [x] rtl_airband 录音目录源（`RtlAirbandRecordingSource`，文件名推断频率）
- [x] JSONL / STDIN 外部推理帧接口
- [x] Watch 模式增量采集（持久化已处理文件，重启不重复）

### Milestone B：分类与评分 ✓

- [x] 启发式分类器（RMS / ZCR / 峰值比，纯标准库）
- [x] YAMNet 后端（tensorflow-hub，已修复 `scipy.signal.resample` 替代 TF 不存在的 API）
- [x] 时序评分器（持续时间门控 + 冷却窗口）
- [x] 分类器后端自动选择（`auto` / `heuristic` / `yamnet`）

### Milestone C：取证记录 ✓

- [x] 取证文件记录器（音频 / IQ / 频谱 PNG / 元数据 JSON）
- [x] 频谱 PNG 生成（无 matplotlib 依赖，纯标准库实现）
- [x] 事件目录按日期组织

### Milestone D：告警与持久化 ✓

- [x] WeCom webhook 告警（支持 dry-run）
- [x] SQLite 事件库（插入 / 查询 / 计数）
- [x] 磁盘水位线清理（`WatermarkRetention`）

### Milestone E：macOS PoC 验证环境 ✓

- [x] 确认 Python 3.12 + macOS 完全兼容（无平台特定 API）
- [x] `configs/poc_macos.yaml`：低阈值配置，便于快速触发测试
- [x] `scripts/capture_macos.sh`：rtl_fm 录音一键脚本
- [x] `scripts/verify_pipeline.sh`：分阶段验证（硬件 → 依赖 → 分类器 → 管道）
- [x] 冒烟测试通过（`--simulate` 触发 dry-run 告警）

## 8. 风险与对策

| 风险 | 对策 |
|------|------|
| ~~WSL USB 稳定性~~ | 已改为 macOS 原生开发，规避此问题 |
| 楼顶强 FM 广播干扰前端 | 加装 118–137 MHz 带通滤波器 + LNA |
| 误报（嘈杂信道）| 保留全量录音日志，用可回放 clip 离线调阈值 |
| IQ 存储增长 | 磁盘水位线清理 + 按需回传策略 |
| YAMNet 推理延迟 | CPU 单帧 < 1s；YAMNet 仅做二级确认，不阻塞录证 |

## 9. 生产配置参考

```yaml
site:
  id: site-gz-001

detection:
  music_prob_threshold: 0.70
  min_duration_sec: 5
  duplicate_cooldown_sec: 120

buffers:
  iq_ring_sec: 120
  pre_trigger_sec: 30
  post_trigger_sec: 90

retention:
  enabled: true
  start_cleanup_percent: 85
  stop_cleanup_percent: 75

alert:
  wecom_webhook: ""   # 或设置 WECOM_WEBHOOK 环境变量
  dry_run: false
```

## 10. 剩余待完成工作

### 进入稳定 v0.1 需完成

- [ ] 在真实 RTL-SDR + 真实航空音频上验证 YAMNet 准确率
- [ ] 实现真正的 IQ 环形缓冲采集（现有结构为占位符）
- [ ] 基于真实捕获样本做误报率分析，调整生产阈值

### v0.2 计划

- [ ] 载波频偏检测（合法航空台偏移 < 500 Hz，干扰常见几 kHz）
- [ ] 载波占空比分析（持续连续载波 = 可疑）
- [ ] 切换至 `rtl_airband` 多信道并行解调

### v0.3 计划

- [ ] 并行录制 FM 广播段做音频相关匹配，定位具体干扰电台

### v1.0 计划

- [ ] 多节点时间同步（GPSDO 或 NTP）
- [ ] TDoA 粗定位
- [ ] 事件联邦与跨站一致性确认
- [ ] systemd / Docker 服务打包

## 11. v0.1 合入检查清单

- [ ] `pytest -q` 全部通过
- [ ] `python -m airband_monitor.main --simulate` 端到端成功
- [ ] 阈值评估报告从标注样本生成（`--evaluate-jsonl`）
- [ ] 真实 RTL-SDR 录音通过 Watch 模式分类，结果符合预期
- [ ] README 快速开始命令在干净环境验证通过
