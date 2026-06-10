# Contributing to TalkToGitHub

Thanks for your interest in contributing to TalkToGitHub! 🚀 TalkToGitHub aims to be friendly for first time contributors, with a simple Python and HTML codebase. We would love your help to make it even better. If you need any help while working with the code, please reach out to us on [Discord](https://discord.com/invite/JKtHeSn4S7).

## How to Contribute (non-technical)

- **Create an Issue**: If you find a bug or have an idea for a new feature, please [create an issue](https://github.com/HarishChandran3304/TTG/issues/new) on GitHub. This will help us track and prioritize your request.
- **Spread the Word**: If you like TalkToGitHub, please share it with your friends, colleagues, and on social media. This will help us grow the community and make TalkToGitHub even better.
- **Use TalkToGitHub**: The best feedback comes from real-world usage! If you encounter any issues or have ideas for improvement, please let us know by [creating an issue](https://github.com/HarishChandran3304/TTG/issues/new) on GitHub or by reaching out to us on [Discord](https://discord.com/invite/JKtHeSn4S7).

## How to submit a Pull Request

Prerequisites:
- [Python 3.13+](https://www.python.org/downloads/release/python-3130/)
- [uv](https://docs.astral.sh/uv/)
- [node 23.6.0+](https://nodejs.org/en/download)

1. Fork the repository.

2. Clone the forked repository:
  ```bash
  git clone https://github.com/HarishChandran3304/TTG.git
  cd TTG
  ```

3. Install backend dependencies:
  ```bash
  uv sync
  source ./.venv/bin/activate
  ```

4. Add the following to your `.env` file:
  ```bash
  GEMINI_API_KEY=<your-gemini-api-key>
  GEMINI_MODEL=gemini-2.0-flash
  ENV=development
  FALLBACK_COUNT=0
  ```

5. Install frontend dependencies:
  ```bash
  cd frontend
  npm install
  ```

6. Create a new branch for your changes:
  ```bash
  git checkout -b <your-branch>
  ```

7. Make your changes

8. Make sure to add relevant tests for your changes if applicable.

9. Run the local web server
  ```bash
  fastapi dev src/main.py
  ```

10. Run the frontend server
  ```bash
  npm run dev
  ```

11. Open the frontend at localhost:5173 and confirm that everything is working as expected.

12. Run tests:
  ```bash
  pytest
  ```

13. Run backend checks:
  ```bash
  ruff check .
  ruf format .
  mypy .
  ```

14. Run frontend checks:
  ```bash
  npm run lint
  ```

15. Stage your changes:
  ```bash
  git add .
  ```

16. Commit your changes:
  ```bash
  git commit -m "<Your commit message>"
  ```

17. Push your changes:
  ```bash
  git push origin your-branch
  ```

18. Open a pull request on GitHub. Make sure to include a detailed description of your changes.

19. Wait for the maintainers to review your pull request. 

20. Once your pull request is approved, it will be merged into the main branch. Thank you for your contribution!