<div align="center">

<img src="apps/已生成图像 1.png" width="120" alt="Aether Guide Logo">

# Aether Guide

**景区智慧导览 AI 数字人平台**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-4-06B6D4?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Live2D](https://img.shields.io/badge/Live2D-Cubism%205-FF6F00)](https://www.live2d.com/)
[![License](https://img.shields.io/badge/License-Private-red)](#license)

[English](#english) | 中文

</div>

---

## 项目简介

Aether Guide 是一套面向景区的 **AI 数字人智慧导览系统**，采用前后端分离架构，集成了 LLM 对话、RAG 知识检索、多模态定位、安全预警等能力，为游客提供沉浸式的智能导览体验。

> 当前为 MVP 阶段，实现了从游客端交互到后端 AI 响应的第一步闭环。

## 核心功能

<table>
<tr>
<td width="50%">

### 游客端

- **AI 数字人 (Live2D)** — Cubism 5 "Mao Pro" 角色浮窗,眼动跟随鼠标 / 点击触发表情与动作,叠加 LLM 流式对话(SSE)
- **智能导览** — 景点推荐、路线规划、语音讲解
- **拍照识景** — 上传照片自动识别景点
- **安全保障** — 一键求助、走失上报、安全告警
- **匿名访问** — 无需注册即可体验

</td>
<td width="50%">

### 管理端

- **数据大盘** — 实时游客统计、会话分析、热度地图
- **知识管理** — RAG 知识库维护、景区信息管理
- **审计日志** — 全链路操作追踪、用户行为分析
- **氛围设置** — 多场景主题切换（森林/海洋/沙漠/黄昏/湖泊）
- **实验管理** — A/B 测试、功能灰度发布

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
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │            │            │            │                   │
│  ┌────▼────────────▼────────────▼────────────▼────┐             │
│  │              Services Layer                     │             │
│  │  ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌───────┐  │             │
│  │  │ AI  │ │ RAG │ │ Loc  │ │Voice │ │Safety │  │             │
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
│   PostgreSQL       Redis        MinIO       LiveKit             │
│   (pgvector)     (缓存/限流)   (对象存储)    (实时通信)           │
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
| **AI 能力** | LiteLLM (可插拔) · RAG 检索增强 · 向量检索 |
| **基础设施** | PostgreSQL (pgvector) · Redis · MinIO · LiveKit |
| **可观测性** | Prometheus · Grafana · Loki · Tempo |
| **包管理** | uv (Python) · npm workspaces (Node) |

## 快速开始

### 环境要求

- **Python 3.12** + [uv](https://docs.astral.sh/uv/)
- **Node.js 20+** + npm
- **Docker** (可选) — 用于启动 PostgreSQL、Redis 等基础设施

### 🚀 一键启动(推荐)

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

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AETHER_STORAGE_MODE` | `inmemory` | 存储模式：`inmemory` / `database` |
| `AETHER_AI_PROVIDER` | `fake` | AI 提供者：`fake` (回显) / `litellm` |
| `AETHER_DATABASE_URL` | `sqlite+aiosqlite:///...` | 数据库连接串 |
| `AETHER_REDIS_URL` | `redis://localhost:6379/0` | Redis 地址（用于限流） |
| `AETHER_JWT_SECRET` | `dev-only-secret-...` | JWT 密钥，**生产环境必须修改** |
| `AETHER_CORS_ORIGINS` | `*` | CORS 允许来源，逗号分隔 |

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
- `apps/web-tourist/public/live2d/mao_pro/` 下需包含 `model3.json` + `moc3` + motions/expressions/physics/pose/cdi 以及 `mao_pro.4096/texture_00.png`

### 交互行为

| 事件 | 行为 |
|------|------|
| 鼠标移动 | 眼睛跟随光标（`autoInteract`） |
| 点击角色 | 播放随机动作 + 切换表情 |
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
    └── mao_pro/                         # Cubism 5 "Mao Pro" 示例模型
        ├── mao_pro.model3.json
        ├── mao_pro.moc3
        ├── motions/*.motion3.json
        ├── expressions/*.exp3.json
        └── mao_pro.4096/texture_00.png
```

### 替换模型

想换成自己的 Cubism 3/4/5 模型：

1. 将整套模型资产（`.model3.json` + `.moc3` + motions / expressions / textures）放到 `apps/web-tourist/public/live2d/<your-model>/`
2. 修改 `apps/web-tourist/app/page.tsx` 中的挂载：

   ```tsx
   <Live2DMao
     modelUrl="/live2d/<your-model>/<your-model>.model3.json"
     width={280}
     height={420}
   />
   ```

3. 如需接入 TTS 口型同步，可调用组件内部 `model.speak(audioUrl)`（`pixi-live2d-display-lipsyncpatch` 原生支持）。

### 授权说明

> ⚠️ **务必确认**：本项目仓库附带的 `mao_pro` 是 **Live2D 官方示例模型**，并非可无限制再分发的资产。

- **Cubism Core 运行时** (`live2dcubismcore.min.js`) 受 *Live2D Proprietary Software License* 约束，商用时需在产品"关于"页显示 "Live2D Cubism SDK" 版权声明。参见 <https://www.live2d.com/en/sdk/license/>
- **Mao Pro 模型**：普通用户及小规模企业在同意授权协议下可用于商业用途；中/大规模企业只能用于非公开的内部试用。详见 [`apps/web-tourist/public/live2d/mao_pro/LICENSE.txt`](apps/web-tourist/public/live2d/mao_pro/LICENSE.txt) 及 <https://www.live2d.com/zh-CHS/download/sample-data/>
- 生产环境建议替换为自有或已取得授权的模型。

## API 接口

```
认证
  POST   /api/v1/auth/anonymous         游客匿名登录
  POST   /admin/v1/auth/login            管理员登录

游客端
  POST   /api/v1/sessions                创建会话
  POST   /api/v1/chat                     发送消息 (SSE 流式响应)
  GET    /api/v1/landmarks                获取景点列表
  GET    /api/v1/recommendations          获取推荐路线
  POST   /api/v1/feedback                 提交反馈

安全保障
  GET    /api/v1/safety/alerts            获取安全告警
  POST   /api/v1/safety/lost              上报走失人员

管理端
  GET    /admin/v1/summary                数据概览
  GET    /admin/v1/audit                  审计日志
  GET    /admin/v1/experiments            实验管理
  GET    /admin/v1/knowledge              知识库管理
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
│   │   │   ├── schemas/        # 请求/响应 Schema
│   │   │   ├── services/       # 业务服务 (AI / RAG / 定位 / 语音 / 安全)
│   │   │   └── worker/         # 后台任务
│   │   └── alembic/            # 数据库迁移
│   ├── web-tourist/            # 游客端 (Next.js)
│   │   ├── app/components/
│   │   │   └── Live2DMao.tsx   # Live2D 数字人浮窗组件
│   │   └── public/live2d/      # Cubism Core + mao_pro 模型资产
│   └── web-admin/              # 管理端 (Next.js)
├── packages/
│   └── design-system/          # 共享设计系统
├── infra/
│   ├── docker-compose.yml      # 基础设施编排
│   └── seed/                   # 演示数据
├── docs/                       # 项目文档
├── scripts/                    # 开发脚本
└── tests/                      # 测试 (E2E / 评估 / 性能)
```

## 测试

```bash
# 后端测试
powershell -ExecutionPolicy Bypass -File scripts\test.ps1

# 前端检查
npm run web:lint          # ESLint
npm run web:typecheck     # TypeScript 类型检查
npm run web:build         # 生产构建
```

## 部署

### Docker Compose (一键启动全部基础设施)

```bash
docker compose -f infra/docker-compose.yml up -d
```

包含：PostgreSQL · Redis · MinIO · LiveKit · Prometheus · Grafana · Loki · Tempo

### K3s (轻量级 Kubernetes)

部署配置参见 [`infra/k3s/`](infra/k3s/)

## 致谢

本项目的技术选型和架构设计参考了以下优秀项目：

- [FastAPI](https://fastapi.tiangolo.com/) — 现代高性能 Python Web 框架
- [Next.js](https://nextjs.org/) — React 全栈框架
- [LiteLLM](https://github.com/BerriAI/litellm) — 统一 LLM 调用层
- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL 向量检索扩展
- [Live2D Cubism](https://www.live2d.com/) — 2D 数字人动画引擎与 "Mao Pro" 示例模型
- [pixi-live2d-display-lipsyncpatch](https://github.com/RaSan147/pixi-live2d-display) — PIXI 7 + Cubism 4/5 兼容的 Live2D 插件
- [PixiJS](https://pixijs.com/) — 高性能 2D WebGL 渲染引擎

---

<div align="center">

**Aether Guide** — 让每一次旅行都有 AI 陪伴

</div>

---

<a id="english"></a>

## English

**Aether Guide** is an AI-powered digital human guide platform for scenic areas. It features LLM-based conversational AI, RAG knowledge retrieval, multi-modal positioning, and safety alerting — delivering an immersive smart tour experience.

A **Live2D Cubism 5** avatar (Mao Pro) is rendered as a floating guide on the tourist home page via `pixi.js` + `pixi-live2d-display-lipsyncpatch`. The model tracks the cursor, reacts to taps with random motions/expressions, and can be swapped out for any Cubism 3/4/5 `.model3.json` asset.

See the [API spec](docs/api/openapi.yaml), the [architecture diagram](#技术架构), and the [数字人 (Live2D)](#数字人-live2d) section above for details.

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

The bundled **Mao Pro** model and `live2dcubismcore.min.js` runtime are proprietary Live2D Inc. assets. Commercial deployment requires agreement to the [Live2D Sample Data License](https://www.live2d.com/en/download/sample-data/) and the [Live2D Proprietary Software License](https://www.live2d.com/en/sdk/license/). Replace with your own licensed model for production use.

### License

Private — not for distribution.
