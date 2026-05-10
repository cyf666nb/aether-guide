# MVP_GAP — Stub 与缺口清单

> 本文档列出 Aether Guide MVP 阶段所有 **stub / 占位 / 未完成** 的实现，避免演示翻车，并指明每项的优先级与落地路径。
>
> **状态图例**：🔴 高风险（演示不能用） · 🟡 中风险（功能受限） · 🟢 低风险（已有降级） · ✅ 已实现

最后更新：2026-05-11

---

## 一、关键 Stub 清单（按"演示翻车风险"排序）

### 🔴 数字人渲染（`services/digital_human/client.py`）

| 项 | 现状 |
|---|---|
| 文件 | `apps/api/aether_api/services/digital_human/client.py` |
| 实现行数 | 14 行 |
| 当前行为 | 硬编码返回 `RenderStatus(engine="MuseTalk stub", livekit_ready=False, fallback="text-card")` |
| 演示影响 | **README 主打"AI 数字人"，但根本没接渲染管线**。任何"看一下数字人"的需求都会暴露 |
| 最低落地路径 | 1) 接入 LiveKit Server SDK，发布一个房间令牌；2) 前端用 LiveKit Web SDK 加入房间；3) 服务端用 MiniMax/字节豆包 TTS 输出音频 → 推到房间；4) 用一张静态立绘 + 简单口型同步（Wav2Lip Light / SadTalker）作为视频流 |
| 需要环境变量 | `AETHER_LIVEKIT_URL`、`AETHER_LIVEKIT_API_KEY`、`AETHER_LIVEKIT_API_SECRET` |
| Demo 兜底 | 当前 `fallback="text-card"` 已生效——前端应**显式渲染"文字卡片模式"**，避免出现空白容器 |

### 🟡 视觉定位（`services/location/vps.py`）

| 项 | 现状 |
|---|---|
| 当前实现 | 已接入 VLM（doubao-seed / OpenAI 兼容多模态），按"图片+地标列表"提示词识别 |
| 缺口 | 1) **无 SLAM/重定位**——亚米级室内定位无法实现；2) GPS hint 未真正参与融合（`fusion.py` 需核查）；3) 无图片大小/格式校验，VLM 失败时回退到"取第一个景点"，**置信度不可靠** |
| 演示影响 | 户外景点（三坊七巷此类街区）够用；室内/复杂场景会失败 |
| 最低落地路径 | 短期：把 fallback 从"取第一个景点"改成"明确返回 uncertain + 引导拍牌匾"；中期：训练景区专属图像检索（CLIP + Faiss） |

### 🟡 语音管线（`services/voice/pipeline.py`）

| 项 | 现状 |
|---|---|
| 当前实现 | `VoicePipeline.status()` 返回全 `stubbed` |
| 已存在的真实实现 | TTS 已可用（`services/tts/client.py`，MiMo v2.5 已对接） |
| 缺口 | **VAD（端点检测）+ ASR（语音识别）完全没做**——用户无法用语音提问 |
| 演示影响 | 当前是纯文字输入。如果客户问"能不能直接说话问"，会回答"暂未上线" |
| 最低落地路径 | 浏览器侧用 Web Speech API（Chrome/Edge 自带 ASR）做最低版本；服务端用 SenseVoice / Whisper 做正式版 |

### 🟢 离线模式（`routers/offline.py`）

| 项 | 现状 |
|---|---|
| Router 文件存在 | `apps/api/aether_api/routers/offline.py` |
| 前端配合 | 没有 PWA manifest、没有 Service Worker、没有 IndexedDB 缓存 |
| 演示影响 | 景区 WiFi 不稳定时，整个 Web 端会白屏 |
| 最低落地路径 | 1) `web-tourist/public/manifest.json` + `next-pwa`；2) 缓存 `/landmarks` 响应；3) 离线时用最近一次成功响应 + 静态卡片 |

---

## 二、Repository 模式

