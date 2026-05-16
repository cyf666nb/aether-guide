<div align="center">

<img src="apps/已生成图像 1.png" width="120" alt="Aether Guide Logo">

# Aether Guide

**景区智慧导览 AI 数字人平台**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4-06B6D4?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![AMap](https://img.shields.io/badge/AMap-JSAPI%20v2.0-0685D4)](https://lbs.amap.com/)
[![Live2D](https://img.shields.io/badge/Live2D-Cubism%205-FF6F00)](https://www.live2d.com/)
[![License](https://img.shields.io/badge/License-Private-red)](#license)

[English](#english) | 中文

</div>

---

## 项目简介

Aether Guide 是一套面向景区的 **AI 数字人智慧导览系统**，采用前后端分离架构，集成了 LLM 对话、RAG 知识检索、多模态定位、安全预警等能力，为游客提供沉浸式的智能导览体验。

> 当前为 MVP 阶段，实现了从游客端交互到后端 AI 响应的第一步闭环。
> 
> 📋 **项目进度与差距**：详见 [`docs/review-and-roadmap-2026-05-16.md`](docs/review-and-roadmap-2026-05-16.md)（2026-05-16 全面体检 + 0–5 周开发规划）
> 
> ⚠️ **当前已知差距**：
> - 数字人仅实现客户端 Live2D 渲染，暂无 TTS 口型同步与 LiveKit 实时渲染
> - 语音识别（ASR）/ 端点检测（VAD）计划在 W1 实现，当前仅支持文字输入
> - 离线模式后端已就绪，前端 PWA / Service Worker 计划在 W3 实现
> - PII 脱敏、内容安全、未成年人模式计划在 W4 上线

## 核心功能

<table>
<tr>
<td width="50%">

### 游客端

- **AI 数字人 (Live2D)** — Cubism 5 "Haru Greeter" 角色浮窗，眼动跟随鼠标 / 点击触发表情与动作，叠加 LLM 流式对话 (WebSocket)
- **高德地图** — AMap JSAPI v2.0 深色风格地图，景点标记 + POI 搜索
- **智能导览** — 景点轮播、路线规划、AI 语音讲解 (TTS)
- **多模态定位** — 视觉定位 (VPS)、QR 码锚点、对话式定位、融合定位
- **拍照识景** — 上传照片 AI 自动识别景点并解说
- **安全保障** — 一键求助、走失上报、紧急点查询
- **离线模式** — 支持离线数据包下载，无网络时仍可浏览景点信息
- **匿名访问** — 无需注册即可体验

</td>
<td width="50%">

### 管理端

- **数据大盘** — 实时游客统计、会话分析、热度地图、Token 成本监控
- **知识管理** — RAG 知识库维护、文档上传与索引、景区信息管理
- **审计日志** — 全链路操作追踪、用户行为分析
- **氛围设置** — 多场景主题切换（森林/海洋/沙漠/黄昏/湖泊）
- **实验管理** — A/B 测试、Prompt 实验、功能灰度发布
- **会话回放** — 游客会话历史回放与标注
- **人设管理** — 数字人人设配置、语音与头像绑定

</td>
</tr>
</table>

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端 (Client)                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │   web-tourist    │  │    web-admin     │  │   小程序/App   │  │
│  │   Next.js 15     │  │   Next.js 15     │  │   (规划中)     │  │
│  └────────┬─────────┘  └────────┬─────────┘  └───────┬───────┘  │
└───────────┼─────────────────────┼─────────────────────┼──────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI 后端 (API)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │   Auth   │ │  Tourist │ │  Admin   │ │  Safety  │  Routers   │
│  │  Avatar  │ │ Location │ │ Offline  │ │Recommend │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                   │
│  ┌────▼────────────▼────────────▼────────────▼────┐             │
│  │              Services Layer                     │             │
│  │  ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌───────┐  │             │
│  │  │ AI  │ │ RAG │ │ Loc  │ │Voice │ │Safety │  │             │
│  │  │ TTS │ │Digital│ │Recommend│ │     │ │       │  │             │
│  │  └─────┘ └─────┘ └──────┘ └──────┘ └───────┘  │             │
│  └────────────────────────────────────────────────┘             │
│       │            │            │            │                   │
│  ┌────▼────────────▼────────────▼────────────▼────┐             │
│  │          Repository (In-Memory / SQL)           │             │
│  └────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        基础设施 (Infra)                          │
│   PostgreSQL       Redis        Qdrant      MinIO               │
│   (pgvector)     (缓存/限流)   (向量检索)   (对象存储)            │
│                                                                  │
│   Prometheus  +  Grafana  +  Loki  +  Tempo  (可观测性)         │
└─────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术选型 |
|------|---------|
| **前端** | Next.js 15 · React 19 · Tailwind CSS 4 · TanStack Query |
| **数字人** | Live2D Cubism 5 Core · pixi.js 7 · pixi-live2d-display-lipsyncpatch |
| **后端** | FastAPI · Pydantic v2 · SQLAlchemy (async) · Alembic |
| **AI 能力** | LiteLLM · Anthropic · OpenAI (可插拔) · RAG 检索增强 · 向量检索 (Qdrant) |
| **TTS 语音** | MiMo TTS (小米) · 支持自定义语音角色 |
| **视觉定位** | VPS (Visual Positioning Service) · QR 码锚点 · 对话式定位 · 融合定位 |
| **基础设施** | PostgreSQL (pgvector) · Redis · Qdrant · MinIO |
| **可观测性** | Prometheus · Grafana · Loki · Tempo |
| **包管理** | uv (Python) · npm workspaces (Node) |

## 快速开始

### 环境要求

- **Python 3.12** + [uv](https://docs.astral.sh/uv/)
- **Node.js 20+** + npm
- **Docker** (可选) — 用于启动 PostgreSQL、Redis 等基础设施

### 一键启动(推荐)

**Windows** — 双击项目根目录的 `start.cmd` 即可,或命令行:

```powershell
.\start.cmd
# 可选参数:-NoAdmin / -NoTourist / -Docker / -Clean / -SkipInstall
```

**macOS / Linux**:

```bash
./start.sh
# 或:make start
```

一键脚本会自动完成以下步骤:

1. 预检 `uv` / `node` / `npm` 工具链
2. 若 `node_modules` 或 `.venv` 缺失自动安装依赖(首次运行约 3-5 分钟)
3. 释放 8000 / 3001 / 3002 端口上的残留进程
4. 同时启动 **API + 游客端 + 管理端**(Windows 下各服务独立控制台窗口)
5. HTTP 健康探测就绪后自动打开浏览器访问游客端
6. `Ctrl+C` 优雅停止所有服务并清理端口

### 手动启动(按服务逐个拉起)

### 1. 克隆项目

```bash
git clone https://github.com/cyf666nb/aether-guide.git
cd aether-guide
```

### 2. 启动后端

**Windows:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\demo.ps1
```

**macOS / Linux:**

```bash
make demo
```

后端默认以 `fake` AI 提供者 + `inmemory` 存储模式启动，**无需任何外部依赖**，开箱即用。

API 地址：http://localhost:8000 · 交互式文档：http://localhost:8000/docs

### 3. 启动前端

```bash
# 安装依赖
npm install

# 启动游客端 (端口 3001)
npm run web:dev:tourist

# 启动管理端 (端口 3002)
npm run web:dev:admin
```

> Windows 用户请使用 `cmd /c npm ...` 执行命令，避免 PowerShell 执行策略限制。

### 4. 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| API 文档 | http://localhost:8000/docs | Swagger UI 交互式文档 |
| 游客端 | http://localhost:3001 | 面向游客的导览界面 |
| 管理端 | http://localhost:3002 | 后台管理大盘 |

## 环境配置

所有配置项以 `AETHER_` 为前缀，支持环境变量和 `.env` 文件。完整配置参见 [`.env.example`](.env.example)。

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_STORAGE_MODE` | `inmemory` | 存储模式：`inmemory` / `database` |
| `AETHER_AI_PROVIDER` | `fake` | AI 提供者：`fake` (回显) / `litellm` / `anthropic` / `openai` |
| `AETHER_DATABASE_URL` | `sqlite+aiosqlite:///...` | 数据库连接串 |
| `AETHER_REDIS_URL` | `redis://localhost:6379/0` | Redis 地址（用于限流） |
| `AETHER_JWT_SECRET` | `dev-only-secret-...` | JWT 密钥，**生产环境必须修改** |
| `AETHER_CORS_ORIGINS` | `*` | CORS 允许来源，逗号分隔 |

### AI 模型配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_ANTHROPIC_API_KEY` | - | Anthropic API 密钥 |
| `AETHER_ANTHROPIC_BASE_URL` | `https://ark.cn-beijing.volces.com/api/coding` | Anthropic API 基础 URL |
| `AETHER_ANTHROPIC_MODEL` | - | Anthropic 模型名称 |
| `AETHER_OPENAI_API_KEY` | - | OpenAI API 密钥 |
| `AETHER_OPENAI_BASE_URL` | `https://ark.cn-beijing.volces.com/api/coding/v3` | OpenAI API 基础 URL |
| `AETHER_LLM_TIMEOUT_SECONDS` | `6.0` | LLM 请求超时时间（秒） |
| `AETHER_LLM_MAX_TOKENS` | `700` | LLM 最大生成 Token 数 |
| `AETHER_LLM_TEMPERATURE` | `0.3` | LLM 温度参数 (0.0-1.0) |
| `AETHER_LLM_THINKING_TYPE` | `disabled` | 思考模式：`disabled` / `enabled` / `adaptive` / `auto` / `omit` |
| `AETHER_LLM_THINKING_BUDGET_TOKENS` | - | 思考模式 Token 预算 |
| `AETHER_LLM_MAX_RETRIES` | `2` | LLM 请求最大重试次数 |

### TTS 语音配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_TTS_API_KEY` | - | TTS API 密钥 |
| `AETHER_TTS_BASE_URL` | `https://token-plan-cn.xiaomimimo.com/v1` | TTS API 基础 URL |
| `AETHER_TTS_MODEL` | `mimo-v2.5-tts` | TTS 模型名称 |
| `AETHER_TTS_VOICE` | `female-tianmei` | TTS 语音角色 |

### 视觉定位配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_VLM_MODEL` | `doubao-seed-2.0-pro` | 视觉语言模型名称 |

### 向量检索配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_QDRANT_URL` | - | Qdrant 向量数据库地址 |
| `AETHER_QDRANT_API_KEY` | - | Qdrant API 密钥 |
| `AETHER_EMBEDDING_MODEL` | `BAAI/bge-m3` | 嵌入模型名称 |
| `AETHER_EMBEDDING_USE_GPU` | `false` | 是否使用 GPU 加速嵌入计算 |

### 限流配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_RATE_LIMIT_PER_MINUTE` | `120` | 每分钟请求限制 |

### 使用数据库模式

```bash
# 启动基础设施
docker compose -f infra/docker-compose.yml up -d postgres redis minio

# 切换为数据库模式
export AETHER_STORAGE_MODE=database
export AETHER_DATABASE_URL="postgresql+asyncpg://aether:aether@localhost:5432/aether"

# 运行迁移并启动
make demo
```

## 数字人 (Live2D)

游客端内置了一个 Live2D Cubism 5 数字人作为导览助手 **"知行"**，默认挂载在主页右下角。

### 运行要求

- 浏览器需支持 **WebGL 2.0**（主流浏览器均已支持）
- `apps/web-tourist/public/live2d/live2dcubismcore.min.js` 必须存在（Cubism Core 运行时，约 200 KB）
- `apps/web-tourist/public/live2d/haru_greeter/` 下需包含 `model3.json` + `moc3` + motions/physics/pose/cdi 以及纹理资源

### 交互行为

| 事件 | 行为 |
|------|------|
| 鼠标移动 | 眼睛跟随光标（`autoInteract`） |
| 点击角色 | 播放随机动作 + 切换表情 |
| AI 语音 | 自动口型同步 (lipsync via `pixi-live2d-display-lipsyncpatch`) |
| 视口尺寸变化 | `ResizeObserver` 自适应画布 |
| 组件卸载 | 销毁 PIXI Application 与模型，释放 WebGL 上下文 |

### 关键文件

```
apps/web-tourist/
├── app/
│   ├── layout.tsx                       # 以 beforeInteractive 策略预加载 Cubism Core
│   ├── page.tsx                         # 在 <main> 末尾以 next/dynamic(ssr:false) 挂载浮窗
│   ├── components/Live2DMao.tsx         # 数字人客户端组件
│   └── linjing.css                      # .live2d-mao-floating 定位样式
└── public/live2d/
    ├── live2dcubismcore.min.js          # Live2D 官方 Cubism 5 Core 运行时
    └── haru_greeter/                    # Cubism 5 "Haru Greeter" 示例模型
        ├── haru_greeter_t05.model3.json
        ├── haru_greeter_t05.moc3
        ├── haru_greeter_t05.cdi3.json
        ├── haru_greeter_t05.physics3.json
        ├── haru_greeter_t05.pose3.json
        ├── motions/*.motion3.json
        └── haru_greeter_t05.2048/texture_00.png
```

### 替换模型

想换成自己的 Cubism 3/4/5 模型：

1. 将整套模型资产（`.model3.json` + `.moc3` + motions / expressions / textures）放到 `apps/web-tourist/public/live2d/<your-model>/`
2. 修改 `apps/web-tourist/app/components/Live2DMao.tsx` 中的 `modelUrl` prop

3. 如需接入 TTS 口型同步，可调用组件内部 `model.speak(audioUrl)`（`pixi-live2d-display-lipsyncpatch` 原生支持）。

### 授权说明

> ⚠️ **务必确认**：本项目仓库附带的 `haru_greeter` 是 **Live2D 官方示例模型**，并非可无限制再分发的资产。

- **Cubism Core 运行时** (`live2dcubismcore.min.js`) 受 *Live2D Proprietary Software License* 约束，商用时需在产品"关于"页显示 "Live2D Cubism SDK" 版权声明。参见 <https://www.live2d.com/en/sdk/license/>
- **Haru Greeter 模型**：普通用户及小规模企业在同意授权协议下可用于商业用途；中/大规模企业只能用于非公开的内部试用。详见 <https://www.live2d.com/en/download/sample-data/>
- 生产环境建议替换为自有或已取得授权的模型。

## API 接口

```
认证
  POST   /api/v1/auth/anonymous         游客匿名登录
  POST   /admin/v1/auth/login            管理员登录

游客端
  POST   /api/v1/sessions                创建会话
  GET    /api/v1/landmarks                获取景点列表
  POST   /api/v1/recommendations/route   获取推荐路线
  POST   /api/v1/sessions/{id}/photo     拍照识景
  POST   /api/v1/tts                     文本转语音
  POST   /api/v1/feedback                提交反馈
  WS     /api/v1/sessions/{id}/stream    AI 对话流 (WebSocket)

数字人
  GET    /api/v1/avatar/manifest          获取 Live2D 数字人配置清单

多模态定位
  POST   /api/v1/location/visual          视觉定位 (VPS)
  POST   /api/v1/location/qr              QR 码锚点定位
  POST   /api/v1/location/conversational  对话式定位
  POST   /api/v1/location/fuse            融合定位
  DELETE /api/v1/location/trail           清除用户轨迹

安全保障
  POST   /api/v1/safety/lost              上报走失人员
  GET    /api/v1/safety/emergency-points  获取紧急点列表

离线模式
  GET    /api/v1/scenic/{id}/offline-pack 获取离线数据包

管理端
  GET    /admin/v1/dashboard/overview     数据大盘概览
  POST   /admin/v1/documents              上传知识文档
  GET    /admin/v1/documents/{id}/progress 文档索引进度
  POST   /admin/v1/personas               配置数字人人设
  POST   /admin/v1/prompts/experiments    创建 Prompt 实验
  GET    /admin/v1/sessions/{id}/replay   会话回放
  POST   /admin/v1/turns/{id}/label       标注对话轮次
  GET    /admin/v1/audit-logs             审计日志

系统
  GET    /healthz                         健康检查
  GET    /readyz                          就绪检查
```

完整接口文档：[`docs/api/openapi.yaml`](docs/api/openapi.yaml)

## 项目结构

```
aether-guide/
├── apps/
│   ├── api/                    # FastAPI 后端
│   │   ├── aether_api/
│   │   │   ├── auth/           # 认证模块 (JWT + bcrypt)
│   │   │   ├── middleware/     # 中间件 (CORS / 限流 / 审计 / 链路追踪)
│   │   │   ├── models/         # 数据模型
│   │   │   ├── repository/     # 存储层 (内存 / SQL)
│   │   │   ├── routers/        # 路由控制器
│   │   │   │   ├── auth.py     # 认证路由
│   │   │   │   ├── tourist.py  # 游客端路由
│   │   │   │   ├── admin.py    # 管理端路由
│   │   │   │   ├── avatar.py   # 数字人路由
│   │   │   │   ├── location.py # 多模态定位路由
│   │   │   │   ├── recommendations.py # 路线推荐路由
│   │   │   │   ├── safety.py   # 安全保障路由
│   │   │   │   ├── offline.py  # 离线模式路由
│   │   │   │   └── audit.py    # 审计日志路由
│   │   │   ├── schemas/        # 请求/响应 Schema
│   │   │   ├── services/       # 业务服务
│   │   │   │   ├── ai/         # AI 对话服务 (LiteLLM / Anthropic / OpenAI)
│   │   │   │   ├── rag/        # RAG 知识检索服务
│   │   │   │   │   ├── embedding.py   # 嵌入模型 (BGE)
│   │   │   │   │   ├── vectorstore.py # 向量存储 (Qdrant)
│   │   │   │   │   ├── retriever.py   # 检索器
│   │   │   │   │   ├── indexer.py     # 索引器
│   │   │   │   │   └── evaluator.py   # 评估器
│   │   │   │   ├── location/   # 多模态定位服务
│   │   │   │   │   ├── vps.py           # 视觉定位 (VPS)
│   │   │   │   │   ├── qr.py            # QR 码锚点定位
│   │   │   │   │   ├── conversational.py # 对话式定位
│   │   │   │   │   └── fusion.py        # 融合定位
│   │   │   │   ├── digital_human/ # 数字人服务
│   │   │   │   ├── tts/         # TTS 语音合成服务
│   │   │   │   ├── voice/       # 语音处理服务
│   │   │   │   ├── recommend/   # 路线推荐服务
│   │   │   │   ├── safety/      # 安全保障服务
│   │   │   │   └── common/      # 公共服务
│   │   │   └── worker/         # 后台任务
│   │   ├── alembic/            # 数据库迁移
│   │   └── tests/              # 后端测试
│   ├── web-tourist/            # 游客端 (Next.js)
│   │   ├── app/
│   │   │   ├── page.tsx        # 主页 (地图 + 数字人 + 聊天)
│   │   │   ├── landmarks/      # 景点列表页
│   │   │   ├── photo/          # 拍照识景页
│   │   │   ├── route/          # 路线规划页
│   │   │   ├── components/     # 组件
│   │   │   │   ├── AmapView.tsx     # 高德地图组件
│   │   │   │   ├── Live2DMao.tsx    # Live2D 数字人组件
│   │   │   │   ├── IntroScreen.tsx  # 引导页
│   │   │   │   ├── TextStream.tsx   # 文本流组件
│   │   │   │   └── VisitorChrome.tsx # 游客端框架
│   │   │   └── lib/            # 工具库
│   │   └── public/live2d/      # Cubism Core + Haru Greeter 模型资产
│   └── web-admin/              # 管理端 (Next.js)
│       ├── app/
│       │   ├── page.tsx        # 数据大盘
│       │   ├── knowledge/      # 知识库管理
│       │   ├── experiments/    # 实验管理
│       │   ├── replay/         # 会话回放
│       │   ├── settings/       # 设置
│       │   │   └── atmosphere/ # 氛围设置
│       │   ├── login/          # 登录页
│       │   ├── components/     # 组件
│       │   │   ├── AdminShell.tsx # 管理端框架
│       │   │   └── Charts.tsx     # 图表组件
│       │   └── lib/            # 工具库
│       └── public/             # 静态资源
├── packages/
│   └── design-system/          # 共享设计系统
│       └── src/
│           ├── index.ts        # 入口文件
│           ├── styles.css      # 样式
│           ├── icons.tsx       # 图标组件
│           ├── typography.tsx  # 排版组件
│           └── demo-data.ts    # 演示数据
├── infra/
│   ├── docker-compose.yml      # 基础设施编排
│   ├── k3s/                    # K3s 部署配置
│   ├── grafana-dashboards/     # Grafana 仪表盘
│   └── seed/                   # 演示数据
│       ├── scenic_demo.json    # 景点种子数据
│       └── admins.yaml         # 管理员种子数据
├── docs/                       # 项目文档
│   ├── api/                    # API 文档
│   ├── decisions/              # 架构决策记录
│   ├── design/                 # 设计文档
│   ├── runbook/                # 运维手册
│   ├── MVP_GAP.md              # MVP 差距分析
│   └── review-round-2.md       # 评审记录
├── scripts/                    # 开发脚本
│   ├── start.ps1               # Windows 启动脚本
│   ├── demo.ps1                # Windows 演示脚本
│   ├── test.ps1                # Windows 测试脚本
│   ├── eval.ps1                # Windows 评估脚本
│   ├── perf.ps1                # Windows 性能测试脚本
│   ├── export_openapi.py       # 导出 OpenAPI 文档
│   └── web-lint.mjs            # 前端 Lint 脚本
├── tests/                      # 测试
│   ├── e2e/                    # 端到端测试
│   ├── eval/                   # 评估测试
│   └── perf/                   # 性能测试
├── package.json                # npm 工作区配置
├── pyproject.toml              # uv 工作区配置
├── tsconfig.base.json          # TypeScript 基础配置
├── Makefile                    # Make 命令
├── start.cmd                   # Windows 一键启动
└── start.sh                    # macOS/Linux 一键启动
```

## 高德地图 & 景点坐标

游客端主页集成 AMap JSAPI v2.0 深色风格地图，展示三坊七巷 19 个精选景点标记。

### 坐标校准

种子数据 (`infra/seed/scenic_demo.json`) 中的景点坐标通过 AMap PlaceSearch 插件搜索校准，使用 GCJ-02 坐标系，17/19 个景点由高德 POI 直接确认。

如需重新校准（例如更换景区），可在浏览器控制台运行：

```js
await window.__calibrate()
```

或打开独立校准页面 `scripts/calibrate.html` 逐个搜索景点并复制输出的 JSON。

### 环境变量

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_AMAP_KEY` | 高德 JSAPI v2.0 Key |
| `NEXT_PUBLIC_AMAP_SECURITY_JS_CODE` | 高德 JSAPI v2.0 安全密钥 |

## 测试

```bash
# 后端测试
powershell -ExecutionPolicy Bypass -File scripts\test.ps1

# 前端检查
npm run web:lint          # ESLint
npm run web:typecheck     # TypeScript 类型检查
npm run web:build         # 生产构建

# RAG 评估
make eval

# 性能测试
make perf
```

## 部署

### Docker Compose (一键启动全部基础设施)

```bash
docker compose -f infra/docker-compose.yml up -d
```

包含：PostgreSQL · Redis · Qdrant · MinIO · Prometheus · Grafana · Loki · Tempo

### K3s (轻量级 Kubernetes)

部署配置参见 [`infra/k3s/`](infra/k3s/)

## 致谢

本项目的技术选型和架构设计参考了以下优秀项目：

- [FastAPI](https://fastapi.tiangolo.com/) — 现代高性能 Python Web 框架
- [Next.js](https://nextjs.org/) — React 全栈框架
- [LiteLLM](https://github.com/BerriAI/litellm) — 统一 LLM 调用层
- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL 向量检索扩展
- [Qdrant](https://qdrant.tech/) — 高性能向量数据库
- [Live2D Cubism](https://www.live2d.com/) — 2D 数字人动画引擎与 "Haru Greeter" 示例模型
- [pixi-live2d-display-lipsyncpatch](https://github.com/RaSan147/pixi-live2d-display) — PIXI 7 + Cubism 4/5 兼容的 Live2D 插件
- [PixiJS](https://pixijs.com/) — 高性能 2D WebGL 渲染引擎
- [MiMo TTS](https://xiaomi.com) — 小米 MiMo TTS 语音合成服务

---

<div align="center">

**Aether Guide** — 让每一次旅行都有 AI 陪伴

</div>

---

<a id="english"></a>

## English

**Aether Guide** is an AI-powered digital human guide platform for scenic areas. It features LLM-based conversational AI, RAG knowledge retrieval, multi-modal positioning, and safety alerting — delivering an immersive smart tour experience.

A **Live2D Cubism 5** avatar (Haru Greeter) is rendered as a floating guide on the tourist home page via `pixi.js` + `pixi-live2d-display-lipsyncpatch`. The model tracks the cursor, reacts to taps with random motions/expressions, auto-lipsyncs with TTS audio, and can be swapped out for any Cubism 3/4/5 `.model3.json` asset.

### Key Features

**Tourist App:**
- AI Digital Human (Live2D) — Cubism 5 "Haru Greeter" floating avatar with eye-tracking, tap interactions, and LLM streaming dialog (WebSocket)
- AMap Integration — AMap JSAPI v2.0 dark-style map with landmark markers and POI search
- Smart Navigation — Landmark carousel, route planning, AI voice narration (TTS)
- Multi-modal Positioning — Visual Positioning (VPS), QR code anchoring, conversational positioning, fused positioning
- Photo Recognition — Upload photos for AI-powered landmark identification and narration
- Safety Features — One-click emergency help, lost person reporting, emergency point lookup
- Offline Mode — Download offline data packs for browsing without network
- Anonymous Access — No registration required

**Admin Dashboard:**
- Real-time Analytics — Live tourist statistics, session analysis, heatmap, Token cost monitoring
- Knowledge Management — RAG knowledge base maintenance, document upload and indexing
- Audit Logs — Full-chain operation tracking, user behavior analysis
- Atmosphere Settings — Multi-scene theme switching (Forest/Ocean/Desert/Dusk/Lake)
- Experiment Management — A/B testing, Prompt experiments, feature flagging
- Session Replay — Tourist session history playback and annotation
- Persona Management — Digital human persona configuration, voice and avatar binding

### Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 15 · React 19 · Tailwind CSS 4 · TanStack Query |
| **Digital Human** | Live2D Cubism 5 Core · pixi.js 7 · pixi-live2d-display-lipsyncpatch |
| **Backend** | FastAPI · Pydantic v2 · SQLAlchemy (async) · Alembic |
| **AI** | LiteLLM · Anthropic · OpenAI (pluggable) · RAG · Vector Search (Qdrant) |
| **TTS** | MiMo TTS (Xiaomi) · Custom voice roles |
| **Positioning** | VPS · QR Code Anchoring · Conversational · Fused |
| **Infrastructure** | PostgreSQL (pgvector) · Redis · Qdrant · MinIO |
| **Observability** | Prometheus · Grafana · Loki · Tempo |
| **Package Management** | uv (Python) · npm workspaces (Node) |

### Quick Start

```bash
# Backend (fake AI + in-memory storage, zero dependencies)
make demo                          # macOS / Linux
powershell -File scripts\demo.ps1  # Windows

# Frontend
npm install
npm run web:dev:tourist  # http://localhost:3001
npm run web:dev:admin    # http://localhost:3002
```

### Live2D Licensing Notice

The bundled **Haru Greeter** model and `live2dcubismcore.min.js` runtime are proprietary Live2D Inc. assets. Commercial deployment requires agreement to the [Live2D Sample Data License](https://www.live2d.com/en/download/sample-data/) and the [Live2D Proprietary Software License](https://www.live2d.com/en/sdk/license/). Replace with your own licensed model for production use.

### License

Private — not for distribution.