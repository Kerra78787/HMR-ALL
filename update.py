
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
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
        url = f"https://github.com/{repository}.git"

        print(f"Downloading full repository: {repository}")

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

        # Download Git LFS files when available.
        lfs = shutil.which("git-lfs")

        if lfs:
            run_git(["git", "lfs", "pull"], cwd=checkout)

            run_git([
                "git", "submodule", "foreach",
                "--recursive",
                "git lfs pull"
            ], cwd=checkout)

        # Copy the complete working tree without changing file contents.
        shutil.copytree(
            checkout,
            mirror,
            symlinks=True,
            ignore=ignore_git_metadata
        )

        if not any(mirror.iterdir()):
            raise RuntimeError("Repository copy is empty")

        # Replace only after the complete copy succeeds.
        replace_directory(mirror, destination)

        print(f"OK: {name} <- {repository}")

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
            "Some sources failed. Their previous copies were preserved: "
            + ", ".join(errors)
        )

    print("All 12 full repositories synchronized!")


if __name__ == "__main__":
    main()
s()) for v in new_files.values())
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
        
