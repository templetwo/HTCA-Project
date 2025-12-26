#!/usr/bin/env python3
"""
GitHub Archive Relay (GAR)
--------------------------
A lightweight, single-file tool that:
1. Polls GitHub public orgs/users every N seconds
2. Pushes new commit hashes to IPFS + Arweave
3. Generates an unthrottleable RSS feed

Usage:
    python github-archive-relay.py --orgs TempleTwo,other-org --interval 60

Requirements:
    pip install requests feedgen

Author: Built for the Temple / Open Source
License: MIT
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
import base64
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
    from feedgen.feed import FeedGenerator
except ImportError:
    print("Install dependencies: pip install requests feedgen")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

DEFAULT_INTERVAL = 60  # seconds
DEFAULT_DB = "gar_state.db"
DEFAULT_RSS = "gar_feed.xml"
GITHUB_API = "https://api.github.com"

# Rate limit retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential backoff: 2^retry seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("GAR")

# -----------------------------------------------------------------------------
# Multihash/CID Utilities (for proper IPFS CID generation)
# -----------------------------------------------------------------------------

def compute_ipfs_cid_v1(content: bytes) -> str:
    """
    Compute a proper IPFS CIDv1 using SHA-256 multihash.

    Format: <multibase><version><codec><multihash>
    - multibase: 'b' (base32)
    - version: 0x01
    - codec: 0x55 (raw)
    - multihash: 0x12 (sha2-256) + length + hash

    This creates a valid CIDv1 that can be resolved on IPFS gateways
    (though the content won't exist unless actually pinned).
    """
    # Compute SHA-256 hash
    h = hashlib.sha256(content).digest()

    # Build multihash: <hash-type><length><hash-bytes>
    # 0x12 = sha2-256, len = 32 bytes
    multihash = bytes([0x12, 0x20]) + h

    # Build CID: <version><codec><multihash>
    # version = 1, codec = 0x55 (raw)
    cid_bytes = bytes([0x01, 0x55]) + multihash

    # Encode to base32 (multibase 'b')
    import base64
    cid_b32 = base64.b32encode(cid_bytes).decode('ascii').lower().rstrip('=')

    return 'b' + cid_b32

# -----------------------------------------------------------------------------
# Security & Secret Detection
# -----------------------------------------------------------------------------

import re

# Secret detection patterns
SECRET_PATTERNS = [
    # AWS Keys
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'aws_secret_access_key\s*=\s*["\']?[\w+/=]{40}["\']?', 'AWS Secret Key'),

    # GitHub Tokens
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
    (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth Token'),
    (r'ghs_[a-zA-Z0-9]{36}', 'GitHub App Token'),

    # Generic API Keys
    (r'api[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}["\']?', 'API Key'),
    (r'secret[_-]?key\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}["\']?', 'Secret Key'),
    (r'access[_-]?token\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{20,}["\']?', 'Access Token'),

    # Private Keys
    (r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', 'Private Key'),
    (r'-----BEGIN OPENSSH PRIVATE KEY-----', 'SSH Private Key'),

    # Database Credentials
    (r'postgres://[^:]+:[^@]+@', 'PostgreSQL Connection String'),
    (r'mysql://[^:]+:[^@]+@', 'MySQL Connection String'),
    (r'mongodb(\+srv)?://[^:]+:[^@]+@', 'MongoDB Connection String'),

    # Cloud Provider Tokens
    (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
    (r'AIza[0-9A-Za-z_-]{35}', 'Google Cloud API Key'),
    (r'sk_live_[0-9a-zA-Z]{24,}', 'Stripe Live Key'),

    # Generic High-Entropy Strings (potential secrets)
    (r'["\'][a-zA-Z0-9_\-]{50,}["\']', 'High-Entropy String'),
]

# Sensitive file patterns
SENSITIVE_FILES = [
    '.env',
    '.env.local',
    '.env.production',
    'credentials.json',
    'secrets.yaml',
    'config/secrets',
    'id_rsa',
    'id_dsa',
    '.pem',
    '.key',
    'keyfile',
    'service-account.json',
]

def contains_secrets(text: str) -> tuple[bool, list]:
    """
    Scan text for potential secrets.

    Returns:
        (has_secrets: bool, findings: list of (pattern_name, match))
    """
    findings = []

    for pattern, name in SECRET_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            findings.append((name, match.group(0)[:50]))  # Truncate for logging

    return len(findings) > 0, findings

def is_sensitive_file(file_path: str) -> bool:
    """Check if a file path indicates sensitive content."""
    file_path_lower = file_path.lower()
    return any(pattern in file_path_lower for pattern in SENSITIVE_FILES)

def should_archive_commit(commit_data: dict, check_secrets: bool = True) -> tuple[bool, str]:
    """
    Determine if a commit should be archived based on security checks.

    Args:
        commit_data: Commit metadata dictionary
        check_secrets: Whether to perform secret detection (default: True)

    Returns:
        (should_archive: bool, reason: str)
    """
    if not check_secrets:
        return True, "Secret checking disabled"

    # Check commit message for secrets
    message = commit_data.get("message", "")
    has_secrets, findings = contains_secrets(message)

    if has_secrets:
        reasons = "; ".join([f"{name}" for name, _ in findings])
        return False, f"Secrets detected in message: {reasons}"

    # Additional metadata checks could go here
    # (e.g., checking file lists if we fetch commit details)

    return True, "Safe to archive"

# -----------------------------------------------------------------------------
# Database Layer (SQLite - zero config)
# -----------------------------------------------------------------------------

def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database for tracking seen commits."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sha TEXT UNIQUE NOT NULL,
            repo TEXT NOT NULL,
            message TEXT,
            author TEXT,
            timestamp TEXT,
            ipfs_cid TEXT,
            arweave_tx TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_sha ON commits(sha)
    """)
    conn.commit()
    return conn

