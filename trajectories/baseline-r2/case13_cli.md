# Trajectory: `/Users/Other/bhopal/projects/micro/HACHATHON/revguard/trajectories/baseline-r2/case13_cli.jsonl`

**Session init** — model `claude-sonnet-5`, tools: none

**Assistant:**

```json
{"findings": [
  {"file": "ledgerly/cli.py", "line": 123, "category": "correctness", "severity": "major", "title": "CLI always exits 0, even on error", "description": "main() catches every exception, prints \"error: ...\", and then falls through to `return 0`. Every invocation of the CLI therefore reports success to the shell regardless of whether the command actually failed (auth failure, bad input, DB error, etc.). Any script or CI job that checks the exit code (e.g. `ledgerly add ... && echo done`) cannot detect failures."},
  {"file": "ledgerly/cli.py", "line": 91, "category": "security", "severity": "major", "title": "Password accepted as a positional command-line argument", "description": "`register` and `login` take the password as a plain argv argument (lines 90-91, 95-96). On most systems this is visible to any other local user via `ps`/`/proc/<pid>/cmdline` while the process runs, and is also written verbatim into the shell history file (e.g. ~/.zsh_history), leaking credentials. Passwords should be read from a prompt (e.g. via getpass) or an environment variable/file instead."},
  {"file": "ledgerly/cli.py", "line": 32, "category": "security", "severity": "minor"
… [3365 chars truncated]

---
**Final result** (1 turns, 76.3s, $0.097):

```json
{"findings": [
  {"file": "ledgerly/cli.py", "line": 123, "category": "correctness", "severity": "major", "title": "CLI always exits 0, even on error", "description": "main() catches every exception, prints \"error: ...\", and then falls through to `return 0`. Every invocation of the CLI therefore reports success to the shell regardless of whether the command actually failed (auth failure, bad input, DB error, etc.). Any script or CI job that checks the exit code (e.g. `ledgerly add ... && echo done`) cannot detect failures."},
  {"file": "ledgerly/cli.py", "line": 91, "category": "security", "severity": "major", "title": "Password accepted as a positional command-line argument", "description": "`register` and `login` take the password as a plain argv argument (lines 90-91, 95-96). On most systems this is visible to any other local user via `ps`/`/proc/<pid>/cmdline` while the process runs, and is also written verbatim into the shell history file (e.g. ~/.zsh_history), leaking credentials. Passwords should be read from a prompt (e.g. via getpass) or an environment variable/file instead."},
  {"file": "ledgerly/cli.py", "line": 32, "category": "security", "severity": "minor"
… [3365 chars truncated]
