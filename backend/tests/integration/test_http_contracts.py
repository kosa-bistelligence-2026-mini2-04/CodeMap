import re
import unittest
from pathlib import Path


HTTP_ROOT = Path(__file__).resolve().parents[1] / "http"
REQUEST_RE = re.compile(r"^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|WEBSOCKET)\s+\S+", re.MULTILINE)
TOKEN_RE = re.compile(r"^@(?:accessToken|serviceToken)\s*=\s*(.+)$", re.MULTILINE | re.IGNORECASE)
API_ID_PATTERN = r"[A-Z]+(?:-[A-Z]+)*-API-[0-9]{3}"
PRIMARY_API_ID_RE = re.compile(
    rf"^(?:###|#)\s*(?:API ID\s*:\s*)?({API_ID_PATTERN})(?:\s*\||\s*$)",
    re.MULTILINE,
)


class HttpContractInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(HTTP_ROOT.rglob("*.http"))

    def test_contract_inventory_is_not_empty(self):
        self.assertTrue(self.files)

    def test_every_file_has_an_executable_request(self):
        missing = [str(path.relative_to(HTTP_ROOT)) for path in self.files if not REQUEST_RE.search(path.read_text(encoding="utf-8"))]
        self.assertEqual(missing, [])

    def test_auth_values_are_safe_placeholders(self):
        unsafe = []
        for path in self.files:
            for value in TOKEN_RE.findall(path.read_text(encoding="utf-8")):
                if not value.strip().startswith("replace-me"):
                    unsafe.append(str(path.relative_to(HTTP_ROOT)))
        self.assertEqual(unsafe, [])

    def test_api_ids_are_not_duplicated_between_files(self):
        owners = {}
        duplicates = {}
        for path in self.files:
            match = PRIMARY_API_ID_RE.search(path.read_text(encoding="utf-8"))
            self.assertIsNotNone(match, str(path.relative_to(HTTP_ROOT)))
            api_id = match.group(1)
            if api_id in owners and owners[api_id] != path:
                duplicates.setdefault(api_id, {owners[api_id]}).add(path)
            owners[api_id] = path
        self.assertEqual({key: sorted(map(str, value)) for key, value in duplicates.items()}, {})
