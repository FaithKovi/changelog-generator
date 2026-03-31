# Changelog Generator

A CLI tool that reads git commit history and generates polished, human-readable changelogs using AI. Run it before each release to produce a ready-to-publish changelog entry. No more manually sorting through commit messages.

Supports two AI providers: **Google Gemini** (free, default) and **Anthropic Claude** (paid, optional).

## The Problem

Writing changelogs is tedious. Most teams either skip it entirely, auto-dump raw commit messages (unreadable), or spend 30+ minutes manually sorting and rewriting commits before each release. The result is changelogs that are either missing, unhelpful, or outdated.

## How It Works

```
Git History → Parse Commits → AI (Gemini or Claude) → Polished Changelog
```

1. Reads commit messages from your git repository using `git log`
2. Filters out noise (merge commits, WIP commits)
3. Sends the commits to an LLM with a prompt that instructs it to:
   - Group changes by category (Added, Changed, Fixed, Removed, etc.)
   - Rewrite commit messages into clear, user-facing descriptions
   - Follow the [Keep a Changelog](https://keepachangelog.com) format
   - Include commit hashes for traceability
4. Outputs clean markdown you can paste directly into your CHANGELOG.md

## An Example Output

Running against a real repository produces something like:

```markdown
## [v2.1.0] — 2026-03-30

### Added
- OAuth 2.0 support with client credentials and device code grant types (a1b2c3d)
- Cross-region storage replication for disaster recovery (e4f5g6h)
- GraphQL API endpoint alongside the existing REST API (i7j8k9l)

### Changed
- Increased maximum file upload size from 10 GB to 50 GB (m0n1o2p)
- Rate limits doubled across all tiers (q3r4s5t)

### Fixed
- Resolved timeout errors when uploading files larger than 2 GB (u6v7w8x)
- Fixed incorrect pagination metadata in list endpoints (y9z0a1b)

### Security
- Server-side encryption (AES-256) now enabled by default on all new storage buckets (c2d3e4f)

### Infrastructure
- Migrated CI pipeline from CircleCI to GitHub Actions (g5h6i7j)
```

## Prerequisites

- **Python 3.8+**
- **Git** installed and available in your PATH
- **A free Google account** (for Gemini, the default provider) OR an **Anthropic API key** (for Claude)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/changelog-generator.git
cd changelog-generator
```

### 2. Create a Virtual Environment

On macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Your API Key

```bash
cp .env.example .env
```

Open `.env` in any editor and add your API key for the provider you want to use.

#### Option A: Google Gemini (Free — Recommended)

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your regular Google/Gmail account
3. Click **Create API Key** and copy it
4. Paste it into your `.env` file:

```
GEMINI_API_KEY=AIzaSy-your-key-here
```

No credit card needed. No billing setup. No expiring credits.

#### Option B: Anthropic Claude (Paid)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and verify your phone number
3. Go to **API Keys** in the sidebar and create a key
4. Paste it into your `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```



## Usage

### Basic — Last 50 commits (uses Gemini by default)

```bash
python changelog.py
```

### Against a specific repo

```bash
git clone https://github.com/some-org/some-repo.git
python changelog.py --repo ./some-repo --last 15
```

### Label a version

```bash
python changelog.py --repo ./some-repo --last 15 --version 1.0.0
```

This produces a heading like `## [v1.0.0] — 2026-03-30`.

### Save to a file

```bash
python changelog.py --repo ./some-repo --last 15 --version 1.0.0 --output CHANGELOG.md
```

### Prepend to an existing changelog

Add the new entry to the top of your existing CHANGELOG.md without overwriting it:

```bash
python changelog.py --repo ./some-repo --since v1.0.0 --version 1.1.0 --output CHANGELOG.md --prepend
```

### Since a tag

Generate a changelog for everything since your last release:

```bash
python changelog.py --since v1.2.0 --version 1.3.0
```

### Since a date

```bash
python changelog.py --since "2025-06-01"
```

### Use Claude instead of Gemini

```bash
python changelog.py --repo ./some-repo --last 15 --provider claude
```

Make sure your `.env` file has `ANTHROPIC_API_KEY` set. You'll also need to install the Anthropic package:

```bash
pip install anthropic
```

## All Options

| Flag | Description | Default |
|------|-------------|---------|
| `--repo` | Path to a local git repository | Current directory |
| `--since` | Start point: a date (`2025-01-01`) or git tag (`v1.2.0`) | None |
| `--last` | Number of recent commits to include | 50 |
| `--version` | Version label for the release heading | "Unreleased" |
| `--output`, `-o` | Save to a file instead of printing to stdout | None (prints) |
| `--prepend` | Prepend to existing output file instead of overwriting | Off |
| `--provider` | AI provider: `gemini` (free) or `claude` (paid) | `gemini` |

## Project Structure

```
changelog-generator/
├── changelog.py        # The entire tool — one file
├── requirements.txt    # Dependencies (google-genai, optionally anthropic)
├── .env.example        # API key template for both providers
├── .gitignore
├── LICENSE             # MIT License
└── README.md           # This file
```

## How the Prompt Works

The prompt sent to the AI follows a specific structure designed to produce consistent, high-quality output:

- **Role framing** tells the model it's acting as a technical writer, not a chatbot
- **Categorization rules** map to the Keep a Changelog standard (Added, Changed, Fixed, Removed, Security, Documentation, Infrastructure)
- **Rewrite instruction** ensures the model doesn't just copy-paste commit messages but rewrites them as user-facing descriptions
- **Noise filtering** tells the model to drop trivial commits (typos, WIP, merge commits)
- **Traceability** includes the short commit hash so readers can find the actual code change

The prompt is in `changelog.py` in the `build_prompt()` function — you can customize it to match your project's conventions.

## Integrating into Your Workflow

### Manual (before a release)

```bash
git tag v2.1.0
python changelog.py --since v2.0.0 --version 2.1.0 --output CHANGELOG.md --prepend
git add CHANGELOG.md
git commit -m "docs: update changelog for v2.1.0"
```

### GitHub Actions (automated)

Add this to `.github/workflows/changelog.yml` to generate a changelog on every release:

```yaml
name: Generate Changelog
on:
  release:
    types: [created]

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history needed for git log

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install google-genai python-dotenv

      - name: Generate changelog
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python changelog.py \
            --since $(git describe --tags --abbrev=0 HEAD~1) \
            --version ${{ github.event.release.tag_name }} \
            --output CHANGELOG.md \
            --prepend

      - name: Commit changelog
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add CHANGELOG.md
          git commit -m "docs: update changelog for ${{ github.event.release.tag_name }}"
          git push
```

To use Claude in the workflow instead, replace `google-genai` with `anthropic`, swap the env variable to `ANTHROPIC_API_KEY`, and add `--provider claude` to the command.

## Customization

### Changing the categories

Edit the prompt in `build_prompt()` to add or rename categories. For example, if your project uses "Performance" instead of "Infrastructure":

```python
# In the prompt, change:
#   - **Infrastructure** — CI/CD, build, dependency updates
# To:
#   - **Performance** — speed improvements, optimization
```

### Changing the AI model

For Gemini, replace `gemini-2.0-flash` in `generate_with_gemini()` with any available model. Options include `gemini-1.5-flash` (wider regional availability) or `gemini-2.0-flash-lite` (lightest and fastest).

For Claude, replace `claude-sonnet-4-20250514` in `generate_with_claude()` with any Anthropic model. Haiku is cheaper and faster for small changelogs; Opus is more thorough for large ones.

### Changing the output format

The prompt currently outputs Keep a Changelog format. You can modify `build_prompt()` to produce any format: plain text, HTML, RST, or your company's internal template.

## Notes

Google Gemini's free tier availability varies by region. If you get a `429 RESOURCE_EXHAUSTED` error with `limit: 0`, try these steps in order:

1. Switch to `gemini-1.5-flash` or `gemini-2.0-flash-lite` (edit the model name in `changelog.py`)
2. Use a VPN connected to a US or EU location
3. Fall back to Claude with `--provider claude`

## License

MIT License. See [LICENSE](LICENSE) for details.
