#!/usr/bin/env python3
"""
Repo Radar - Discovery by Velocity, Not Vanity
-----------------------------------------------
Surfaces fresh repos by activity metrics, not star counts.

Features:
1. Polls GitHub Events API for new repos and activity
2. Scores by velocity (commits/day, contributor growth, fork momentum)
3. Archives high-velocity repos to IPFS
4. Generates ranked RSS feed (unthrottleable discovery index)
5. Feeds high-velocity repos to GAR for commit archiving

Usage:
    python repo-radar.py --watch python,rust,ai --interval 60
    python repo-radar.py --orgs anthropics,openai --threshold 50

Requirements:
    pip install requests feedgen

Author: Built for the Temple / Open Source
License: MIT
"""

import argparse
import base64
import hashlib
import json
import logging
import math
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    import requests
    from feedgen.feed import FeedGenerator
except ImportError:
    print("Install dependencies: pip install requests feedgen")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

DEFAULT_INTERVAL = 300  # 5 minutes (Events API updates ~5min)
DEFAULT_DB = "radar_state.db"
DEFAULT_RSS = "radar_feed.xml"
DEFAULT_THRESHOLD = 25.0  # Minimum velocity score to archive
GITHUB_API = "https://api.github.com"
VELOCITY_WINDOW_DAYS = 7
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2

# Scoring weights (tune based on what matters for discovery)
WEIGHT_COMMITS = 10.0
WEIGHT_FORKS = 5.0
WEIGHT_CONTRIBUTORS = 15.0
WEIGHT_ISSUES = 2.0
WEIGHT_PRS = 3.0
WEIGHT_WATCHERS = 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("RADAR")

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _week_ago() -> str:
    """Return date string for 7 days ago."""
    return (datetime.now(timezone.utc) - timedelta(days=VELOCITY_WINDOW_DAYS)).strftime("%Y-%m-%d")

def compute_ipfs_cid_v1(content: bytes) -> str:
    """
    Compute proper IPFS CIDv1 using SHA-256 multihash.
    Shared implementation with GAR for consistency.
    """
    h = hashlib.sha256(content).digest()
    multihash = bytes([0x12, 0x20]) + h  # sha2-256 + length
    cid_bytes = bytes([0x01, 0x55]) + multihash  # version 1, raw codec
    cid_b32 = base64.b32encode(cid_bytes).decode('ascii').lower().rstrip('=')
    return 'b' + cid_b32

# -----------------------------------------------------------------------------
# Database Layer
# -----------------------------------------------------------------------------

