# samples/

这个目录通过 `docker-compose.yml` 被挂载到 backend 容器的 `/workspace`（只读）。

## 两种分析仓库的方式

### ① GitHub URL 模式（推荐，零配置）

直接在前端粘贴 GitHub URL，例如：

```
https://github.com/pallets/flask
https://github.com/kennethreitz/records
https://github.com/encode/httpx
```

Backend 会在容器内 `git clone` 到原生 ext4，没有任何文件系统瓶颈，三端（Linux/macOS/Windows）性能一致。**推荐所有评审使用这种方式**。

### ② 本地路径模式

把待分析的 Python 仓库放到这个 `samples/` 目录下，例如：

```
samples/
├── README.md          ← 本文件
├── test-repos.md      ← 参考测试仓库清单
├── flask/             ← 你自己 clone 的
└── my-project/
```

然后在前端选"本地路径"标签页，填入 `/workspace/flask` 或 `/workspace/my-project`。

如需把其它位置的仓库挂进来（而不是复制到 `samples/`），设置环境变量再重启即可：

```bash
# Linux/macOS
HOST_REPOS_DIR=/home/me/code docker compose up -d

# Windows PowerShell
$env:HOST_REPOS_DIR = "D:/code"; docker compose up -d
```

## 性能提示

Windows Docker Desktop 用户在大仓库（>200 py 文件）上可能比 Linux 慢 30-50%，但不会降级 —— 详见根目录 `README.md` 的"环境与性能"章节。若追求最快体验，用 GitHub URL 模式绕过所有 bind mount 开销。

## 参考仓库清单

见 `test-repos.md`，列出了若干不同规模与技术栈的公开 Python 仓库，覆盖小/中/大、同步/异步、框架/工具/库。
