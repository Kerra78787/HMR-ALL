
import os
import re
import json
import base64
import shutil
import tempfile
import requests

from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit, unquote
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


SOURCES = {
    "01-MustafaBaqer": ("MustafaBaqer/VestraNet-Nodes", "protocols"),
    "02-aviamastersgh": ("aviamastersgh/vpn-free-russia", ""),
    "03-R3ZARAHIMI": ("R3ZARAHIMI/tg-v2ray-configs-every2h", ""),
    "04-ALIILAPRO": ("ALIILAPRO/v2rayNG-Config", ""),
    "05-ermaozi": ("ermaozi/get_subscribe", "subscribe"),
    "06-FlareFeed": ("svinakraft-maker/FlareFeed", "public"),
    "07-alireza786786": ("alireza786786/Free-V2ray-Configs", "servers"),
    "08-daily_free_vpn": ("cbusifabcap/daily_free_vpn", ""),
    "09-0xRadikal": ("0xRadikal/Free-v2ray-Configs", "protocols"),
    "10-histeenn": ("histeenn/VLESS-PO-GRIBI", "deploy"),
    "11-igareck": ("igareck/vpn-configs-for-russia", ""),
    "12-mrdevmohamed": ("mrdevmohamed/v2ray-configs", ""),
}

ROOT = Path("Sources")
MANIFEST = ".mirror-manifest.txt"

URI_PATTERN = re.compile(
    r"(?:vless|vmess|trojan)://[^\s<>'\"`]+",
    re.IGNORECASE
)


def make_session():
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = "HMR-ALL-Updater/6.0"

    token = os.getenv("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    return session


def get_json(session, url):
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return response.json()


def safe_relative(path):
    parsed = PurePosixPath(path)
    if (
        not path
        or parsed.is_absolute()
        or "\\" in path
        or any(part in ("", ".", "..") for part in parsed.parts)
    ):
        raise RuntimeError(f"Unsafe path: {path}")
    return Path(*parsed.parts)


def read_manifest(destination):
    manifest = destination / MANIFEST
    old_files = set()
    old_prefix = None

    if manifest.is_file():
        for line in manifest.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            line = line.strip()
            if line.startswith("# prefix="):
                old_prefix = line.split("=", 1)[1]
            elif line and not line.startswith("#"):
                old_files.add(line)

    return old_prefix, old_files


def valid_config(uri):
    try:
        scheme, payload = uri.split("://", 1)
        scheme = scheme.lower()

        if not payload or "..." in payload or "×" in payload:
            return False

        if scheme == "vmess":
            padded = payload + "=" * (-len(payload) % 4)
            raw = base64.urlsafe_b64decode(padded)
            data = json.loads(raw.decode("utf-8-sig"))

            host = str(data.get("add", "")).strip()
            port = int(data.get("port", 0))
            user_id = str(data.get("id", "")).strip()

            if not host or not 1 <= port <= 65535:
                return False

            if not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id):
                return False

            return True

        if scheme in ("vless", "trojan"):
            parsed = urlsplit(uri)

            if not parsed.hostname or parsed.port is None:
                return False

            if not 1 <= parsed.port <= 65535:
                return False

            user = unquote(parsed.username or "")
            if not user:
                return False

            if scheme == "vless":
                return bool(re.fullmatch(
                    r"[0-9a-fA-F]{8}-"
                    r"[0-9a-fA-F]{4}-"
                    r"[0-9a-fA-F]{4}-"
                    r"[0-9a-fA-F]{4}-"
                    r"[0-9a-fA-F]{12}",
                    user
                ))

            return len(user) >= 4

        return False

    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError):
        return False