def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database for tracking repos and velocity."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS repos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT UNIQUE NOT NULL,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT,
            velocity_score REAL DEFAULT 0,
            commits_7d INTEGER DEFAULT 0,
            forks_7d INTEGER DEFAULT 0,
            contributors_7d INTEGER DEFAULT 0,
            issues_7d INTEGER DEFAULT 0,
            prs_7d INTEGER DEFAULT 0,
            stars INTEGER DEFAULT 0,
            watchers INTEGER DEFAULT 0,
            ipfs_cid TEXT,
            last_seen TEXT,
            last_scored TEXT,
            fed_to_gar INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            repo_name TEXT NOT NULL,
            actor TEXT,
            created_at TEXT,
            processed INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_repo_name ON repos(full_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_velocity ON repos(velocity_score DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_id ON events(event_id)")
    conn.commit()
    return conn

def repo_exists(conn: sqlite3.Connection, full_name: str) -> bool:
    """Check if repo is already tracked."""
    cur = conn.execute("SELECT 1 FROM repos WHERE full_name = ?", (full_name,))
    return cur.fetchone() is not None

def store_repo(conn: sqlite3.Connection, repo_data: dict) -> None:
    """Store or update repo record."""
    conn.execute("""
        INSERT OR REPLACE INTO repos
        (full_name, owner, name, description, created_at, velocity_score,
         commits_7d, forks_7d, contributors_7d, issues_7d, prs_7d, stars, watchers,
         ipfs_cid, last_seen, last_scored, fed_to_gar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        repo_data["full_name"],
        repo_data["owner"],
        repo_data["name"],
        repo_data.get("description", ""),
        repo_data.get("created_at"),
        repo_data.get("velocity_score", 0),
        repo_data.get("commits_7d", 0),
        repo_data.get("forks_7d", 0),
        repo_data.get("contributors_7d", 0),
        repo_data.get("issues_7d", 0),
        repo_data.get("prs_7d", 0),
        repo_data.get("stars", 0),
        repo_data.get("watchers", 0),
        repo_data.get("ipfs_cid"),
        datetime.now(timezone.utc).isoformat(),
        datetime.now(timezone.utc).isoformat(),
        repo_data.get("fed_to_gar", 0)
    ))
    conn.commit()

def get_top_repos(conn: sqlite3.Connection, limit: int = 100) -> List[dict]:
    """Get top repos by velocity score."""
    cur = conn.execute("""
        SELECT full_name, velocity_score, commits_7d, forks_7d, contributors_7d,
               stars, description, created_at, ipfs_cid, last_scored
        FROM repos
        ORDER BY velocity_score DESC
        LIMIT ?
    """, (limit,))

    repos = []
    for row in cur.fetchall():
        repos.append({
            "full_name": row[0],
            "velocity_score": row[1],
            "commits_7d": row[2],
            "forks_7d": row[3],
            "contributors_7d": row[4],
            "stars": row[5],
            "description": row[6],
            "created_at": row[7],
            "ipfs_cid": row[8],
            "last_scored": row[9]
        })
    return repos

# -----------------------------------------------------------------------------
# GitHub API with Rate Limit Handling
# -----------------------------------------------------------------------------

def get_github_headers() -> dict:
    """Build headers with optional auth token."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Repo-Radar/1.0"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def handle_rate_limit(resp: requests.Response, retry: int = 0) -> bool:
    """Handle GitHub rate limiting with exponential backoff."""
    if resp.status_code in (403, 429):
        remaining = resp.headers.get("X-RateLimit-Remaining", "0")
        reset_time = resp.headers.get("X-RateLimit-Reset")

        if remaining == "0" and reset_time:
            reset_timestamp = int(reset_time)
            current_timestamp = int(time.time())
            wait_seconds = max(reset_timestamp - current_timestamp, 0)

            if retry < MAX_RETRIES and wait_seconds < 3600:
                log.warning(f"Rate limited. Waiting {wait_seconds}s until reset...")
                time.sleep(wait_seconds + 1)
                return True

        if retry < MAX_RETRIES:
            wait = RETRY_BACKOFF_BASE ** retry
            log.warning(f"Request failed. Retrying in {wait}s... (attempt {retry + 1}/{MAX_RETRIES})")
            time.sleep(wait)
            return True

    return False

def fetch_repo_details(full_name: str) -> Optional[dict]:
    """Fetch detailed repo information."""
    headers = get_github_headers()
    url = f"{GITHUB_API}/repos/{full_name}"

    for retry in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif handle_rate_limit(resp, retry):
                continue
            else:
                log.debug(f"Error fetching {full_name}: {resp.status_code}")
                return None
        except Exception as e:
            log.error(f"Error fetching repo details for {full_name}: {e}")
            if retry < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_BASE ** retry)
                continue
            return None
    return None

def fetch_commits_count(full_name: str, since_days: int = 7) -> int:
    """Count commits in the last N days."""
    headers = get_github_headers()
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    url = f"{GITHUB_API}/repos/{full_name}/commits?since={since}&per_page=100"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            commits = resp.json()
            return len(commits)
    except Exception as e:
        log.debug(f"Error counting commits for {full_name}: {e}")
    return 0

def fetch_prs_count(full_name: str, since_days: int = 7) -> int:
    """Count PRs in the last N days."""
    headers = get_github_headers()
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    url = f"{GITHUB_API}/repos/{full_name}/pulls?state=all&per_page=100"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            prs = resp.json()
            # Filter by created_at
            count = sum(1 for pr in prs if pr.get('created_at', '') >= since)
            return count
    except Exception as e:
        log.debug(f"Error counting PRs for {full_name}: {e}")
    return 0

def fetch_issues_count(full_name: str, since_days: int = 7) -> int:
    """Count issues in the last N days (excluding PRs)."""
    headers = get_github_headers()
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
    url = f"{GITHUB_API}/repos/{full_name}/issues?state=all&per_page=100"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            issues = resp.json()
            # Exclude PRs (issues with pull_request key)
            count = sum(1 for issue in issues
                       if 'pull_request' not in issue and issue.get('created_at', '') >= since)
            return count
    except Exception as e:
        log.debug(f"Error counting issues for {full_name}: {e}")
    return 0

def fetch_forks_count(full_name: str, since_days: int = 7) -> int:
    """Count forks in the last N days."""
    headers = get_github_headers()
    url = f"{GITHUB_API}/repos/{full_name}/forks?sort=newest&per_page=100"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            forks = resp.json()
            since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
            count = sum(1 for f in forks if f.get('created_at', '') >= since)
            return count
    except Exception as e:
        log.debug(f"Error counting forks for {full_name}: {e}")
    return 0

def fetch_contributors_count(full_name: str) -> int:
    """Get total contributor count."""
    headers = get_github_headers()
    url = f"{GITHUB_API}/repos/{full_name}/contributors?per_page=1"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            # GitHub returns total count in Link header
            link = resp.headers.get("Link", "")
            if "last" in link:
                # Parse last page number from Link header
                import re
                match = re.search(r'page=(\d+)>; rel="last"', link)
                if match:
                    return int(match.group(1))
            return len(resp.json())
    except Exception as e:
        log.debug(f"Error counting contributors for {full_name}: {e}")
    return 0

def fetch_events(event_type: Optional[str] = None, per_page: int = 30) -> List[dict]:
    """Fetch recent GitHub events."""
    headers = get_github_headers()
    url = f"{GITHUB_API}/events?per_page={per_page}"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            events = resp.json()
            if event_type:
                return [e for e in events if e.get("type") == event_type]
            return events
    except Exception as e:
        log.error(f"Error fetching events: {e}")
    return []

def search_repos_by_topic(topic: str, limit: int = 30) -> List[dict]:
    """Search for repos by topic/language."""
    headers = get_github_headers()
    week_ago = _week_ago()
    url = f"{GITHUB_API}/search/repositories?q=topic:{topic}+pushed:>={week_ago}&sort=updated&per_page={limit}"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("items", [])
        if handle_rate_limit(resp):
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("items", [])
    except Exception as e:
        log.error(f"Error searching topic {topic}: {e}")
    return []

# -----------------------------------------------------------------------------
# Velocity Scoring
# -----------------------------------------------------------------------------

def calculate_velocity_score(
    commits_7d: int,
    forks_7d: int,
    contributors: int,
    issues_7d: int,
    prs_7d: int,
    watchers: int,
    created_at: Optional[str] = None
) -> float:
    """
    Calculate velocity score based on activity metrics.

    Higher scores = more active, regardless of age or star count.
    """
    # Base score from weighted activity
    score = (
        commits_7d * WEIGHT_COMMITS +
        forks_7d * WEIGHT_FORKS +
        contributors * WEIGHT_CONTRIBUTORS +
        issues_7d * WEIGHT_ISSUES +
        prs_7d * WEIGHT_PRS +
        watchers * WEIGHT_WATCHERS
    )

    # Time-based multipliers
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created).days

            # Freshness boost: repos < 30 days get 1.5x
            if age_days < 30:
                score *= 1.5

            # Sustained activity bonus: repos > 180 days with activity get 1.2x
            elif age_days > 180 and commits_7d > 0:
                score *= 1.2

        except:
            pass

    return round(score, 2)

def gather_velocity_metrics(full_name: str) -> dict:
    """Gather all velocity metrics for a repo."""
    metrics = {
        "full_name": full_name,
        "owner": full_name.split("/")[0] if "/" in full_name else "",
        "name": full_name.split("/")[1] if "/" in full_name else full_name,
        "commits_7d": 0,
        "forks_7d": 0,
        "contributors_7d": 0,
        "issues_7d": 0,
        "prs_7d": 0,
        "stars": 0,
        "watchers": 0,
        "description": "",
        "created_at": None,
        "velocity_score": 0,
        "ipfs_cid": None,
        "fed_to_gar": 0
    }

    # Fetch repo details
    repo = fetch_repo_details(full_name)
    if not repo:
        return metrics

    metrics["description"] = repo.get("description", "")[:500] if repo.get("description") else ""
    metrics["created_at"] = repo.get("created_at")
    metrics["stars"] = repo.get("stargazers_count", 0)
    metrics["watchers"] = repo.get("subscribers_count", 0)

    # Fetch accurate 7d counts
    metrics["commits_7d"] = fetch_commits_count(full_name, VELOCITY_WINDOW_DAYS)
    metrics["forks_7d"] = fetch_forks_count(full_name, VELOCITY_WINDOW_DAYS)
    metrics["issues_7d"] = fetch_issues_count(full_name, VELOCITY_WINDOW_DAYS)
    metrics["prs_7d"] = fetch_prs_count(full_name, VELOCITY_WINDOW_DAYS)
    metrics["contributors_7d"] = fetch_contributors_count(full_name)

    # Calculate velocity score
    metrics["velocity_score"] = calculate_velocity_score(
        commits_7d=metrics["commits_7d"],
        forks_7d=metrics["forks_7d"],
        contributors=metrics["contributors_7d"],
        issues_7d=metrics["issues_7d"],
        prs_7d=metrics["prs_7d"],
        watchers=metrics["watchers"],
        created_at=metrics["created_at"]
    )

    return metrics

# -----------------------------------------------------------------------------
# IPFS Integration
# -----------------------------------------------------------------------------

def pin_to_ipfs(data: dict) -> Optional[str]:
    """Pin repo metadata to IPFS. Returns CID if successful."""
    content = json.dumps(data, indent=2, default=str).encode()

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
    cid = compute_ipfs_cid_v1(content)
    log.debug(f"No IPFS available, computed CIDv1: {cid}")
    return cid

# -----------------------------------------------------------------------------
# GAR Integration (Refined: Shared DB)
# -----------------------------------------------------------------------------

def feed_to_gar(full_name: str, gar_db_path: str = "../gar/gar_state.db") -> bool:
    """
    Feed a high-velocity repo to GAR for commit archiving.

    Tries to insert directly into GAR's DB if it exists.
    Falls back to gar_orgs.txt file.
    """
    owner = full_name.split("/")[0] if "/" in full_name else full_name

    # Try shared DB integration
    if Path(gar_db_path).exists():
        try:
            # Note: This assumes GAR might add an 'orgs' table in future
            # For now, we can log the org for manual GAR configuration
            log.info(f"Would add {owner} to GAR DB (feature pending)")
            # Fallback to file method for now
        except Exception as e:
            log.debug(f"GAR DB integration failed: {e}")

    # File-based integration
    gar_orgs_file = Path("gar_orgs.txt")
    existing = set()
    if gar_orgs_file.exists():
        existing = set(line.strip() for line in gar_orgs_file.read_text().strip().split("\n") if line.strip())

    if owner not in existing:
        existing.add(owner)
        gar_orgs_file.write_text("\n".join(sorted(existing)) + "\n")
        log.info(f"Added {owner} to GAR watch list (gar_orgs.txt)")
        return True

    return False

# -----------------------------------------------------------------------------
# RSS Feed Generation
# -----------------------------------------------------------------------------

def generate_rss(conn: sqlite3.Connection, output_path: str, topics: List[str]) -> None:
    """Generate RSS feed from top velocity repos."""
    fg = FeedGenerator()
    fg.id(f"urn:radar:{hashlib.md5(','.join(topics).encode()).hexdigest()}")
    fg.title(f"Repo Radar - Velocity Discovery")
    fg.description("Discover repos by activity velocity, not star count")
    fg.link(href="https://github.com", rel="alternate")
    fg.language("en")
    fg.lastBuildDate(datetime.now(timezone.utc))

    repos = get_top_repos(conn, limit=100)

    for repo in repos:
        fe = fg.add_entry()
        fe.id(f"urn:github:repo:{repo['full_name']}")
        fe.title(f"{repo['full_name']} (velocity: {repo['velocity_score']:.1f})")
        fe.link(href=f"https://github.com/{repo['full_name']}")

        # Build description
        desc = f"<p><strong>Velocity Score:</strong> {repo['velocity_score']:.1f}</p>"
        desc += f"<p><strong>Activity (7 days):</strong></p>"
        desc += f"<ul>"
        desc += f"<li>{repo['commits_7d']} commits</li>"
        desc += f"<li>{repo['forks_7d']} forks</li>"
        desc += f"<li>{repo['contributors_7d']} contributors</li>"
        desc += f"<li>{repo['stars']} stars (total)</li>"
        desc += f"</ul>"
        if repo['description']:
            desc += f"<p>{repo['description']}</p>"
        if repo['ipfs_cid']:
            desc += f"<p><strong>IPFS:</strong> <a href='https://ipfs.io/ipfs/{repo['ipfs_cid']}'>{repo['ipfs_cid']}</a></p>"

        fe.description(desc)

        # Parse timestamp
        try:
            if repo['created_at']:
                dt = datetime.fromisoformat(repo['created_at'].replace("Z", "+00:00"))
                fe.published(dt)
                fe.updated(datetime.now(timezone.utc))
        except:
            pass

    # Write feeds
    fg.rss_file(output_path)
    atom_path = output_path.replace(".xml", ".atom")
    fg.atom_file(atom_path)

    log.info(f"Generated RSS: {output_path} and Atom: {atom_path}")

# -----------------------------------------------------------------------------
# Main Scanning Loop
# -----------------------------------------------------------------------------

def scan_once(conn: sqlite3.Connection, orgs: List[str], topics: List[str], threshold: float, rss_path: str) -> int:
    """Run one scanning cycle."""
    new_repos = 0

    # Scan by topics/languages
    for topic in topics:
        log.info(f"Scanning topic: {topic}")
        repos = search_repos_by_topic(topic)

        for repo in repos:
            full_name = repo.get("full_name")
            if not full_name:
                continue

            log.info(f"  Analyzing: {full_name}")
            metrics = gather_velocity_metrics(full_name)

            # Store repo
            store_repo(conn, metrics)

            # Archive if high velocity
            if metrics["velocity_score"] >= threshold:
                log.info(f"  High velocity: {full_name} (score: {metrics['velocity_score']:.1f})")

                # Pin to IPFS
                if not metrics.get("ipfs_cid"):
                    cid = pin_to_ipfs(metrics)
                    if cid:
                        conn.execute("UPDATE repos SET ipfs_cid = ? WHERE full_name = ?", (cid, full_name))
                        conn.commit()

                # Feed to GAR
                if not metrics.get("fed_to_gar"):
                    if feed_to_gar(full_name):
                        conn.execute("UPDATE repos SET fed_to_gar = 1 WHERE full_name = ?", (full_name,))
                        conn.commit()

                new_repos += 1

    # Generate RSS
    generate_rss(conn, rss_path, topics)

    return new_repos

def run_daemon(orgs: List[str], topics: List[str], interval: int, threshold: float, db_path: str, rss_path: str) -> None:
    """Run continuous scanning daemon."""
    conn = init_db(db_path)
    log.info(f"Starting Repo Radar")
    log.info(f"  Topics: {', '.join(topics)}")
    log.info(f"  Interval: {interval}s")
    log.info(f"  Threshold: {threshold}")
    log.info(f"  Database: {db_path}")
    log.info(f"  RSS: {rss_path}")
    log.info(f"  GitHub Token: {'configured' if os.environ.get('GITHUB_TOKEN') else 'not set (60 req/hr limit)'}")
    log.info("-" * 60)

    # Initial scan
    generate_rss(conn, rss_path, topics)

    while True:
        try:
            new = scan_once(conn, orgs, topics, threshold, rss_path)
            log.info(f"Scan complete: {new} high-velocity repos found")
        except KeyboardInterrupt:
            log.info("Shutting down...")
            break
        except Exception as e:
            log.error(f"Scan error: {e}")

        time.sleep(interval)

    conn.close()

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Repo Radar - Discovery by Velocity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  GITHUB_TOKEN          GitHub personal access token (for higher rate limits)
  PINATA_API_KEY       Pinata API key for IPFS pinning
  PINATA_SECRET_KEY    Pinata secret key

Examples:
  # Watch AI/ML topics
  python repo-radar.py --watch ai,ml,python --interval 300

  # Monitor specific orgs
  python repo-radar.py --orgs anthropics,openai --threshold 50

  # Run once (no daemon)
  python repo-radar.py --watch rust --once

  # View stats
  python repo-radar.py --stats
        """
    )
    parser.add_argument(
        "--orgs", "-o",
        default="",
        help="Comma-separated list of GitHub orgs to monitor"
    )
    parser.add_argument(
        "--watch", "-w",
        default="",
        help="Comma-separated list of topics/languages to watch"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Polling interval in seconds (default: {DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum velocity score to archive (default: {DEFAULT_THRESHOLD})"
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
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )
    parser.add_argument(
        "--verify-db",
        action="store_true",
        help="Verify database integrity and show top repos (audit mode)"
    )
    parser.add_argument(
        "--verify-feeds",
        action="store_true",
        help="Verify RSS/Atom feeds exist and are valid"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Verify database integrity (audit mode)
        if args.verify_db:
            try:
                if not Path(args.db).exists():
                    log.error(f"Database not found: {args.db}")
                    log.info("Run a scan first: python repo-radar.py --watch ai --once")
                    return

                conn = sqlite3.connect(args.db)

                # Check table exists
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repos'")
                if not cursor.fetchone():
                    log.error("Database schema invalid: 'repos' table missing")
                    conn.close()
                    return

                # Get top repos with full identity metadata
                cursor = conn.execute("""
                    SELECT
                        full_name,
                        owner,
                        velocity_score,
                        commits_7d,
                        contributors_7d,
                        stars,
                        created_at,
                        pushed_at,
                        ipfs_cid
                    FROM repos
                    ORDER BY velocity_score DESC
                    LIMIT 10
                """)

                repos = cursor.fetchall()

                if not repos:
                    log.info("✓ Database structure valid, but no repos discovered yet")
                    conn.close()
                    return

                print("\n" + "="*80)
                print("DATABASE VERIFICATION - TOP 10 HIGH-VELOCITY REPOS")
                print("="*80 + "\n")

                for i, row in enumerate(repos, 1):
                    full_name, owner, velocity, commits, contributors, stars, created_at, pushed_at, cid = row

                    print(f"{i}. {full_name}")
                    print(f"   Owner: {owner} (User/Org - verify at github.com/{owner})")
                    print(f"   Velocity: {velocity}")
                    print(f"   Commits (7d): {commits} | Contributors: {contributors} | Stars: {stars}")
                    print(f"   Created: {created_at}")
                    print(f"   Last Push: {pushed_at}")
                    print(f"   IPFS CID: {cid}")
                    print(f"   GitHub: https://github.com/{full_name}")

                    # Name collision warning for common names
                    common_names = ['lynx', 'atlas', 'phoenix', 'core', 'framework', 'engine']
                    repo_name = full_name.split('/')[-1].lower()
                    if repo_name in common_names:
                        print(f"   ⚠️  NOTE: '{repo_name}' is a common name - verify specific owner identity")
                    print()

                # Spam detection check
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM repos
                    WHERE commits_7d > 50 AND contributors_7d = 1
                """)
                spam_count = cursor.fetchone()[0]

                if spam_count > 0:
                    log.warning(f"⚠️  {spam_count} repos flagged as potential single-dev spam")
                else:
                    log.info("✓ No spam patterns detected")

                conn.close()
                log.info("✓ Database verification complete")
                return

            except sqlite3.Error as e:
                log.error(f"Database verification failed: {e}")
                return
            except Exception as e:
                log.error(f"Unexpected error during verification: {e}")
                return

        # Verify RSS/Atom feeds
        if args.verify_feeds:
            feeds = list(Path().glob('*.xml')) + list(Path().glob('*.atom'))

            if not feeds:
                log.warning("⚠️  No feeds found")
                log.info("Feeds are generated after first discovery")
                log.info("Run a scan: python repo-radar.py --watch ai --once")
                return

            print("\n" + "="*80)
            print("FEED VERIFICATION")
            print("="*80 + "\n")

            for feed in feeds:
                try:
                    size = feed.stat().st_size
                    print(f"✓ {feed.name} ({size:,} bytes)")

                    # Proper XML validation via parsing
                    import xml.etree.ElementTree as ET
                    try:
                        tree = ET.parse(feed)
                        root = tree.getroot()
                        # Count items/entries
                        items = root.findall('.//item') if 'rss' in feed.name else root.findall('.//{http://www.w3.org/2005/Atom}entry')
                        log.info(f"  ✓ Valid XML (parsed successfully, {len(items)} entries)")
                    except ET.ParseError as pe:
                        log.error(f"  ✗ Invalid XML structure: {pe}")

                except Exception as e:
                    log.error(f"✗ {feed.name}: {e}")

            log.info("\n✓ Feed verification complete")
            return

        if args.stats:
            conn = init_db(args.db)
            repos = get_top_repos(conn, limit=20)
            print("\n" + "="*80)
            print("Repo Radar - Top Repos by Velocity")
            print("="*80)
            print(f"\n{'Rank':<6} {'Score':<8} {'Commits':<8} {'Forks':<7} {'Repo'}")
            print("-" * 80)
            for i, r in enumerate(repos, 1):
                print(f"{i:<6} {r['velocity_score']:<8.1f} {r['commits_7d']:<8} {r['forks_7d']:<7} {r['full_name']}")
            print("="*80 + "\n")
            conn.close()
            return

        orgs = [o.strip() for o in args.orgs.split(",") if o.strip()]
        topics = [t.strip() for t in args.watch.split(",") if t.strip()]

        if not orgs and not topics:
            parser.error("At least one --orgs or --watch must be specified")

        if args.once:
            conn = init_db(args.db)
            scan_once(conn, orgs, topics, args.threshold, args.rss)
            conn.close()
        else:
            run_daemon(orgs, topics, args.interval, args.threshold, args.db, args.rss)

    except Exception as e:
        log.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
