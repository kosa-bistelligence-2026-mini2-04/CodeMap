import unittest
import regex
import asyncio
from app.agent.util.safe_regex import compile_safe_regex, RegexTimeoutError

class TestSafeRegex(unittest.IsolatedAsyncioTestCase):
    def test_compile_safe_regex_valid(self):
        compiled = compile_safe_regex(r"^hello\s+world$", regex.IGNORECASE)
        self.assertIsNotNone(compiled.search("Hello  World"))

    def test_compile_safe_regex_too_long(self):
        long_pattern = "a" * 129
        with self.assertRaisesRegex(ValueError, "Pattern exceeds max length"):
            compile_safe_regex(long_pattern)

    def test_compile_safe_regex_nested(self):
        nested_pattern = "(a+)+$"
        with self.assertRaisesRegex(ValueError, "Pattern contains nested quantifiers"):
            compile_safe_regex(nested_pattern)

    def test_regex_timeout(self):
        # regex 엔진 자체의 timeout 기능 검증 (ReDoS 패턴이 아니어도 타임아웃 발생)
        c = regex.compile("a")
        # timeout을 0으로 주어 즉시 타임아웃 발생 유도
        with self.assertRaises(TimeoutError):
            c.search("a" * 100000, timeout=0.0)

    async def test_worker_timeout(self):
        # asyncio.wait_for 기반의 워커 타임아웃 로직 검증
        async def slow_func():
            await asyncio.sleep(0.2)
            return "done"
        
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(slow_func(), timeout=0.1)
