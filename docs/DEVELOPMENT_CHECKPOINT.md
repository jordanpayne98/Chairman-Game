# Development checkpoint

## SETUP-002 — repository setup

Date: 2026-09-19. Design references: GDD chapters 26 (technical architecture) and 27 (delivery stages).

Project instructions were merged through pull request #1. This change brings the previously verified environment diagnostic into the dedicated game repository and adds Linux/Windows automation.

Implemented: Python 3.12 baseline, pinned Pygame 2.6.1 dependency, isolated-environment setup instructions, Windows setup script, environment diagnostic and GitHub Actions workflow. Existing README expanded; no existing gameplay code was present.

Local verification: Python 3.12.14/Pygame 2.6.1 on Linux passed dependency consistency, headless display/font rendering, event delivery, SQLite disk round-trip and database integrity checks. Initial Windows CI caught an open SQLite handle during temporary-file cleanup. The diagnostic now explicitly commits and closes both database connections. GitHub Actions results are reported on the pull request; do not assume they passed from this record.

Limitations: no game, career, Continue, game persistence, content or reusable UI is implemented. No Windows executable has been built. The Windows convenience script, physical input and audio have not been manually tested. Foundation remains incomplete.

## Design source and next task

The supplied attachment identifies itself as GDD revision 0.2. The existing living GDD was separately identified as revision 0.3. This setup uses the established Python/Pygame stack and does not change design. Before gameplay work, read the relevant sections of the current living GDD and inspect the approved visual references, including newer QoL requirements.

Next implementation unit: runnable application shell, followed by new career, one fictional club, validated commands, calendar progression and recoverable saves. Preserve the full Foundation acceptance gate, including one calendar month, knowledge filtering and packaged-build verification. Do not call Foundation complete until all required behaviours pass.
