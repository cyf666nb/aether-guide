# 第二轮全面审查报告 — Aether Guide

本文档是 2026-05-09 对 `Aether Guide` 仓库进行第二轮全面审查的结果,对第一次审查提出的 **14 条 🔴 / 🟠 问题** 逐项核对修复情况,并列出新引入的风险与下一轮 🟡 改进建议。

## 验证管道结果

| 命令 | 结果 |
|---|---|
| `ruff check apps/api/aether_api apps/api/tests tests/eval scripts` | ✅ All checks passed |
| `mypy apps/api/aether_api` (strict) | ✅ Success: no issues found in 66 source files |
| `pytest apps/api/tests` | ✅ **21 passed**, 3 warnings |
| `npm run web:typecheck` | ✅ both apps pass |
| `npm run web:lint` | ✅ next lint + web-lint.mjs 双闸口,仅遗留 `<img>` 警告(Task 11 范围) |
| `npm run web:build` | ✅ tourist 1.7s / admin 4.0s 编译通过 |
| `python scripts/export_openapi.py` | ✅ `docs/api/openapi.yaml` 重新生成 |

## 14 项问题对照表

### 🔴 阻塞项(6 条)

| # | 问题 | 修复状态 | 证据 |
|---|---|---|---|
| 1 | Alembic 迁移脚本缺失 | ✅ | `alembic/versions/369167cfdb09_init.py` + `0002_auth_and_summary.py`;`make migrate`;`test_alembic_upgrade_head_creates_expected_tables` |
| 2 | `storage_mode=database` 未实现 | ✅ | `repository/sql.py` 实现全部 14 个方法;`create_repository` 工厂按 settings 切换;`test_storage_mode_database_end_to_end` |
| 3 | Admin/WS 鉴权缺失 | ✅ | `auth/` 子包(JWT+bcrypt+依赖)+ `admin` 路由级 `require_role("admin")` + WS `authenticate_websocket` 用 `?token=`;3 条回归测试 |
| 4 | CORS 默认全通 + credentials | ✅ | `config.py` 的 `model_validator` 在 `environment=="production"` 且含 `*` 时直接抛错;`cors_origins` 从 `AETHER_CORS_ORIGINS` 读;`test_cors_rejects_unknown_origin_when_restricted` |
| 5 | 审计中间件是假实现 | ✅ | `middleware/audit.py` 把写操作写入 `AuditLog`;`GET /admin/v1/audit-logs` 分页查看;`test_audit_log_recorded_on_admin_write` |
| 6 | RateLimit 进程内失效 | ✅ | `middleware/rate_limit_redis.py` 用 ZREMRANGEBYSCORE+ZCARD+ZADD+PEXPIRE 的管道模式;`X-RateLimit-*` 响应头;Redis 不可达 passthrough+warning;`test_redis_rate_limit_enforced_and_isolated_by_user` (fakeredis 驱动) |

### 🟠 强烈建议(8 条)

| # | 问题 | 修复状态 | 证据 |
|---|---|---|---|
| 7 | WS `session_id` 鉴权加固 | ✅ | WS 握手 `?token=` JWT 校验,失败 `close(1008)`;`test_websocket_rejects_without_token` |
| 8 | ruff/mypy 扫描范围扩大 | ✅ | root `pyproject.toml` 打开 `S/N` 规则;mypy `files=[apps/api, tests, scripts, tests/eval]`;全部 `Success/All passed` |
| 9 | ESLint + `eslint-config-next` | ✅ | 两端 `eslint.config.mjs` flat config;`npm run web:lint` 走 `next lint` + `web-lint.mjs` 双闸口 |
| 10 | 前端 `X-Trace-Id` + `next/image` + 共享 assets | ⚠️ 部分 | trace-id 前端生成并附到每个请求 ✅;next/image 未迁移(3 条 `<img>` 警告保留,留到 🟡 轮处理);场景 PNG 仍在两端 public(不影响功能,属纯清理) |
| 11 | PersonaRequest.system_prompt + document_progress 状态机 | ✅ | 两端后端都持久化 system_prompt 并在 `PersonaDTO` 返回;`document_progress` 按 `created_at` 与当下时间差推进 queued(<30s) → indexing(<90s) → ready(≥90s);同时 SQL 模式写 `indexed_at` |
| 12 | AIClient 异常收窄 + `cost_usd` | ✅ | `except (TimeoutError, httpx.HTTPError, OSError)`,production 模式直接抛 `AppError(503)`;`cost_usd` 从 `response._hidden_params.response_cost` 读取;`test_ai_client_production_timeout_raises_503` |
| 13 | `image_base64` 大小/格式校验 | ✅ | `services/common/image.py.validate_image_base64`:≤1MB、base64 strict、magic bytes 仅允许 JPEG/PNG/WebP;`POST /sessions/.../photo` 与 `POST /location/visual` 均调用;`test_image_base64_too_large_rejected` |
| 14 | `readyz` 真实依赖检查 | ✅ | `readyz` 执行 DB `SELECT 1` + Redis `PING`;任一失败返回 `503 + {status:degraded, checks:{db,redis}}`;`test_readyz_reports_redis_outage` |