def commit_exists(conn: sqlite3.Connection, sha: str) -> bool:
    """Check if we've already seen this commit."""
    cur = conn.execute("SELECT 1 FROM commits WHERE sha = ?", (sha,))
    return cur.fetchone() is not None

def store_commit(conn: sqlite3.Connection, commit_data: dict) -> None:
    """Store a new commit record."""
    conn.execute("""
        INSERT OR IGNORE INTO commits (sha, repo, message, author, timestamp, ipfs_cid, arweave_tx)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        commit_data["sha"],
        commit_data["repo"],
        commit_data.get("message", ""),
        commit_data.get("author", ""),
        commit_data.get("timestamp", ""),
        commit_data.get("ipfs_cid"),
        commit_data.get("arweave_tx")
    ))
    conn.commit()

def get_recent_commits(conn: sqlite3.Connection, limit: int = 100) -> list:
    """Get recent commits for RSS feed generation."""
    cur = conn.execute("""
        SELECT sha, repo, message, author, timestamp, ipfs_cid, arweave_tx, created_at
        FROM commits ORDER BY id DESC LIMIT ?
    """, (limit,))
    return cur.fetchall()

# -----------------------------------------------------------------------------
# GitHub Polling with Rate Limit Handling
# -----------------------------------------------------------------------------

def get_github_headers() -> dict:
    """Build headers with optional auth token."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Archive-Relay/1.0"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def handle_rate_limit(resp: requests.Response, retry: int) -> bool:
    """
    Handle GitHub rate limiting with exponential backoff.
    Returns True if should retry, False if should give up.
    """
    if resp.status_code in (403, 429):
        # Check if rate limited
        remaining = resp.headers.get("X-RateLimit-Remaining", "0")
        reset_time = resp.headers.get("X-RateLimit-Reset")

        if remaining == "0" and reset_time:
            # Rate limited - calculate wait time
            reset_timestamp = int(reset_time)
            current_timestamp = int(time.time())
            wait_seconds = max(reset_timestamp - current_timestamp, 0)

            if retry < MAX_RETRIES and wait_seconds < 3600:  # Don't wait more than 1 hour
                log.warning(f"Rate limited. Waiting {wait_seconds}s until reset...")
                time.sleep(wait_seconds + 1)
                return True

        # Exponential backoff for other 403/429 errors
        if retry < MAX_RETRIES:
            wait = RETRY_BACKOFF_BASE ** retry
            log.warning(f"Request failed (403/429). Retrying in {wait}s... (attempt {retry + 1}/{MAX_RETRIES})")
            time.sleep(wait)
            return True

    return False

def fetch_org_repos(org: str) -> list:
    """Fetch all public repos for an org/user with rate limit handling."""
    repos = []
    page = 1
    headers = get_github_headers()

    while True:
        # Try as org first, fall back to user
        for endpoint in [f"/orgs/{org}/repos", f"/users/{org}/repos"]:
            url = f"{GITHUB_API}{endpoint}?per_page=100&page={page}&type=public"

            for retry in range(MAX_RETRIES):
                try:
                    resp = requests.get(url, headers=headers, timeout=30)

                    if resp.status_code == 200:
                        data = resp.json()
                        if not data:
                            return repos
                        repos.extend(data)
                        if len(data) < 100:
                            return repos
                        page += 1
                        break
                    elif resp.status_code == 404:
                        break  # Try next endpoint
                    elif handle_rate_limit(resp, retry):
                        continue  # Retry after backoff
                    else:
                        log.warning(f"GitHub API error {resp.status_code}: {resp.text[:200]}")
                        return repos
                except Exception as e:
                    log.error(f"Error fetching repos for {org}: {e}")
                    if retry < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF_BASE ** retry)
                        continue
                    return repos
            else:
                # All retries exhausted
                return repos
        else:
            # Neither endpoint worked
            return repos

    return repos

