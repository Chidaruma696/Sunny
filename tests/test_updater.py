import hashlib

from sunny.updater import is_newer, parse_version, release_from_json, verify_sha256


def test_versions_compare_as_numbers():
    assert parse_version("v0.2.1") == (0, 2, 1) and parse_version("1.10") == (1, 10)
    assert is_newer("v0.3.0", "0.2.1") and is_newer("v1.0.0", "0.10.9")
    assert not is_newer("v0.2.1", "0.2.1") and not is_newer("v0.2.0", "0.2.1")
    assert not is_newer("garbage", "0.2.1")


def test_release_from_github_json_takes_installer_and_sha():
    data = {
        "tag_name": "v0.3.0", "html_url": "https://github.com/Chidaruma696/Sunny/releases/tag/v0.3.0", "body": "notes",
        "assets": [
            {"name": "Sunny-0.3.0-setup.exe", "browser_download_url": "https://github.com/Chidaruma696/Sunny/releases/download/v0.3.0/Sunny-0.3.0-setup.exe"},
            {"name": "Sunny-0.3.0-setup.exe.sha256", "browser_download_url": "https://github.com/Chidaruma696/Sunny/releases/download/v0.3.0/Sunny-0.3.0-setup.exe.sha256"},
            {"name": "evil.exe", "browser_download_url": "http://example.com/evil.exe"},
        ],
    }
    r = release_from_json(data)
    assert r.version == "0.3.0" and r.installer_name == "Sunny-0.3.0-setup.exe" and r.sha256_url.endswith(".sha256")
    assert release_from_json({"tag_name": "v9", "assets": []}) is None
    assert release_from_json({"tag_name": "v9", "assets": [{"name": "Sunny-9-setup.exe", "browser_download_url": "http://evil/x-setup.exe"}]}) is None


def test_sha256_verification(tmp_path):
    f = tmp_path / "x.exe"
    f.write_bytes(b"hello")
    digest = hashlib.sha256(b"hello").hexdigest()
    assert verify_sha256(f, f"{digest} *Sunny-0.3.0-setup.exe\n")
    assert verify_sha256(f, digest.upper())
    assert not verify_sha256(f, "0" * 64) and not verify_sha256(f, "not a hash")
