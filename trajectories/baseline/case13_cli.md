# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/baseline/case13_cli.jsonl`

**Session init** — model `claude-sonnet-5`, tools: none

**Assistant:**

{"findings": [{"file": "ledgerly/cli.py", "line": 123, "category": "robustness", "title": "CLI always exits with status 0, even on failure", "description": "main() catches every exception from args.func(), prints an 'error: ...' message, but still falls through to `return 0`. Any caller relying on the exit code (shell scripts, cron jobs, CI) will see success even when registration, login, add, list, or summary fail (auth errors, bad input, DB errors, etc.). The except block should re-raise or return a non-zero exit code, and main() should propagate that to sys.exit().", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 91, "category": "security", "title": "Passwords accepted as plaintext CLI arguments", "description": "register and login take the password as a positional command-line argument (args.password). Command-line arguments are visible to other local users via `ps`/`/proc/<pid>/cmdline` and are recorded in shell history files, leaking the plaintext password. Passwords should be read via a hidden prompt (e.g. getpass) instead of being passed as an argv token.", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 96, "category": "security", "title": "Passwords a
… [2500 chars truncated]

---
**Final result** (1 turns, 58.7s, $0.079):

{"findings": [{"file": "ledgerly/cli.py", "line": 123, "category": "robustness", "title": "CLI always exits with status 0, even on failure", "description": "main() catches every exception from args.func(), prints an 'error: ...' message, but still falls through to `return 0`. Any caller relying on the exit code (shell scripts, cron jobs, CI) will see success even when registration, login, add, list, or summary fail (auth errors, bad input, DB errors, etc.). The except block should re-raise or return a non-zero exit code, and main() should propagate that to sys.exit().", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 91, "category": "security", "title": "Passwords accepted as plaintext CLI arguments", "description": "register and login take the password as a positional command-line argument (args.password). Command-line arguments are visible to other local users via `ps`/`/proc/<pid>/cmdline` and are recorded in shell history files, leaking the plaintext password. Passwords should be read via a hidden prompt (e.g. getpass) instead of being passed as an argv token.", "severity": "major"}, {"file": "ledgerly/cli.py", "line": 96, "category": "security", "title": "Passwords a
… [2500 chars truncated]
