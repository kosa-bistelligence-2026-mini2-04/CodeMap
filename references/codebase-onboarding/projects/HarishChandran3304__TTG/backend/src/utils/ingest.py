from gitingest import ingest_async  # type: ignore
import aiohttp


async def check_repo_exists(repo_url: str) -> bool:
    """Check if a repository exists and is accessible."""
    api_url = repo_url.replace("github.com", "api.github.com/repos")
    async with aiohttp.ClientSession() as session:
        try:
            response = await session.get(api_url)
            return response.status == 200
        except Exception:
            return False


async def ingest_repo(repo_url: str) -> tuple[str, str, str]:
    """
    Converts a github repository into LLM-friendly format.

    Args:
            repo_url: The URL of the repository to ingest.

    Returns:
            A tuple containing the summary, the folder structure, and the content of the files in LLM-friendly format.
    """
    # Check if repository exists and is accessible
    if not await check_repo_exists(repo_url):
        raise ValueError("error:repo_not_found")

    try:
        summary, tree, content = await ingest_async(
            repo_url, exclude_patterns={"tests/*", "docs/*"}
        )

        # Check if token count exceeds limit
        if "Estimated tokens: " in summary:
            tokens_str = summary.split("Estimated tokens: ")[-1].strip()
            if tokens_str.endswith("M"):
                raise ValueError("error:repo_too_large")
            elif tokens_str.endswith("K"):
                tokens = float(tokens_str[:-1])
                if tokens > 750:
                    raise ValueError("error:repo_too_large")

        return summary, tree, content
    except Exception as e:
        if "Repository not found" in str(e) or "Not Found" in str(e):
            raise ValueError("error:repo_not_found")
        if "Bad credentials" in str(e) or "API rate limit exceeded" in str(e):
            raise ValueError("error:repo_private")
        raise


if __name__ == "__main__":
    import asyncio

    # summary, tree, content = asyncio.run(
    #     ingest_repo("https://github.com/HarishChandran3304/FCA")
    # )
    # print(summary)
    # print(tree)
    # print(content)

    print(asyncio.run(check_repo_exists("https://github.com/HarishChandran3304/FCA")))
