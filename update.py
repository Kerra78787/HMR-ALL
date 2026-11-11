import os
import re
import base64
import shutil
import tempfile
import requests

from pathlib import Path, PurePosixPath
from urllib.parse import quote
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
ROOT.mkdir(exist_ok=True)

MANIFEST = ".mirror-manifest.txt"

URI_PATTERN = re.compile(
    r"""(?:vless|vmess|trojan)://[^\s<>"']+""",
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
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)

    session.headers["User-Agent"] = "HMR-ALL-Updater/5.0"

    token = os.getenv("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    return session


def get_json(session, url):
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return response.json()


def safe_relative(path):
    if not path or "\\" in path:
        raise RuntimeError(f"Invalid path: {path}")

    parsed = PurePosixPath(path)

    if parsed.is_absolute() or any(
        part in ("", ".", "..") for part in parsed.parts
    ):
        raise RuntimeError(f"Unsafe path: {path}")

    return Path(*parsed.parts)


def read_manifest(destination):
    manifest = destination / MANIFEST

    old_files = set()
    old_prefix = None

    if not manifest.is_file():
        return old_prefix, old_files

    for line in manifest.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines():

        line = line.strip()

        if line.startswith("# prefix="):
            old_prefix = line.split("=", 1)[1]

        elif line and not line.startswith("#"):
            old_files.add(line)

    return old_prefix, old_files


def extract_configs(content):
    text = content.decode("utf-8-sig", errors="replace")
    found = []
    seen = set()

    def collect(value):
        for match in URI_PATTERN.findall(value):
            uri = match.rstrip(".,;)]}")

            if uri and uri not in seen:
                seen.add(uri)
                found.append(uri)

    # First: ordinary text files.
    collect(text)

    # Also inspect Base64 subscription content.
    candidates = [text]
    candidates.extend(text.splitlines())

    for candidate in candidates:
        compact = "".join(candidate.split())

        if len(compact) < 16:
            continue

        if not re.fullmatch(r"[A-Za-z0-9_+/=-]+", compact):
            continue

        try:
            padded = compact + "=" * (-len(compact) % 4)
            decoded = base64.urlsafe_b64decode(padded)
            decoded_text = decoded.decode(
                "utf-8-sig",
                errors="ignore"
            )

            collect(decoded_text)

        except Exception:
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
    tree_paths = {
        item["path"]
        for item in tree
        if item.get("type") in ("tree", "blob")
    }

    if not configured:
        return ""

    if configured in tree_paths or any(
        path.startswith(configured + "/")
        for path in tree_paths
    ):
        return configured

    # The configured folder disappeared.
    # Find a replacement only when old relative paths match uniquely.
    if not old_files:
        raise RuntimeError(
            f"Folder '{configured}' missing; "
            "no old manifest available for safe detection."
        )

    candidates = set()

    for item in tree:
        if item.get("type") != "tree":
            continue

        candidates.add(item["path"])

    scores = {}

    for candidate in candidates:
        candidate_files = {
            relative
            for _, relative in get_txt_paths(tree, candidate)
        }

        overlap = len(candidate_files & old_files)

        if overlap:
            scores[candidate] = overlap

    if not scores:
        raise RuntimeError(
            f"Could not safely identify renamed folder '{configured}'. "
            "Old files preserved."
        )

    highest = max(scores.values())
    winners = [
        folder for folder, score in scores.items()
        if score == highest
    ]

    if len(winners) != 1:
        raise RuntimeError(
            f"Folder rename is ambiguous: {winners}. "
            "Old files preserved."
        )

    new_folder = winners[0]

    print(
        f"FOLDER RENAME: {configured} -> {new_folder}"
    )

    return new_folder


def download_source(session, repo, branch, path):
    encoded_path = quote(path, safe="/")
    encoded_branch = quote(branch, safe="")

    url = (
        "https://raw.githubusercontent.com/"
        f"{repo}/{encoded_branch}/{encoded_path}"
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

    old_prefix, old_files = read_manifest(destination)

    api = f"https://api.github.com/repos/{repo}"

    info = get_json(session, api)
    branch = info["default_branch"]

    tree_url = (
        f"{api}/git/trees/"
        f"{quote(branch, safe='')}?recursive=1"
    )

    tree_data = get_json(session, tree_url)

    if tree_data.get("truncated"):
        raise RuntimeError(
            "GitHub tree is incomplete. Old files preserved."
        )

    tree = tree_data["tree"]

    folder = resolve_folder(
        tree,
        configured_folder,
        old_files
    )

    source_files = get_txt_paths(tree, folder)

    if not source_files:
        raise RuntimeError(
            "No TXT files found. Old files preserved."
        )

    # Download and filter everything before changing the mirror.
    new_files = {}

    for remote_path, relative_path in source_files:
        content = download_source(
            session,
            repo,
            branch,
            remote_path
        )

        configs = extract_configs(content)

        if not configs:
            continue

        new_files[relative_path] = (
            "\n".join(configs) + "\n"
        ).encode("utf-8")

    if not new_files:
        raise RuntimeError(
            "No VLESS, VMess or Trojan configs found. "
            "Old files preserved."
        )

    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{name}.tmp-",
            dir=ROOT
        )
    )

    try:
        for relative, content in new_files.items():
            target = stage / safe_relative(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        manifest_lines = [
            "# HMR-ALL mirror manifest v2",
            f"# source={repo}",
            f"# prefix={folder}",
        ]

        manifest_lines.extend(sorted(new_files))

        (stage / MANIFEST).write_text(
            "\n".join(manifest_lines) + "\n",
            encoding="utf-8"
        )

        replace_directory(stage, destination)

    finally:
        if stage.exists():
            shutil.rmtree(stage)

    print(
        f"OK: {name} — "
        f"{len(new_files)} TXT files, "
        f"{sum(len(v.splitlines()) for v in new_files.values())} configs"
    )


def main():
    errors = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        jobs = {
            executor.submit(
                refresh,
                name,
                repo,
                folder
            ): name
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
            "Some sources failed. Their previous files were preserved."
        )

    print("All 12 sources synchronized successfully!")


if __name__ == "__main__":
    main()
