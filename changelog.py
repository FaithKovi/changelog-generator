"""
changelog.py — Generate polished changelogs from git history using AI.

Reads git commit messages from a repository, groups them by type,
and uses an LLM to produce a clean, human-readable CHANGELOG.md.

Supports two AI providers:
    - Google Gemini (default) — free, no credit card needed
    - Anthropic Claude        — requires API key from console.anthropic.com

Usage:
    python changelog.py                             # Last 50 commits (Gemini)
    python changelog.py --since "2025-01-01"        # Since a date
    python changelog.py --since "v1.2.0"            # Since a tag
    python changelog.py --last 20                   # Last 20 commits
    python changelog.py --repo /path/to/repo        # Different repo
    python changelog.py --output CHANGELOG.md       # Save to file
    python changelog.py --version "2.1.0"           # Label the release
    python changelog.py --provider claude           # Use Claude instead
"""

import subprocess
import argparse
import os
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional


# Git Functions

def get_commits(repo_path=".", since=None, last=50):
    """
    Read commit messages from a git repository.

    Args:
        repo_path: Path to the git repository (default: current directory).
        since:     A date string ("2025-01-01") or tag ("v1.2.0") to start from.
        last:      Number of recent commits to fetch if 'since' is not set.

    Returns:
        A list of dicts with keys: hash, author, date, message
    """
    # Build the git log command
    # Format: hash | author name | date | full commit message
    separator = "---COMMIT_SEP---"
    log_format = f"%H|%an|%ai|%B{separator}"

    cmd = ["git", "-C", repo_path, "log", f"--pretty=format:{log_format}"]

    if since:
        # Check if 'since' looks like a tag/ref or a date
        tag_check = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--verify", since],
            capture_output=True, text=True
        )
        if tag_check.returncode == 0:
            # It's a valid git ref (tag, branch, commit)
            cmd.append(f"{since}..HEAD")
        else:
            # Treat it as a date
            cmd.append(f"--since={since}")
    else:
        cmd.append(f"-{last}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running git log: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'git' command not found. Make sure git is installed.")
        sys.exit(1)

    raw = result.stdout.strip()
    if not raw:
        print("No commits found. Check your --since or --last value.")
        sys.exit(0)

    # Parse the raw output into structured commits
    commits = []
    for block in raw.split(separator):
        block = block.strip()
        if not block:
            continue

        parts = block.split("|", 3)
        if len(parts) < 4:
            continue

        commit_hash, author, date, message = parts
        message = message.strip()

        # Skip empty merge commits
        if message.lower().startswith("merge") and len(message.split("\n")[0]) < 80:
            continue

        commits.append({
            "hash": commit_hash[:8],  # Short hash is enough
            "author": author.strip(),
            "date": date.strip()[:10],  # Just the date, not time
            "message": message,
        })

    return commits


def get_repo_name(repo_path="."):
    """Try to extract the repository name from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "remote", "get-url", "origin"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract name from URLs like:
            #   https://github.com/user/repo.git
            #   git@github.com:user/repo.git
            name = url.rstrip("/").split("/")[-1]
            return name.replace(".git", "")
    except Exception:
        pass
    return "Project"


# AI Changelog Generation

def build_prompt(commits, version=None):
    """Build the prompt that will be sent to whichever AI provider."""
    commit_text = ""
    for c in commits:
        commit_text += f"- [{c['hash']}] ({c['date']}) {c['message']}\n"

    today = datetime.now().strftime("%Y-%m-%d")
    if version:
        version_label = f"v{version}" if not version.startswith("v") else version
        heading_hint = f'Use this heading: "## [{version_label}] — {today}"'
    else:
        heading_hint = f'Use this heading: "## Unreleased — {today}"'

    return f"""You are a technical writer generating a changelog from git commits.

Here are the raw git commits:

{commit_text}

Generate a clean, professional changelog entry in markdown. Follow these rules:

1. {heading_hint}
2. Group changes into these categories (skip empty categories):
   - **Added** — new features or capabilities
   - **Changed** — modifications to existing functionality
   - **Fixed** — bug fixes
   - **Removed** — removed features or deprecated items
   - **Security** — security-related changes
   - **Documentation** — docs-only changes
   - **Infrastructure** — CI/CD, build, dependency updates
