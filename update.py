
import os
import requests
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

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

EXCLUDED = {
    "llms.txt",
    "llms-full.txt",
    "blocked_ips.txt",
    "reset_log.txt",
    "commit-timestamp.txt",
    "force-update.txt",
    "last_update.txt",
    "updated.txt",
    ".mirror-manifest.txt",
}

ROOT = Path("Sources")
ROOT.mkdir(exist_ok=True)


def safe_relative(path):
    if not path or "\\" in path:
        raise RuntimeError(f"Invalid path: {path}")

    p = PurePosixPath(path)

    if p.is_absolute() or any(
        part in ("", ".", "..") for part in p.parts
    ):
        raise RuntimeError(f"Unsafe path: {path}")

    return Path(*p.parts)


def make_session():
    session = requests.Session()
    session.headers["User-Agent"] = "HMR-ALL-Updater/4.0"

    token = os.getenv("GITHUB_TOKEN")
    if token:
        session.headers["Authorization"] = f"Bearer {token}"

    return session


def get_json(session, url):
    response = session.get(url, timeout=40)
    response.raise_for_status()
    return response.json()


def is_txt(path):
    return (
        path.lower().endswith(".txt")
        and PurePosixPath(path).name.lower() not in EXCLUDED
    )


def resolve_source_folder(tree, configured_folder):
    paths = [
        item["path"]
        for item in tree
        if item["type"] in ("blob", "tree")
    ]

    if not configured_folder:
        return ""

    prefix = configured_folder + "/"

    if any(
        path == configured_folder or path.startswith(prefix)
        for path in paths
    ):
        return configured_folder

    # Old folder not found: discover the new folder.
    counts = {}

    for item in tree:
        path = item["path"]

        if item["type"] != "blob" or not is_txt(path):
            continue

        parts = PurePosixPath(path).parts

        if len(parts) == 1:
            candidate = ""
        else:
            candidate = parts[0]

        counts[candidate] = counts.get(candidate, 0) + 1

    if not counts:
        raise RuntimeError(
            f"Folder '{configured_folder}' missing; "
            "no TXT folders found. Old files preserved."
        )

    highest = max(counts.values())
    winners = [
        folder for folder, count in counts.items()
        if count == highest
    ]

    if len(winners) != 1:
        raise RuntimeError(
            f"New folder is ambiguous: {winners}. "
            "Old files preserved."
        )

    new_folder = winners[0]

    print(
        f"FOLDER RENAME DETECTED: "
        f"'{configured_folder}' -> "
        f"'{new_folder or '[ROOT]'}'"
    )

    return new_folder


def refresh(name, repo, configured_folder):
    session = make_session()
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
            "GitHub tree incomplete; old files preserved."
        )

    tree = tree_data["tree"]

    folder = resolve_source_folder(tree, configured_folder)
    prefix = folder + "/" if folder else ""

    files = {}

    for item in tree:
        path = item["path"]

        if item["type"] != "blob":
            continue

        if not path.startswith(prefix):
            continue

        if not is_txt(path):
            continue

        relative = path[len(prefix):]
        relative_path = safe_relative(relative)

        encoded_path = quote(path, safe="/")
        encoded_branch = quote(branch, safe="")

        raw_url = (
            f"https://raw.githubusercontent.com/"
            f"{repo}/{encoded_branch}/{encoded_path}"
        )

        response = session.get(raw_url, timeout=60)
        response.raise_for_status()

        files[relative_path.as_posix()] = response.content

    if not files:
        raise RuntimeError(
            "No TXT files found; old files preserved."
        )

    destination = ROOT / name
    destination.mkdir(parents=True, exist_ok=True)

    manifest = destination / ".mirror-manifest.txt"

    old_files = set()

    if manifest.exists():
        old_files = {
            line.strip()
            for line in manifest.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        }

    new_files = set(files)

    # Download all files before changing local files.
    for relative, content in files.items():
        target = destination / safe_relative(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    # Remove deleted or renamed TXT files.
    for relative in old_files - new_files:
        target = destination / safe_relative(relative)

        if target.is_file():
            target.unlink()

    # Update manifest after successful synchronization.
    temp_manifest = destination / ".mirror-manifest.tmp"

    temp_manifest.write_text(
        "\n".join(sorted(new_files))
        + ("\n" if new_files else ""),
        encoding="utf-8"
    )

    temp_manifest.replace(manifest)

    print(f"OK: {name} — {len(files)} TXT files")


errors = []

with ThreadPoolExecutor(max_workers=6) as executor:
    jobs = {
        executor.submit(
            refresh, name, repo, folder
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
        "Some sources failed. Their old files were preserved."
    )

print("All sources synchronized successfully!")
