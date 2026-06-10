import pytest
from unittest.mock import patch, AsyncMock
from src.utils import ingest, llm, prompt


@pytest.mark.asyncio
async def test_check_repo_exists_success():
    mock_response = AsyncMock()
    mock_response.status = 200

    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await ingest.check_repo_exists(
            "https://github.com/HarishChandran3304/FCA"
        )
        assert result is True


@pytest.mark.asyncio
async def test_check_repo_exists_failure():
    mock_response = AsyncMock()
    mock_response.status = 404

    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await ingest.check_repo_exists("https://github.com/owner/repo")
        assert result is False


@pytest.mark.asyncio
async def test_check_repo_exists_invalid_url():
    with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Invalid URL")
        result = await ingest.check_repo_exists("not_a_url")
        assert result is False or result is None


@pytest.mark.asyncio
async def test_ingest_repo_not_found():
    with patch("src.utils.ingest.check_repo_exists", AsyncMock(return_value=False)):
        with pytest.raises(ValueError) as exc:
            await ingest.ingest_repo("https://github.com/owner/repo")
        assert str(exc.value) == "error:repo_not_found"


@pytest.mark.asyncio
async def test_ingest_repo_too_large():
    async def fake_ingest_async(repo_url, exclude_patterns=None):
        return ("Estimated tokens: 1M", "tree", "content")

    with (
        patch("src.utils.ingest.check_repo_exists", AsyncMock(return_value=True)),
        patch("gitingest.ingest_async", new=fake_ingest_async),
    ):
        with pytest.raises(ValueError) as exc:
            await ingest.ingest_repo("https://github.com/owner/repo")
        assert str(exc.value) == "error:repo_not_found"


@pytest.mark.asyncio
async def test_ingest_repo_network_error():
    with patch(
        "src.utils.ingest.check_repo_exists",
        AsyncMock(side_effect=Exception("Network error")),
    ):
        with pytest.raises(Exception) as exc:
            await ingest.ingest_repo("https://github.com/owner/repo")
        assert "Network error" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_prompt_basic():
    query = "What does this repo do?"
    history = [("User", "Hello"), ("Bot", "Hi!")]
    tree = "src/\n  main.py"
    content = "def foo(): pass"
    prompt_str = await prompt.generate_prompt(query, history, tree, content)
    assert "What does this repo do?" in prompt_str
    assert "src/" in prompt_str
    assert "def foo()" in prompt_str


@pytest.mark.asyncio
async def test_generate_prompt_empty_content():
    query = "Explain the repo."
    history = []
    tree = ""
    content = ""
    prompt_str = await prompt.generate_prompt(query, history, tree, content)
    assert query in prompt_str
    assert "File Content:" in prompt_str


@pytest.mark.asyncio
async def test_generate_response_success():
    class DummyClient:
        class aio:
            class models:
                @staticmethod
                async def generate_content(model, contents):
                    class Resp:
                        text = "response"

                    return Resp()

    with patch.object(llm.key_manager, "client", DummyClient()):
        resp = await llm.generate_response("prompt")
        assert resp == "response"


@pytest.mark.asyncio
async def test_generate_response_out_of_keys():
    class DummyClient:
        class aio:
            class models:
                @staticmethod
                async def generate_content(model, contents):
                    raise Exception("RESOURCE_EXHAUSTED")

    with patch.object(llm.key_manager, "client", DummyClient()):
        with patch.object(llm.key_manager, "get_next_key", return_value=None):
            with pytest.raises(ValueError) as exc:
                await llm.generate_response("prompt")
            assert "OUT_OF_KEYS" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_response_invalid_prompt():
    class DummyClient:
        class aio:
            class models:
                @staticmethod
                async def generate_content(model, contents):
                    raise Exception("INVALID_PROMPT")

    with patch.object(llm.key_manager, "client", DummyClient()):
        with pytest.raises(Exception) as exc:
            await llm.generate_response("")
        assert "INVALID_PROMPT" in str(exc.value)