def extract_configs(content):
    text = content.decode("utf-8-sig", errors="replace")
    found = []
    seen = set()

    def collect(value):
        for match in URI_PATTERN.findall(value):
            uri = match.rstrip(".,;)]}")
            if uri not in seen and valid_config(uri):
                seen.add(uri)
                found.append(uri)

    collect(text)

    # Base64 subscription support
    compact = "".join(text.split())

    if len(compact) >= 16 and re.fullmatch(
        r"[A-Za-z0-9_+/=-]+", compact
    ):
        try:
            padded = compact + "=" * (-len(compact) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            collect(decoded.decode("utf-8-sig", errors="ignore"))
        except (ValueError, UnicodeError):
            pass

    # Also check individual Base64 lines
    for line in text.splitlines():
        compact_line = "".join(line.split())

        if len(compact_line) < 16:
            continue

        if not re.fullmatch(r"[A-Za-z0-9_+/=-]+", compact_line):
            continue

        try:
            padded = compact_line + "=" * (-len(compact_line) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            collect(decoded.decode("utf-8-sig", errors="ignore"))
        except (ValueError, UnicodeError):
            continue

    return found


def get_txt_paths(tree, prefix):
    result = []

    for item in tree:
        if item.get("type") != "blob":
            continue

        path = item["path"]

        if not path.lower().endswith(".txt"):
            continue

        if prefix and not path.startswith(prefix + "/"):
            continue

        relative = path[len(prefix) + 1:] if prefix else path

        try:
            safe_relative(relative)
        except RuntimeError:
            continue

        result.append((path, relative))

    return result


def resolve_folder(tree, configured, old_files):
    paths = {
        item["path"]
        for item in tree
        if item.get("type") in ("tree", "blob")
    }

    if not configured:
        return ""

    if configured in paths or any(
        p.startswith(configured + "/") for p in paths
    ):
        return configured

    candidates = {
        item["path"]
        for item in tree
        if item.get("type") == "tree"
    }

    scores = {}

    for candidate in candidates:
        current = {
            relative
            for _, relative in get_txt_paths(tree, candidate)
        }
        overlap = len(current & old_files)

        if overlap:
            scores[candidate] = overlap

    if not scores:
        raise RuntimeError(
            f"Cannot safely identify renamed folder: {configured}"
        )

    best = max(scores.values())
    winners = [p for p, score in scores.items() if score == best]

    if len(winners) != 1:
        raise RuntimeError(
            f"Ambiguous renamed folder: {winners}"
        )

    print(f"Folder renamed: {configured} -> {winners[0]}")
    return winners[0]


def download_file(session, repo, branch, path):
    url = (
        f"https://raw.githubusercontent.com/{repo}/"
        f"{quote(branch, safe='')}/{quote(path, safe='/')}"
    )
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def replace_directory(stage, destination):
    backup = ROOT / f".{destination.name}.backup"

    if backup.exists():
        shutil.rmtree(backup)

    had_old = destination.exists()

    try:
        if had_old:
            destination.rename(backup)

        stage.rename(destination)

    except Exception:
        if destination.exists():
            shutil.rmtree(destination)

        if had_old and backup.exists():
            backup.rename(destination)

        raise

    if backup.exists():
        shutil.rmtree(backup)


def refresh(name, repo, configured_folder):
    session = make_session()
    destination = ROOT / name
    _, old_files = read_manifest(destination)

    api = f"https://api.github.com/repos/{repo}"
    info = get_json(session, api)
    branch = info["default_branch"]

    tree_url = (
        f"{api}/git/trees/{quote(branch, safe='')}?recursive=1"
    )
    tree_data = get_json(session, tree_url)

    if tree_data.get("truncated"):
        raise RuntimeError("GitHub tree truncated; old files preserved")

    tree = tree_data["tree"]
    folder = resolve_folder(tree, configured_folder, old_files)
    source_files = get_txt_paths(tree, folder)

    if not source_files:
        raise RuntimeError("No TXT files found; old files preserved")

    new_files = {}

    for remote_path, relative_path in source_files:
        content = download_file(session, repo, branch, remote_path)
        configs = extract_configs(content)

        if configs:
            new_files[relative_path] = (
                "\n".join(configs) + "\n"
            ).encode("utf-8")

    if not new_files:
        raise RuntimeError(
            "No valid VLESS/VMess/Trojan configs; old files preserved"
        )

    stage = Path(tempfile.mkdtemp(prefix=".hmr-", dir=ROOT))

    try:
        for relative, content in new_files.items():
            target = stage / safe_relative(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        lines = [
            "# HMR-ALL manifest v3",
            f"# source={repo}",
            f"# prefix={folder}",
            *sorted(new_files),
        ]

        (stage / MANIFEST).write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8"
        )

        replace_directory(stage, destination)

    finally:
        if stage.exists():
            shutil.rmtree(stage)

    count = sum(len(v.decode("utf-8").splitlines()) for v in new_files.values())
    print(f"OK: {name}: {len(new_files)} TXT files, {count} configs")


def main():
    ROOT.mkdir(exist_ok=True)
    errors = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = {
            executor.submit(refresh, name, repo, folder): name
            for name, (repo, folder) in SOURCES.items()
        }

        for job in as_completed(jobs):
            name = jobs[job]
            try:
                job.result()
            except Exception as error:
                errors.append(name)
                print(f"ERROR: {name}: {error}")

    print(f"\nSources: {len(SOURCES)}")
    print(f"Errors: {len(errors)}")

    if errors:
        raise SystemExit(
            "Some sources failed. Their old mirrored data was preserved."
        )

    print("All 12 sources synchronized successfully!")


if __name__ == "__main__":
    main()
        