3. Write each item as a concise, user-facing description. Don't just copy the commit message — rewrite it to be clear and useful to someone reading a changelog.
4. Drop trivial commits (typo fixes, merge commits, "wip" commits) unless they represent meaningful changes.
5. Include the short commit hash in parentheses at the end of each item, like: (abc1234)
6. Use the Keep a Changelog format (keepachangelog.com).
7. Output ONLY the markdown — no preamble, no explanation, no code fences.
"""


def generate_with_gemini(prompt):
    """Generate changelog using Google Gemini (free, no credit card needed)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        print("Then add it to your .env file:")
        print('  GEMINI_API_KEY=your_key_here')
        sys.exit(1)

    try:
        from google import genai
    except ImportError:
        print("Error: 'google-genai' package not installed.")
        print("Run: pip install google-genai")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print("Generating changelog with Gemini...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )

    return response.text


def generate_with_claude(prompt):
    """Generate changelog using Anthropic Claude (requires paid API key)."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set.")
        print("Get a key at: https://console.anthropic.com/")
        print("Then add it to your .env file:")
        print('  ANTHROPIC_API_KEY=your_key_here')
        sys.exit(1)

    try:
        from anthropic import Anthropic
    except ImportError:
        print("Error: 'anthropic' package not installed.")
        print("Run: pip install anthropic")
        sys.exit(1)

    client = Anthropic(api_key=api_key, timeout=120.0)

    print("Generating changelog with Claude...")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def generate_changelog(commits, version=None, repo_name="Project", provider="gemini"):
    """
    Send commits to an LLM and get back a polished changelog.

    Args:
        commits:   List of commit dicts from get_commits().
        version:   Optional version label (e.g., "2.1.0").
        repo_name: Name of the project for the heading.
        provider:  Which AI to use — "gemini" (default, free) or "claude".

    Returns:
        A string containing the formatted changelog in markdown.
    """
    prompt = build_prompt(commits, version)

    if provider == "claude":
        return generate_with_claude(prompt)
    else:
        return generate_with_gemini(prompt)


# Main

def main():
    parser = argparse.ArgumentParser(
        description="Generate a polished changelog from git commit history using AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python changelog.py                           # Last 50 commits
  python changelog.py --since v1.2.0            # All commits since tag v1.2.0
  python changelog.py --since "2025-06-01"      # All commits since June 1
  python changelog.py --last 30 --version 2.1.0 # Last 30 commits, label as v2.1.0
  python changelog.py --output CHANGELOG.md     # Save to file
        """,
    )
    parser.add_argument(
        "--repo", default=".",
        help="Path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--since", default=None,
        help="Starting point: a date (2025-01-01) or git tag (v1.2.0)",
    )
    parser.add_argument(
        "--last", type=int, default=50,
        help="Number of recent commits to include (default: 50)",
    )
    parser.add_argument(
        "--version", default=None,
        help="Version label for this release (e.g., 2.1.0)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Save changelog to a file instead of printing to stdout",
    )
    parser.add_argument(
        "--prepend", action="store_true",
        help="Prepend to existing output file instead of overwriting",
    )
    parser.add_argument(
        "--provider", default="gemini",
        choices=["gemini", "claude"],
        help="AI provider: 'gemini' (free, default) or 'claude' (requires API key)",
    )

    args = parser.parse_args()

    # Read commits from git
    print(f"Reading commits from '{os.path.abspath(args.repo)}'...")
    commits = get_commits(
        repo_path=args.repo,
        since=args.since,
        last=args.last,
    )
    print(f"Found {len(commits)} commits.")

    if not commits:
        print("No commits to process.")
        return

    # Get repo namefor the heading
    repo_name = get_repo_name(args.repo)

    # Generate the changelog
    changelog = generate_changelog(
        commits=commits,
        version=args.version,
        repo_name=repo_name,
        provider=args.provider,
    )

    # Output
    if args.output:
        if args.prepend and os.path.exists(args.output):
            # Read existing content and prepend the new entry
            with open(args.output, "r") as f:
                existing = f.read()
            with open(args.output, "w") as f:
                f.write(changelog + "\n\n" + existing)
            print(f"Prepended to {args.output}")
        else:
            with open(args.output, "w") as f:
                f.write(changelog + "\n")
            print(f"Saved to {args.output}")
    else:
        # Printto stdout
        print("\n" + "=" * 50)
        print(changelog)
        print("=" * 50)


if __name__ == "__main__":
    main()
