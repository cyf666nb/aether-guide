# Aether Guide — 项目体检 + 0–5 周 AI Coding 规划

> 生成日期：2026-05-16
> 范围：`C:\Users\Legion\Documents\New project`
> 输入：README.md、`docs/MVP_GAP.md`、`docs/review-round-2.md`、API 主入口、数字人/视觉定位/语音/RAG 服务、前后端目录结构与测试目录

---

## 一、项目体检（Aether Guide）

### 体量与定位
- **monorepo**：`apps/api` (FastAPI, 75 个 .py)、`apps/web-tourist` (Next 15, 20 个 ts/tsx)、`apps/web-admin` (Next 15, 12 个 ts/tsx)、`packages/design-system`
- **场景**：景区智慧导览（三坊七巷为种子数据），主打 AI 数字人 + RAG + 多模态定位
- **阶段**：MVP，已完成两轮"全面审查"，14 项阻塞问题修了 13.5 项

### ✅ 已达到生产级别的能力

| 维度 | 现状 |
|---|---|
| 鉴权 | JWT + bcrypt + WS `?token=` 校验、admin role gate（`auth/dependencies.py`） |
| 限流 | Redis 滑窗 + 进程内降级，带 `X-RateLimit-*` 头 |
| 审计 | `AuditMiddleware` 把写操作落 `AuditLog`，admin 可查 |
| 存储 | inmemory ↔ SQL（SQLAlchemy async + Alembic），连不上自动降级 |
| RAG | **真实**：BGE-m3 嵌入 + Qdrant，未配 Qdrant 时降级为 lexical+sparse 评分 |
| 健康检查 | `/healthz` + `/readyz`（DB SELECT 1 + Redis PING） |
| AI 客户端 | LiteLLM/Anthropic/OpenAI 三路 + cost_usd 抽取 + 异常收窄 |
| CI 门禁 | ruff strict、mypy strict（66 文件 0 issue）、pytest 21 通过、ESLint 双闸口、typecheck、build |

### ⚠️ 标"完成"但实质有差距的地方

1. **数字人渲染** — `services/digital_human/client.py` 只返回 manifest，**真实渲染 100% 在前端 Live2D**。README 主打"AI 数字人"，但没有 LiveKit / MuseTalk / SadTalker 视频管线，TTS → 口型同步胶水也没接上。
2. **语音管线** — `services/voice/pipeline.py` 全字段 `stubbed`；只有 TTS 出，**没有 VAD/ASR 入**。
3. **离线模式** — 后端 `offline.py` 路由有，前端 0：没有 manifest、没有 SW、没有 IndexedDB。
4. **VPS 融合** — `services/location/fusion.py` 没真正用 GPS hint，置信度直接 `sum/len`；与 `MVP_GAP.md` 自检一致。
5. **E2E 测试** — `tests/e2e/` 只有一个 `.gitkeep`，**等于没有**。
6. **观测栈** — `infra/docker-compose.yml` 起 Prometheus/Grafana/Loki/Tempo，但 `prometheus.yml` / `loki-config.yaml` / `tempo.yaml` / dashboard provisioning 缺失（review-round-2 §"🟡 轮候选清单"已点名）。
7. **Prompt 实验** — schema 在、后端在、**admin UI 不在**。
8. **`next/image` 迁移** — 3 处 `<img>` 警告还在；两份 public PNG 副本未合到 design-system。

### 🟥 合规与商用风险

- **Live2D 模型**：默认带的 Haru Greeter / Mao PRO 都是 Live2D Inc. **样例模型**，商用需另签授权。生产前必须替换或获取 SDK 商用证书。
- **PII**：人脸照片直接收 base64，**未做模糊**；视觉定位场景下违反《个人信息保护法》"最小必要"。
- **内容安全**：用户输入、AI 输出**都没有过敏感词/合规检查**，景区场景对舆情敏感度高。
- **未成年人模式**：完全没做，监护人联系、简化内容档都缺。

### 🟨 架构上需要尽快做的小修

- `web-admin` 用"兼职游客 token"调 `/api/v1/landmarks`（review-round-2 §3）— 跨角色调用，要补 `/admin/v1/landmarks`。
- 审计 `before` 永远是 `None`，回滚和合规审计意义打折。
- Rate-limit 在生产真实 Redis 下还是 pipeline 命令，没切回 Lua `evalsha`。
- Session token 在 `sessionStorage`，刷新保留但跨标签不共享。

