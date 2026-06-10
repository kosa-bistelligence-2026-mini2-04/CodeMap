# 测试仓库清单（多技术栈覆盖）

## 用户自有仓库
- `https://github.com/CronusL-1141/AI-company` — 大型多Agent项目（public）

## 公开测试仓库（不同技术栈/规模）
- `https://github.com/encode/httpx` — 异步HTTP客户端（中等规模，高质量）
- `https://github.com/tiangolo/fastapi` — Web框架（大规模，活跃社区）
- `https://github.com/psf/requests` — 经典HTTP库（成熟项目）
- `https://github.com/pallets/flask` — 微框架（成熟+稳定）
- `https://github.com/python-poetry/poetry` — 工具类（包管理）
- `https://github.com/kennethreitz/records` — 小项目（SQL记录库）

## 验收用例
| 用例 | 仓库 | 目的 |
|---|---|---|
| U1 | httpx | 标准异步库，验证完整流程 |
| U2 | records | 小项目，验证最小可运行路径 |
| U3 | fastapi | 大项目，验证超时降级机制 |
| U4 | AI-company | 用户项目，验证端到端 |
