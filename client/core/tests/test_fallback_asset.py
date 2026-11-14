import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "fallback_asset", Path(__file__).resolve().parents[3] / "scripts/fallback_asset.py"
)

asset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset)


class FallbackAssetTests(unittest.TestCase):
    def test_verified_download_is_cached(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fallback.zip"
            payload = b"downloaded animation"
            path.with_suffix(".json").write_text(json.dumps({
                "url": "https://example.test/fallback.zip",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }))

            with patch.object(asset, "ASSET", path), patch.object(asset, "urlopen", return_value=io.BytesIO(payload)) as fetch:
                asset.download()
                asset.download()

            self.assertEqual(path.read_bytes(), payload)
            fetch.assert_called_once_with("https://example.test/fallback.zip", timeout=60)

    def test_checksum_failure_preserves_existing_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fallback.zip"
            path.write_bytes(b"old animation")
            path.with_suffix(".json").write_text(json.dumps({
                "url": "https://example.test/fallback.zip",
                "sha256": hashlib.sha256(b"expected animation").hexdigest(),
            }))

            with patch.object(asset, "ASSET", path), patch.object(asset, "urlopen", return_value=io.BytesIO(b"corrupt")):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    asset.download()

            self.assertEqual(path.read_bytes(), b"old animation")