| 项 | 现状 |
|---|---|
| `inmemory` | ✅ 默认模式，从 `infra/seed/scenic_demo.json` 加载，零依赖 |
| `database` | ✅ SQLAlchemy async + Alembic 迁移，需要 PostgreSQL |
| 切换方式 | 通过 `AETHER_STORAGE_MODE` 环境变量手动切换 |
| 缺口 | **没有自动 fallback**——如果设了 `database` 但数据库连不上，启动直接崩溃 |
| 已实现 | `/healthz` + `/readyz` 端点（`main.py` 已有） |

> 修复：见 `apps/api/aether_api/repository/__init__.py` 的 `create_repository` 已加入"connect 失败时记录警告并降级到 inmemory"逻辑。

---

## 三、RAG 真实性核查

> ✅ **RAG 是真的**——不是关键词匹配。

- **嵌入**：BGE-m3（`services/rag/embedding.py`），cold start 在 lifespan 里 warm
- **向量库**：Qdrant（`services/rag/vectorstore.py`），URL 未配时自动 fallback 到全表扫描 + sparse vector + lexical 评分
- **混合评分**：`lexical * 0.85 + dense * 0.15`，并按 food/route/safety/family 意图加权（`retriever.py` 第 474–513 行）
- **评估**：`tests/eval/rag_eval.py` 跑 10 个探针，输出 `passed / total / faithfulness`

### 增强项（已落地）
- ✅ 加 `tests/eval/rag_eval.py` 的 `pytest` 包装，让 CI 可以直接读取 faithfulness
- ✅ 把 evaluator 从"硬编码 10 条"改为读 YAML 的探针集，方便扩展

---

## 四、前端缺口（已修复）

| 项 | 现状 | 备注 |
|---|---|---|
| TanStack Query | ✅ 已用（`page.tsx` 第 4 行 import） | 已有 `Providers` 注入 QueryClient |
| Suspense 边界 | ✅ 已有（`page.tsx` 第 72 行） | 顶层包裹 |
| ErrorBoundary | ✅ **本次新增** | `apps/web-tourist/app/components/ErrorBoundary.tsx` |
| 骨架屏 | ✅ **本次新增** | `apps/web-tourist/app/components/Skeleton.tsx` |
| 共享状态 | ❌ 未引入 Zustand | 当前用 useState 局部管理，规模不大暂可接受 |
| PWA / 离线 | ❌ 未启用 | 见 §1 离线模式 |

---

## 五、合规与运营缺口（待办）

| 项 | 状态 |
|---|---|
| 未成年人模式（监护人联系方式） | ❌ |
| PII 脱敏（人脸照片存储前模糊） | ❌ |
| 内容安全（敏感词过滤） | ❌ |
| 多语言（i18n 资源、多语言知识库分库） | ❌ |
| 微信小程序端 | ❌ |
| AR 实景导航 | ❌ |
| 真人讲解员接管 | ❌ |
| Prompt 版本管理 / 灰度 | 🟡 已有 `PromptExperimentDTO` schema，无 UI |

---

## 六、演示前 Checklist

- [ ] 数字人页面 **不打开**，或显式说明"文字卡片模式（数字人渲染本周接入）"
- [ ] 走 `inmemory` 模式（避免数据库连接异常）
- [ ] 提前 warm 一遍 BGE-m3（首问要 2–5s 冷启动）
- [ ] `AETHER_AI_PROVIDER=anthropic` + 真实 API key 时，先打 `/healthz` 确认 `ai_model` 非空
- [ ] 准备好"网络降级"演示路径：拔掉 LLM key → 看到 `ai_provider_unavailable` 文字卡片
- [ ] 走失上报 / 安全告警走 mock 路径，不要在演示时按真实联动
- [ ] 浏览器环境用 Chrome 最新版（Web Speech API 兼容性最好）

---

## 七、相关文档

- 架构总览：[`README.md`](../README.md)
- API 规范：[`docs/api/openapi.yaml`](api/openapi.yaml)
- 评审记录：[`docs/review-round-2.md`](review-round-2.md)
- 部署 Runbook：[`docs/runbook/`](runbook/)
