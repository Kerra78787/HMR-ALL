HMR-ALL

Automatic mirror of 12 public GitHub repositories.

Features

- Scheduled update configured every 5 minutes
- Manual updates through GitHub Actions
- Mirrors the complete working tree of each source repository
- Keeps all file types and folders; does not filter by protocol or file extension
- Stores each source in its own numbered folder under "Sources/"
- Includes recursive Git submodules
- Downloads Git LFS content when available
- Replaces a source folder only after its new copy has downloaded successfully
- Preserves the previous copy when a source update fails
- Runs up to 4 source updates in parallel

Scope and limitations

- Mirrors the current default branch only
- Does not copy Git history, branches, tags, or ".git" metadata
- Source folder names are fixed labels defined in "update.py"
- If a source repository is renamed or moved, update its repository path in the "SOURCES" mapping in "update.py"
- The 5-minute schedule is configured in GitHub Actions; actual scheduled execution depends on GitHub Actions availability and repository activity

Sources

All mirrored repositories are stored under the "Sources/" directory.

Update

Open GitHub Actions and run the HMR-ALL Auto Update workflow manually, or let the configured schedule trigger it.
