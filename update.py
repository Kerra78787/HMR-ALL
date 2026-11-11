import os
import requests
from pathlib import Path
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
    "llms.txt", "llms-full.txt",
    "blocked_ips.txt", "reset_log.txt",
    "commit-timestamp.txt", "force-update.txt",
    "last_update.txt", "updated.txt",
}

ROOT = Path("Sources")
ROOT.mkdir(exist_ok=True)

session = requests.Session()
session.headers["User-Agent"] = "HMR-ALL-Updater/2.0"

token = os.getenv("GITHUB_TOKEN")
if token:
    session.headers["Authorization"] = f"Bearer {token}"


def get_json(url):
    response = session.get(url, timeout=40)
    response.raise_for_status()
    return response.json()


def refresh(name, repo, folder):
    api = f"https://api.github.com/repos/{repo}"
    info = get_json(api)
    branch = info["default_branch"]

    tree = get_json(
        f"{api}/git/trees/{branch}?recursive=1"
    )

    prefix = f"{folder}/" if folder else ""
    files = {}

    for item in tree["tree"]:
        path = item["path"]

        if item["type"] != "blob":
            continue
        if not path.startswith(prefix):
            continue
        if not path.lower().endswith(".txt"):
            continue
        if Path(path).name.lower() in EXCLUDED:
            continue

        relative = path[len(prefix):]
        if not relative:
            continue

        raw_url = (
            f"https://raw.githubusercontent.com/"
            f"{repo}/{branch}/{path}"
        )
        response = session.get(raw_url, timeout=60)
        response.raise_for_status()
        files[relative] = response.content

    if not files:
        raise RuntimeError("Çeşmede .txt faýl tapylmady")

    destination = ROOT / name
    destination.mkdir(parents=True, exist_ok=True)

    manifest = destination / ".mirror-manifest.txt"
    old_files = set()

    if manifest.exists():
        old_files = set(manifest.read_text(encoding="utf-8").splitlines())

    new_files = set(files)

    for relative, content in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    for relative in old_files - new_files:
        target = destination / relative
        if target.is_file():
            target.unlink()

    manifest.write_text(
        "\n".join(sorted(new_files)) + "\n",
        encoding="utf-8"
    )

    print(f"OK: {name} — {len(files)} faýl")


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

print(f"\nÇeşmeler: {len(SOURCES)}")
print(f"Ýalňyşlyklar: {len(errors)}")

if errors:
    raise SystemExit("Käbir çeşmeler täzelenmedi!")