---

## 二、0–5 周 AI Coding 规划

每个 sprint 列三件事：**目标 / 关键交付 / AI 代理执行策略**（哪种适合 `subagent-driven-development` 多代理并行，哪种需要 `writing-plans` + `executing-plans` 两段式，哪种用 `test-driven-development`）。

---

### 🟦 Week 0（本周，稳住演示）— 收尾遗留 + 补观测

**目标**：把"已完成 13.5/14"的 0.5 项收掉，让仓库进入"任何人 clone 都能跑通+演示不翻车"的状态。

| 任务 | 工具/技能 |
|---|---|
| `<img>` → `next/image` 全量迁移；场景 PNG 合并到 `packages/design-system/src/scenes/` 单源 | 直接执行（小批量改动） |
| `infra/` 补 prometheus.yml / loki-config.yaml / tempo.yaml + grafana provisioning + api+worker 容器 | `writing-plans` 先把目标拓扑画清，再 `executing-plans` |
| `/admin/v1/landmarks` 端点 + 从 web-admin 移除"兼职游客 token" | TDD：先写测试，再 router，再删冗余 |
| Playwright E2E 骨架：3 条 happy path（匿名登录 → 看景点 → WS 聊天 → 拍照识别） | `dispatching-parallel-agents`，三条路并行写 |
| 修 VPS `fusion.py` 让 GPS hint 真正参与加权 + 单测 | TDD |
| `AuditMiddleware` 补 `before` 字段 | 小改动直接做 |

**输出**：一个绿色 CI + 一份"演示前 checklist 自动化脚本" `scripts/preflight.ps1`。

---

### 🟩 Week 1 — 语音入：VAD + ASR 最小可用

**目标**：用户可以"说一句话"提问，闭环到现有 WS 聊天流。

**关键交付**：
- 浏览器侧：push-to-talk 按钮 + Web Speech API（Chrome/Edge 自带 ASR）作为 P0 路径
- 服务端：`services/voice/pipeline.py` 接 webrtcvad（VAD）+ SenseVoice-small 或 faster-whisper（ASR，CPU 也能跑）
- WS 协议：`audio_chunk` 消息类型，ASR 结果作为 `user_message` 转发到 LLM
- `VoicePipelineStatus` 上报真实状态（`vad="webrtcvad"`、`asr="sensevoice-small"`）
- 失败降级：ASR 5 秒未出结果 → 提示用户切回文字

**AI 代理策略**：
- 用 `brainstorming` 先把 "Web Speech API 优先 + 服务端兜底" 的边界谈清
- `writing-plans` 写两段：前端 push-to-talk UI 与 WS 协议；后端 pipeline 选型 + 实现
- `executing-plans` 执行；选型那段强烈建议人工介入决策（SenseVoice vs faster-whisper 与部署机器算力有关）

---

### 🟨 Week 2 — 数字人变"活"：TTS 口型 + 情绪驱动

**目标**：从"会跳舞的纸片人"升级到"说话嘴会动、情绪和回答匹配"，**不上视频流，先把 Live2D 价值榨干**。

**关键交付**：
- 前端 `Live2DMao.tsx` 接通 `pixi-live2d-display-lipsyncpatch` 的 `model.speak(audioUrl)`，TTS 输出的 mp3/wav 自动驱动 `ParamA`
- LLM 回包附带情绪标签（`sentiment: happy|neutral|alert|sad`），前端按情绪切 `exp_01..exp_08` 表情与对应 motion group
- Admin UI 加"人设管理"页（PersonaDTO 后端已有），上传新模型 + 预览
- **可选 feature flag**：服务端 MuseTalk / SadTalker 走 LiveKit 推流路径（带开关，默认关）
- 替换或确认 Haru Greeter / Mao PRO 商用授权

**AI 代理策略**：
- 前端 Live2D 逻辑写起来琐碎但独立，适合 `subagent-driven-development` 拆 3 子任务并行（lipsync 接线 / 情绪切表情 / Persona 上传 UI）
- MuseTalk 那条线先用 `Plan` 调研可行性，不在 W2 落地，留口子给 W3+

---

### 🟧 Week 3 — 离线模式 + PWA

**目标**：景区 WiFi 抽风时游客端不白屏。