def fetch_recent_commits(repo_full_name: str, since: Optional[str] = None) -> list:
    """Fetch recent commits for a repo with rate limit handling."""
    headers = get_github_headers()
    url = f"{GITHUB_API}/repos/{repo_full_name}/commits?per_page=30"
    if since:
        url += f"&since={since}"

    for retry in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=30)

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 409:  # Empty repo
                return []
            elif handle_rate_limit(resp, retry):
                continue  # Retry after backoff
            else:
                log.debug(f"Error fetching commits for {repo_full_name}: {resp.status_code}")
                return []
        except Exception as e:
            log.error(f"Error fetching commits for {repo_full_name}: {e}")
            if retry < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_BASE ** retry)
                continue
            return []

    return []

# -----------------------------------------------------------------------------
# IPFS Integration
# -----------------------------------------------------------------------------

def pin_to_ipfs(data: dict) -> Optional[str]:
    """
    Pin commit data to IPFS. Returns CID if successful.

    Supports:
    - Local IPFS node (IPFS_API env var)
    - Pinata (PINATA_API_KEY + PINATA_SECRET_KEY env vars)
    - Fallback: Compute valid CIDv1 locally (content addressable proof)
    """
    content = json.dumps(data, indent=2, default=str).encode()

    # Try local IPFS node first
    ipfs_api = os.environ.get("IPFS_API", "http://localhost:5001")
    try:
        resp = requests.post(
            f"{ipfs_api}/api/v0/add",
            files={"file": ("commit.json", content)},
            timeout=30
        )
        if resp.status_code == 200:
            cid = resp.json().get("Hash")
            log.info(f"Pinned to IPFS: {cid}")
            return cid
    except requests.exceptions.ConnectionError:
        pass  # No local node, try alternatives
    except Exception as e:
        log.debug(f"Local IPFS failed: {e}")

    # Try Pinata
    pinata_key = os.environ.get("PINATA_API_KEY")
    pinata_secret = os.environ.get("PINATA_SECRET_KEY")
    if pinata_key and pinata_secret:
        try:
            resp = requests.post(
                "https://api.pinata.cloud/pinning/pinJSONToIPFS",
                json={"pinataContent": data},
                headers={
                    "pinata_api_key": pinata_key,
                    "pinata_secret_api_key": pinata_secret
                },
                timeout=30
            )
            if resp.status_code == 200:
                cid = resp.json().get("IpfsHash")
                log.info(f"Pinned to Pinata: {cid}")
                return cid
        except Exception as e:
            log.debug(f"Pinata failed: {e}")

    # Fallback: Compute valid CIDv1 locally
    # This creates a proper IPFS CID that proves content addressability
    # even though the content isn't actually pinned anywhere
    cid = compute_ipfs_cid_v1(content)
    log.debug(f"No IPFS available, computed CIDv1: {cid}")
    return cid

