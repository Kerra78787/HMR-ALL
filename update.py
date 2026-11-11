import os
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


def run_git(command, cwd=None):
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        timeout=900,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def resolve_repository(repository):
    url = f"https://github.com/{repository}"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HMR-ALL-Updater"}
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl()

        parsed = urlparse(final_url)
        parts = parsed.path.strip("/").split("/")

        if parsed.netloc.lower() == "github.com" and len(parts) >= 2:
            owner = parts[0]
            name = parts[1].removesuffix(".git")

            if owner and name:
                resolved = f"{owner}/{name}"

                if resolved.lower() != repository.lower():
                    print(f"Repository moved: {repository} -> {resolved}")

                return resolved

    except Exception as error:
        print(f"Redirect check warning for {repository}: {error}")

    return repository


def ignore_git_metadata(directory, names):
    return {name for name in names if name == ".git"}


def get_paths(directory):
    result = set()

    for current, dirs, files in os.walk(directory, followlinks=False):
        dirs[:] = [d for d in dirs if d != ".git"]

        base = Path(current)

        for name in dirs + files:
            path = base / name

            if path.is_symlink() or path.is_file():
                result.add(path.relative_to(directory).as_posix())

    return result


def verify_copy(source, mirror):
    source_paths = get_paths(source)
    mirror_paths = get_paths(mirror)

    missing = source_paths - mirror_paths
    extra = mirror_paths - source_paths

    if missing or extra:
        details = []

        if missing:
            details.append(
                "Missing files: " + ", ".join(sorted(missing)[:20])
            )

        if extra:
            details.append(
                "Unexpected files: " + ", ".join(sorted(extra)[:20])
            )

        raise RuntimeError("Copy verification failed. " + " | ".join(details))

    print(f"Copy verified: {len(source_paths)} files and links")


def verify_submodules(checkout):
    result = run_git(
        ["git", "submodule", "status", "--recursive"],
        cwd=checkout
    )

    for line in result.stdout.splitlines():
        if line and line[0] in "-+":
            raise RuntimeError(
                "Submodule is missing or at an unexpected commit: " + line
            )


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
        resolved = resolve_repository(repository)
        url = f"https://github.com/{resolved}.git"

        print(f"Downloading: {resolved}")

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

        verify_submodules(checkout)

        shutil.copytree(
            checkout,
            mirror,
            symlinks=True,
            ignore=ignore_git_metadata
        )

        if not any(mirror.iterdir()):
            raise RuntimeError("Repository copy is empty")

        verify_copy(checkout, mirror)

        replace_directory(mirror, destination)

        print(f"SUCCESS: {name} <- {resolved}")

    finally:
        if work.exists():
            shutil.rmtree(work)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)

    errors = []

    print("Starting HMR-ALL synchronization")
    print(f"Total configured sources: {len(SOURCES)}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = {
            executor.submit(refresh, name, repository): name
            for name, repository in SOURCES.items()
        }

        for job in as_completed(jobs):
            name = jobs[job]

            try:
                job.result()
            except Exception as error:
                errors.append(name)
                print(f"FAILED: {name}: {error}")

    print("\n========== SUMMARY ==========")
    print(f"Total sources: {len(SOURCES)}")
    print(f"Successful sources: {len(SOURCES) - len(errors)}")
    print(f"Failed sources: {len(errors)}")

    if errors:
        raise SystemExit(
            "Synchronization failed for: " + ", ".join(errors)
        )

    print("ALL 12 SOURCES SYNCHRONIZED AND VERIFIED!")


if __name__ == "__main__":
    main()