**关键交付**：
- `apps/web-tourist/public/manifest.json` + `next-pwa`（Next 15 适配版）
- Service Worker 缓存策略：`/landmarks`（stale-while-revalidate）、`/scenic/{id}/offline-pack`（cache-first）、静态资源（cache-first）
- IndexedDB 存最近 50 条聊天记录，离线时显式标"离线消息（未送达）"
- "离线模式" 顶部 banner，恢复连接后自动同步
- 离线包冷启用 `/api/v1/scenic/{id}/offline-pack` 后端路由（已有）打全

**AI 代理策略**：
- 这一块踩坑多（next-pwa 的 Next 15 兼容、SW 调试），先 `systematic-debugging` 心态，逐个 case 用 Playwright 验证
- 离线场景测试用例必须先写：`writing-plans` → `test-driven-development`

---

### 🟥 Week 4 — 合规与 i18n 硬化（上生产前必做）

**目标**：把合规风险从"有"压到"可接受"。

**关键交付**：
- **PII 脱敏**：上传照片在落 MinIO 前用 mediapipe Face Mesh 或 opencv haar 模糊人脸；保留原图 24h 后删除
- **内容安全**：用户输入 + LLM 输出双向过敏感词（开源 sensitive-word-filter 起步），再叠豆包/通义内容安全 API 兜底
- **i18n**：`next-intl` 接入两端，简体中文 + 英文起步；RAG 知识库按 `lang` tag 分桶检索
- **未成年人模式**：登录时勾选年龄段，未成年人启用 `persona_minor` 人设 + 监护人联系字段 + 安全告警双发
- **审计补 PII 字段**：监护人手机号写入前 SHA-256

**AI 代理策略**：
- 合规决策不要让 Agent 单飞，**先 `brainstorming` 把法律边界谈清**（人工介入），再让 Agent 实现
- `requesting-code-review` 在每个 PR 合并前跑一次

---

### 🟪 Week 5 — 发布就绪 + Prompt 实验 UI

**目标**：产生一个"按 checklist 就能 K3s 部署"的版本。

**关键交付**：
- web-admin 的 Prompt 实验 UI（schema 已就位，只缺前端）：创建实验、查看 A/B 分流、看 metric 漏斗
- k6 压测升级到 `tests/perf/k6-smoke.js` 之上：POST /sessions 限流场景、WS 长连接 1k 并发、拍照识景
- K3s 清单评审 + secrets via External Secrets Operator
- Live2D 授权最终确认（要么换模型、要么签 SDK License）
- 生产 Redis 切回 Lua `evalsha` 原子限流
- 跑完 `docs/MVP_GAP.md` §六 演示前 checklist + `docs/review-round-2.md` §"发布清单"全过

**AI 代理策略**：
- Prompt 实验 UI 是 CRUD + 图表，标准 `subagent-driven-development` 三件套（列表页 / 详情页 / 创建表单）并行
- k6 用例可让 Agent 模板化生成，**人工 review 阈值**
- 部署清单用 `verification-before-completion` 严格走一遍

---

## 三、跨周期持续做的事

1. **每周一次** `requesting-code-review`（cloud ultrareview）扫一遍上周分支
2. **每周末** `uv sync --upgrade --dry-run` 看依赖飘移
3. **bug fix** 全部走 `test-driven-development`（已有 21 个测试托底，加测成本低）
4. **新 feature** 全部走 `brainstorming` → `writing-plans` → `executing-plans`，不让 Agent 直接动手
5. **不写"未来扩展点"代码** — 仓库目前架构很干净（Repository Protocol、可插拔 AI provider），保持

---

## 四、优先级排序（如果只能做 3 件事）

1. **W1 语音入**：README 承诺的"语音对话"目前是单向的，这是用户感知最强的差距
2. **W4 合规**：景区项目过合规是上线先决条件，比新功能优先
3. **W0 观测栈 + E2E**：现在 PR 合进 main 没有 E2E 兜底，很危险

---

## 五、相关文档索引

- 架构总览：[`../README.md`](../README.md)
- MVP 差距：[`MVP_GAP.md`](MVP_GAP.md)
- 第二轮审查：[`review-round-2.md`](review-round-2.md)
- API 规范：[`api/openapi.yaml`](api/openapi.yaml)
- ADR：[`decisions/ADR-001-stack.md`](decisions/ADR-001-stack.md)
- Runbook：[`runbook/local-dev.md`](runbook/local-dev.md)