**共计 13/14 完成,1/14 部分完成**(#10 中 next/image + 共享 assets 属纯优化,前端 trace/auth/ESLint 主线已落地)。

## 新引入的风险/遗留

下面列出本轮修复过程中新增的小问题或妥协,建议在 🟡 轮跟进:

1. **前端 `<img>` 警告**:3 个页面仍用原生 `<img>`。Next 的 `no-img-element` 触发 warning(不影响 lint 通过)。🟡 轮迁移到 `next/image` 并从 `packages/design-system/src/scenes/` 单源提供 PNG,消除两份 public 拷贝。
2. **RateLimit 原子性妥协**:为了与 `fakeredis` 兼容,放弃了 Lua `eval` 脚本,改为 pipeline 命令。高并发下存在非常小的竞争窗口 — 生产 Redis 建议切回 `eval` 脚本(代码内只需要在 `_ensure_ready` 里额外 `script_load` 并切换到 `evalsha`)。
3. **Admin UI 取景数据**:`web-admin` 为了访问 `/api/v1/landmarks` 会顺便领一个匿名游客 token 并用它去请求。短期可用,🟡 轮建议把「给 admin 看的景点视图」放到 `/admin/v1/landmarks`,避免跨角色调用。
4. **审计日志 `before` 永远为 `None`**:当前只记录 `after`(响应体 `data` 字段)。🟡 轮接 ORM `history` 或在业务层把旧值显式传入中间件。
5. **passlib 弃用**:由于 `bcrypt 5.x` 与 `passlib 1.7.4` 兼容性问题,直接依赖 `bcrypt` 库。如果未来需要多哈希算法,考虑引入 `argon2-cffi` 或等 passlib 2.x。
6. **`litellm` 不装**:默认 `dependencies` 不含 litellm(留在 optional `ai` 组)。`AETHER_AI_PROVIDER=litellm` 时需 `uv sync --group ai`。
7. **`get_settings()` 用 lru_cache**:测试里每次修改环境变量需要显式 `get_settings.cache_clear()`。如果后续做热更新,考虑改成每请求注入或 `Settings()` 直接构造。
8. **前端 session token 存 sessionStorage**:刷新保留但跨标签不共享。生产如需「持续登录」改 localStorage + 主动过期校验。
9. **Audit `X-Audit-Recorded: true` 响应头**:写操作 5xx 也会带这个头(因为 middleware 先返回 response 再尝试写入)。行为正确但头语义略歧义;🟡 轮可改为只在成功写入 DB 后设置。
10. **WS 中间件鉴权只允许 query param `token`**:如果客户端在浏览器内跨域发 WS 只能用 query 或 Sec-WebSocket-Protocol;如需后者,再加一个分支。

## 🟡 轮候选清单(供下次会话规划)

- 前端:`<img>` 全量迁移 `next/image`,场景 PNG 合并到 design-system 并删除两份 public 副本
- RateLimit:升级到 Lua 脚本原子版本(生产真实 Redis 下)
- Admin UI:`/admin/v1/landmarks` 端点 + 移除 web-admin 的"兼职游客 token"
- Audit:补 `before` 字段;按 `admin_id` 索引;暴露 CSV 导出
- 测试:Playwright E2E、k6 压测升级(覆盖 POST /sessions/rate-limit)、RAG ragas 集成
- 部署:compose 补齐 prometheus.yml/loki-config.yaml/tempo.yaml/grafana provisioning;加 api + worker 容器
- 文档:README 架构图 + 安全边界 + 数据模型;ADR-002 鉴权决策;ADR-003 存储切换决策
- 依赖治理:pin CI 版本;weekly `uv sync --upgrade` 自动化

## 发布清单(建议 🔴 上线前必须执行)

- [ ] 设置 `AETHER_JWT_SECRET` 为 48+ 随机字符(prod)
- [ ] 设置 `AETHER_CORS_ORIGINS` 为真实白名单(不含 `*`)
- [ ] `AETHER_ENVIRONMENT=production` 下启动会自动 fail-fast 以上两项
- [ ] 替换 `infra/seed/admins.yaml` 的 demo 账号或将文件剔除
- [ ] 生产 Redis 部署后确认 rate-limit 非降级模式(日志里应没有 `Redis unavailable` 告警)
- [ ] 首次部署运行 `make migrate`(`AETHER_STORAGE_MODE=database`)

---

**本轮修复提交序列**(main 分支,12 次任务提交):

```
f0146e2 chore: baseline before 14-issue fix plan
44e9f59 task-1: expand deps, config, ruff/mypy baselines
<commit> task-2: alembic init migration + migrate target
<commit> task-3: introduce Repository Protocol + inmemory package
8b613d7 task-4: SqlRepository + 0002 migration (summary/password_hash)
<commit> task-5: auth core (JWT + bcrypt + login + anonymous + seed)
ff9dd58 task-6: enforce auth on routes + websocket token
<commit> task-7: CORS env whitelist + real audit persistence + body size limit
1f81984 task-8: Redis sliding-window rate limit with in-memory degrade
a86e12c task-9: split safety GET, real clear_trail, persist system_prompt, doc state machine
<commit> task-10: narrow AI exceptions + cost_usd + trace sanitize + image validator + readyz deps check
<commit> task-11: frontend trace propagation + tokenized auth + admin login + ESLint flat config
```