# -----------------------------------------------------------------------------
# Arweave Integration (FIXED)
# -----------------------------------------------------------------------------

def post_to_arweave(data: dict) -> Optional[str]:
    """
    Post commit data to Arweave via Bundlr/Irys.
    Returns transaction ID if successful.

    Requires BUNDLR_API_KEY env var for Bundlr uploads.
    Uses Irys Network for cost-effective permanent storage.
    """
    bundlr_key = os.environ.get("BUNDLR_API_KEY")
    if not bundlr_key:
        log.debug("No BUNDLR_API_KEY configured")
        return None

    # Use Irys (formerly Bundlr) for uploads
    irys_node = os.environ.get("IRYS_NODE", "https://node2.irys.xyz")

    try:
        content = json.dumps(data, indent=2, default=str)

        # Irys upload endpoint
        resp = requests.post(
            f"{irys_node}/tx",
            headers={
                "Authorization": f"Bearer {bundlr_key}",
                "Content-Type": "application/json"
            },
            data=content,
            timeout=60
        )

        if resp.status_code in (200, 201):
            result = resp.json()
            tx_id = result.get("id")
            if tx_id:
                log.info(f"Posted to Arweave (Irys): {tx_id}")
                return tx_id
        else:
            log.debug(f"Arweave upload failed: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        log.debug(f"Arweave failed: {e}")

    return None

# -----------------------------------------------------------------------------
# RSS Feed Generation
# -----------------------------------------------------------------------------

def generate_rss(conn: sqlite3.Connection, output_path: str, orgs: list) -> None:
    """Generate RSS feed from stored commits."""
    fg = FeedGenerator()
    fg.id(f"urn:gar:{hashlib.md5(','.join(orgs).encode()).hexdigest()}")
    fg.title(f"GitHub Archive Relay - {', '.join(orgs)}")
    fg.description("Decentralized archive of GitHub commits")
    fg.link(href="https://github.com", rel="alternate")
    fg.language("en")
    fg.lastBuildDate(datetime.now(timezone.utc))

    commits = get_recent_commits(conn, limit=100)

    for sha, repo, message, author, timestamp, ipfs_cid, arweave_tx, created_at in commits:
        fe = fg.add_entry()
        fe.id(f"urn:github:commit:{sha}")
        fe.title(f"[{repo}] {message[:80]}..." if len(message) > 80 else f"[{repo}] {message}")
        fe.link(href=f"https://github.com/{repo}/commit/{sha}")
        fe.author({"name": author})

        # Build description with archive links
        desc = f"<p><strong>Commit:</strong> {sha}</p>"
        desc += f"<p><strong>Author:</strong> {author}</p>"
        desc += f"<p><strong>Message:</strong> {message}</p>"
        if ipfs_cid:
            desc += f"<p><strong>IPFS:</strong> <a href='https://ipfs.io/ipfs/{ipfs_cid}'>{ipfs_cid}</a></p>"
        if arweave_tx:
            desc += f"<p><strong>Arweave:</strong> <a href='https://arweave.net/{arweave_tx}'>{arweave_tx}</a></p>"
        fe.description(desc)

        # Parse timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                fe.published(dt)
                fe.updated(dt)
        except:
            pass

    # Write RSS and Atom feeds
    fg.rss_file(output_path)
    atom_path = output_path.replace(".xml", ".atom")
    fg.atom_file(atom_path)

    log.info(f"Generated RSS: {output_path} and Atom: {atom_path}")

# -----------------------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------------------

def poll_once(conn: sqlite3.Connection, orgs: list, rss_path: str, check_secrets: bool = True) -> int:
    """Run one polling cycle. Returns number of new commits found."""
    new_commits = 0

    for org in orgs:
        log.info(f"Polling {org}...")
        repos = fetch_org_repos(org)
        log.info(f"  Found {len(repos)} repos")

        for repo in repos:
            repo_name = repo.get("full_name")
            if not repo_name:
                continue

            commits = fetch_recent_commits(repo_name)

            for commit in commits:
                sha = commit.get("sha")
                if not sha or commit_exists(conn, sha):
                    continue

                # Extract commit info
                commit_info = commit.get("commit", {})
                author_info = commit_info.get("author", {})

                commit_data = {
                    "sha": sha,
                    "repo": repo_name,
                    "message": commit_info.get("message", "")[:500],
                    "author": author_info.get("name", "unknown"),
                    "timestamp": author_info.get("date", ""),
                    "url": commit.get("html_url", ""),
                    "tree_sha": commit_info.get("tree", {}).get("sha", "")
                }

                # Security check: scan for secrets before archiving
                should_archive, reason = should_archive_commit(commit_data, check_secrets=check_secrets)

                if not should_archive:
                    log.warning(f"  Skipping commit {sha[:8]} from {repo_name}: {reason}")
                    continue

                # Archive to IPFS
                commit_data["ipfs_cid"] = pin_to_ipfs(commit_data)

                # Archive to Arweave
                commit_data["arweave_tx"] = post_to_arweave(commit_data)

                # Store in local DB
                store_commit(conn, commit_data)
                new_commits += 1

                log.info(f"  New commit: {repo_name} {sha[:8]} - {commit_data['message'][:50]}...")

    # Regenerate RSS feed
    if new_commits > 0:
        generate_rss(conn, rss_path, orgs)

    return new_commits

def run_daemon(orgs: list, interval: int, db_path: str, rss_path: str, check_secrets: bool = True) -> None:
    """Run continuous polling daemon."""
    conn = init_db(db_path)
    log.info(f"Starting GitHub Archive Relay")
    log.info(f"  Orgs: {', '.join(orgs)}")
    log.info(f"  Interval: {interval}s")
    log.info(f"  Database: {db_path}")
    log.info(f"  RSS: {rss_path}")
    log.info(f"  GitHub Token: {'configured' if os.environ.get('GITHUB_TOKEN') else 'not set (60 req/hr limit)'}")
    log.info(f"  IPFS: {'configured' if os.environ.get('IPFS_API') or os.environ.get('PINATA_API_KEY') else 'local CID generation'}")
    log.info(f"  Arweave: {'configured' if os.environ.get('BUNDLR_API_KEY') else 'not configured'}")
    log.info(f"  Secret Detection: {'disabled' if not check_secrets else 'enabled'}")
    log.info("-" * 60)

    # Initial poll
    generate_rss(conn, rss_path, orgs)  # Generate empty feed first

    while True:
        try:
            new = poll_once(conn, orgs, rss_path, check_secrets=check_secrets)
            log.info(f"Poll complete: {new} new commits")
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(interval)

    conn.close()

# -----------------------------------------------------------------------------
# Monitoring & Stats
# -----------------------------------------------------------------------------

def show_stats(db_path: str) -> None:
    """Display database statistics."""
    try:
        conn = sqlite3.connect(db_path)

        # Total commits
        cur = conn.execute("SELECT COUNT(*) FROM commits")
        total = cur.fetchone()[0]

        # Commits in last hour
        cur = conn.execute("""
            SELECT COUNT(*) FROM commits
            WHERE datetime(created_at) >= datetime('now', '-1 hour')
        """)
        last_hour = cur.fetchone()[0]

        # Commits in last 24 hours
        cur = conn.execute("""
            SELECT COUNT(*) FROM commits
            WHERE datetime(created_at) >= datetime('now', '-24 hours')
        """)
        last_24h = cur.fetchone()[0]

        # Archive success rates
        cur = conn.execute("SELECT COUNT(*) FROM commits WHERE ipfs_cid IS NOT NULL")
        ipfs_count = cur.fetchone()[0]

        cur = conn.execute("SELECT COUNT(*) FROM commits WHERE arweave_tx IS NOT NULL")
        arweave_count = cur.fetchone()[0]

        # Top repos
        cur = conn.execute("""
            SELECT repo, COUNT(*) as count
            FROM commits
            GROUP BY repo
            ORDER BY count DESC
            LIMIT 10
        """)
        top_repos = cur.fetchall()

        # Display stats
        print("\n" + "="*60)
        print("GitHub Archive Relay - Statistics")
        print("="*60)
        print(f"\nTotal Commits:        {total}")
        print(f"Last Hour:            {last_hour}")
        print(f"Last 24 Hours:        {last_24h}")
        print(f"\nArchive Status:")
        print(f"  IPFS Archived:      {ipfs_count} ({100*ipfs_count/total if total else 0:.1f}%)")
        print(f"  Arweave Archived:   {arweave_count} ({100*arweave_count/total if total else 0:.1f}%)")

        if top_repos:
            print(f"\nTop Repositories:")
            for repo, count in top_repos:
                print(f"  {repo:40} {count:5} commits")

        print("="*60 + "\n")

        conn.close()
    except Exception as e:
        print(f"Error reading stats: {e}")

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Archive Relay - Decentralized commit archiving",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  GITHUB_TOKEN          GitHub personal access token (for higher rate limits)
  IPFS_API             IPFS API endpoint (default: http://localhost:5001)
  PINATA_API_KEY       Pinata API key for IPFS pinning
  PINATA_SECRET_KEY    Pinata secret key
  BUNDLR_API_KEY       Bundlr/Irys API key for Arweave uploads
  IRYS_NODE            Irys node URL (default: https://node2.irys.xyz)

Examples:
  # Basic usage
  python github-archive-relay.py --orgs TempleTwo

  # Multiple orgs with custom interval
  python github-archive-relay.py --orgs TempleTwo,anthropics,openai --interval 120

  # Run once (no daemon)
  python github-archive-relay.py --orgs TempleTwo --once
        """
    )
    parser.add_argument(
        "--orgs", "-o",
        help="Comma-separated list of GitHub orgs/users to monitor"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Polling interval in seconds (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--rss",
        default=DEFAULT_RSS,
        help=f"RSS feed output path (default: {DEFAULT_RSS})"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no daemon mode)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )
    parser.add_argument(
        "--no-secret-check",
        action="store_true",
        help="Disable secret detection (archives all commits including those with potential secrets)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle stats command
    if args.stats:
        show_stats(args.db)
        return

    orgs = [o.strip() for o in args.orgs.split(",") if o.strip()]

    if not orgs:
        parser.error("At least one org/user must be specified")

    check_secrets = not args.no_secret_check

    if args.once:
        conn = init_db(args.db)
        poll_once(conn, orgs, args.rss, check_secrets=check_secrets)
        conn.close()
    else:
        run_daemon(orgs, args.interval, args.db, args.rss, check_secrets=check_secrets)

if __name__ == "__main__":
    main()
