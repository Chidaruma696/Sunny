"""Updates from GitHub releases, with nothing but the standard library.

On start the window asks GitHub for the latest release of the repository. If its tag is newer
than this version, the user is offered the update: the installer is downloaded to a temp folder,
its SHA-256 is checked against the `.sha256` file published next to it, and it is run silently
with /RELAUNCH so Sunny opens again when it finishes. Nothing is ever installed without the user
pressing the button.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import APP_NAME, REPO_URL, __version__

API_LATEST = REPO_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
TIMEOUT = 10
USER_AGENT = f"{APP_NAME}/{__version__}"
ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")


class UpdateError(RuntimeError):
    """Could not check, download or verify an update."""


@dataclass
class Release:
    version: str
    tag: str
    page: str
    installer_url: str
    installer_name: str
    sha256_url: str | None
    notes: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    """"v0.2.1" / "0.2.1" → (0, 2, 1); anything unparsable is (0,)."""
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    if not m:
        return (0,)
    return tuple(int(g) for g in m.groups() if g is not None)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def release_from_json(data: dict) -> Release | None:
    """The Release described by GitHub's /releases/latest JSON, or None if it has no installer."""
    tag = str(data.get("tag_name") or "")
    installer = sha = None
    for asset in data.get("assets") or []:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if not url.startswith("https://") or not any(h in url for h in ALLOWED_HOSTS):
            continue
        if name.lower().endswith("-setup.exe"):
            installer = (name, url)
        elif name.lower().endswith("-setup.exe.sha256"):
            sha = url
    if not installer:
        return None
    return Release(version=".".join(str(n) for n in parse_version(tag)), tag=tag,
                   page=str(data.get("html_url") or REPO_URL + "/releases/latest"),
                   installer_name=installer[0], installer_url=installer[1], sha256_url=sha,
                   notes=str(data.get("body") or ""))


def _get(url: str, binary: bool = False, progress: Callable[[int, int], None] | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream" if binary else "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 - https URLs on GitHub only
            total = int(resp.headers.get("Content-Length") or 0)
            chunks = []
            done = 0
            while True:
                chunk = resp.read(256 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
            return b"".join(chunks)
    except urllib.error.HTTPError as e:
        raise UpdateError(f"GitHub contestó {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError("sin conexión con GitHub") from e


def check() -> Release | None:
    """The latest release if it is newer than this version, else None. Raises UpdateError."""
    try:
        data = json.loads(_get(API_LATEST).decode("utf-8"))
    except ValueError as e:
        raise UpdateError("respuesta rara de GitHub") from e
    release = release_from_json(data)
    if release and is_newer(release.tag):
        return release
    return None


def verify_sha256(path: Path, expected_text: str) -> bool:
    """EXPECTED_TEXT is the content of a .sha256 file: the hex digest, optionally followed by the name."""
    m = re.search(r"\b([0-9a-fA-F]{64})\b", expected_text)
    if not m:
        return False
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest.lower() == m.group(1).lower()


def download(release: Release, progress: Callable[[int, int], None] | None = None) -> Path:
    """The installer in a temp folder, verified against its .sha256 when the release has one."""
    folder = Path(tempfile.mkdtemp(prefix="sunny-update-"))
    target = folder / release.installer_name
    target.write_bytes(_get(release.installer_url, binary=True, progress=progress))
    if target.stat().st_size < 1_000_000:
        raise UpdateError("el instalador bajado está incompleto")
    if release.sha256_url:
        expected = _get(release.sha256_url).decode("utf-8", errors="replace")
        if not verify_sha256(target, expected):
            target.unlink(missing_ok=True)
            raise UpdateError("la huella SHA-256 del instalador no coincide; no se instala")
    return target


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install(installer: Path) -> None:
    """Run the installer silently; it relaunches Sunny at the end (see installer/Sunny.iss).
    The caller must quit right after, so the installer can replace the files."""
    subprocess.Popen([str(installer), "/SILENT", "/SP-", "/SUPPRESSMSGBOXES", "/NORESTART", "/RELAUNCH"],  # noqa: S603
                     close_fds=True, creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
