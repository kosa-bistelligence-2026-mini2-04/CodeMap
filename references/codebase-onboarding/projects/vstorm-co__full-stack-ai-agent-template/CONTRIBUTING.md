# Contributing

Thank you for your interest in contributing to Full-Stack AI Agent Template!

## Developer Certificate of Origin (DCO)

This project uses a [Developer Certificate of Origin (DCO)](DCO) to ensure that contributors have the right to submit their contributions.

By submitting a contribution, you agree to the terms of the DCO. You must sign off on every commit:

```bash
git commit -s -m "Your commit message"
```

This adds a `Signed-off-by` line to your commit message:

```
Signed-off-by: Your Name <your@email.com>
```

If you forget, you can amend your last commit:

```bash
git commit --amend -s
```

## How to Contribute

1. **Fork** the repository
2. **Create a branch** for your feature or fix
3. **Make your changes** following the project conventions
4. **Run tests** to ensure nothing is broken:
   ```bash
   uv run pytest
   uv run ruff check . --fix
   uv run ruff format .
   uv run ty check
   ```
5. **Commit** with sign-off (`git commit -s`)
6. **Open a Pull Request** against `main`

## Development Setup

```bash
git clone https://github.com/vstorm-co/full-stack-ai-agent-template.git
cd full-stack-ai-agent-template
uv sync
```

## Reporting Issues

Use [GitHub Issues](https://github.com/vstorm-co/full-stack-ai-agent-template/issues) to report bugs or request features.

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
