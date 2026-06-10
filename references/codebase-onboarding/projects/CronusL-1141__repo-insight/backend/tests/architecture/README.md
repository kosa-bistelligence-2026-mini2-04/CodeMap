# Architecture Boundary Tests

本目录承载 RepoInsight 的**架构边界双层防御**测试，配合仓库根 CI 的 Gate C 使用。

## 为什么需要"静态 + 运行期"双层

### 静态层：`backend/.importlinter`

`import-linter` 在解析阶段通过 AST 静态分析 `import` / `from ... import ...` 语句，构建模块依赖图，验证是否违反 `layered` 与 `forbidden` 契约。对 RepoInsight 的分层（`api > orchestrator > agents > (llm|guardrail|services) > models`）以及 `BehaviorInferer -> Guardrail` 禁令提供第一道防线。

### 运行期层：`test_import_boundaries.py`

PATCH-PLAN R2 backend 真实多 Agent 推理中，`backend-arch-13` 明确击穿了静态 AST 的盲区：

> `importlib.import_module('app.guardrail.validator')`、`getattr(sys.modules, ...)`、`__import__(...)` 等**反射导入**绕过 AST 静态扫描，import-linter 无法识别，`BehaviorInferer` 仍可通过动态路径注入 `Guardrail` 模块，违背"Guardrail 必须经 Planner 编织"的架构约束。

运行期断言的思路：

1. 清理 `sys.modules` 中所有已加载的 `app.guardrail.*` 模块（避免测试顺序污染）
2. 干净地 `importlib.import_module('app.agents.behavior_inferer')`
3. 断言加载后 `sys.modules` 不含任何 `app.guardrail.*` 键

如果 `behavior_inferer` 中存在任何形式的 guardrail 反射调用（即使是条件执行路径或延迟导入），加载时就会把对应模块拉入 `sys.modules`，断言立刻失败。

### 双层组合的覆盖矩阵

| 违规形式 | 静态 import-linter | 运行期 sys.modules 断言 |
|---|---|---|
| `from app.guardrail import X` | 拦截 | 拦截 |
| `import app.guardrail.validator` | 拦截 | 拦截 |
| `importlib.import_module("app.guardrail.validator")` | 漏过 | 拦截 |
| `__import__("app.guardrail")` | 漏过 | 拦截 |
| `getattr(sys.modules, "app.guardrail")` 访问已加载模块 | 漏过 | 拦截 |

两层结合覆盖了 AST 静态与运行时反射两类违规路径。CI `Gate C` 任一红则阻断 PR。

## 扩展

未来新增的架构契约：

- 新增跨层禁令：先写 `.importlinter` 契约，再在本目录补对应反射场景的 pytest
- 新增模块层级：修改 `.importlinter` 的 `layers` 顺序，运行期测试无需改动
