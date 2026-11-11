
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed


SOURCES = {
    "01-MustafaBaqer": "MustafaBaqer/VestraNet-Nodes",
    "02-aviamastersgh": "aviamastersgh/vpn-free-russia",
    "03-R3ZARAHIMI": "R3ZARAHIMI/tg-v2ray-configs-every2h",
    "04-ALIILAPRO": "ALIILAPRO/v2rayNG-Config",
    "05-ermaozi": "ermaozi/get_subscribe",
    "06-FlareFeed": "svinakraft-maker/FlareFeed",
    "07-alireza786786": "alireza786786/Free-V2ray-Configs",
    "08-daily_free_vpn": "cbusifabcap/daily_free_vpn",
    "09-0xRadikal": "0xRadikal/Free-v2ray-Configs",
    "10-histeenn": "histeenn/VLESS-PO-GRIBI",
    "11-igareck": "igareck/vpn-configs-for-russia",
    "12-mrdevmohamed": "mrdevmohamed/v2ray-configs",
}

ROOT = Path("Sources")


def resolve_repository(repository):
    original_url = f"https://github.com/{repository}"

    try:
        request = urllib.request.Request(
            original_url,
            headers={"User-Agent": "HMR-ALL-Updater"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl()

        parsed = urlparse(final_url)
        parts = parsed.path.strip("/").split("/")

        if parsed.netloc.lower() == "github.com" and len(parts) >= 2:
            owner = parts[0]
            name = parts[1].removesuffix(".git")
            resolved = f"{owner}/{name}"

            if resolved.lower() != repository.lower():
                print(f"Repository renamed or moved: {repository} -> {resolved}")

            return resolved

    except Exception as error:
        print(f"Could not resolve redirect for {repository}: {error}")

    return repository


def run_git(command, cwd=None):
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        timeout=600
    )


def ignore_git_metadata(directory, names):
    return {name for name in names if name == ".git"}


def replace_directory(new_dir, destination):
    backup = ROOT / f".{destination.name}.backup"

    if backup.exists():
        shutil.rmtree(backup)

    had_old = destination.exists()

    try:
        if had_old:
            destination.rename(backup)

        new_dir.rename(destination)

    except Exception:
        if destination.exists():
            shutil.rmtree(destination)

        if had_old and backup.exists():
            backup.rename(destination)

        raise

    if backup.exists():
        shutil.rmtree(backup)


def refresh(name, repository):
    destination = ROOT / name
    work = Path(tempfile.mkdtemp(prefix=".hmr-", dir=ROOT))
    checkout = work / "checkout"
    mirror = work / "mirror"

    try:
        resolved_repository = resolve_repository(repository)
        url = f"https://github.com/{resolved_repository}.git"

        print(f"Downloading repository: {resolved_repository}")

        run_git([
            "git",
            "-c", "core.symlinks=true",
            "clone",
            "--depth", "1",
            "--single-branch",
            "--recurse-submodules",
            "--shallow-submodules",
            url,
            str(checkout),
        ])

        if shutil.which("git-lfs"):
            run_git(["git", "lfs", "pull"], cwd=checkout)

            run_git([
                "git",
                "submodule",
                "foreach",
                "--recursive",
                "git lfs pull"
            ], cwd=checkout)

        shutil.copytree(
            checkout,
            mirror,
            symlinks=True,
            ignore=ignore_git_metadata
        )

        if not any(mirror.iterdir()):
            raise RuntimeError("Repository copy is empty")

        replace_directory(mirror, destination)

        print(f"OK: {name} <- {resolved_repository}")

    finally:
        if work.exists():
            shutil.rmtree(work)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    errors = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = {
            executor.submit(refresh, name, repo): name
            for name, repo in SOURCES.items()
        }

        for job in as_completed(jobs):
            name = jobs[job]

            try:
                job.result()
            except Exception as error:
                errors.append(name)
                print(f"ERROR: {name}: {error}")

    print(f"\nTotal sources: {len(SOURCES)}")
    print(f"Failed sources: {len(errors)}")

    if errors:
        raise SystemExit(
            "Some sources failed. Previous copies were preserved: "
            + ", ".join(errors)
        )

    print("All 12 repositories synchronized successfully!")


if __name__ == "__main__":
    main()
