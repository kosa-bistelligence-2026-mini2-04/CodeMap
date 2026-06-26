import asyncio
import os
import sys

# Ensure backend directory is in the sys path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.repo.service import analyze_repository

async def main():
    repo_url = "https://github.com/kosa-bistelligence-2026-mini2-04/CodeMap"
    owner = "kosa-bistelligence-2026-mini2-04"
    repo_name = "CodeMap"
    print("Starting analysis...")
    # I don't know the exact arguments for analyze_repository. I will check first.
