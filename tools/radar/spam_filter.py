#!/usr/bin/env python3
"""
Spam Filter for Repo Radar - Adversarial Resilience Layer
----------------------------------------------------------
Multi-signal detection to separate genuine velocity from coordinated noise.

Design Philosophy:
- Filter for usability, archive everything for evidence
- Assume 80% incentive-driven noise, 20% potential adversarial probe
- The spam itself is data about what threatens gatekeepers

Signals:
1. Keyword blocklist (explicit bad-actor language)
2. Description pattern matching (crypto spam fingerprints)
3. Owner concentration (same actor, many repos)
4. Velocity anomaly detection (suspiciously uniform scores)
5. Name pattern detection (SEO-stuffed repo names)

Author: Temple Tools / HTCA Project
License: MIT
"""

import re
import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("SPAM_FILTER")

# -----------------------------------------------------------------------------
# Blocklists and Patterns
# -----------------------------------------------------------------------------

# Hard blocklist - repos matching these are almost certainly spam/malicious
KEYWORD_BLOCKLIST = {
    # Explicit malicious intent
    "bypass", "unauthorized", "tricking", "exploit", "crack", "keygen",
    "hack tool", "brute force", "credential", "phishing",

    # Deepfake/identity fraud
    "deepfake", "face swap", "id verification bypass", "2fa bypass",
    "biometric bypass",

    # Crypto spam signatures
    "airdrop bot", "airdrop farming", "airdrop automation",
    "arbitrage bot deployer", "flash loan attack",
    "pump and dump", "rug pull",

    # Wallet spam (fake SDKs)
    "wallet connect sdk", "metamask sdk", "phantom sdk",
    "coinbase wallet api", "trust wallet sdk",

    # Crypto spam in repo names (case-insensitive matching)
    "wallet-connect", "walletconnect",
    "multi-crypto", "multicrypto",
    "web3-ethereum", "web3-solana",
    "crypto-payment", "blockchain-network",
    "passive income", "renda passiva",
    "income generator", "gerador renda",
}

# Additional repo name patterns that indicate spam
SPAM_NAME_KEYWORDS = {
    "airdrop", "wallet-connect", "metamask-wallet", "phantom-wallet",
    "coinbase-wallet", "trust-wallet", "web3-sdk", "web3-api",
    "blockchain-plugin", "crypto-payment", "defi-arbitrage",
    "income-generator", "passive-income",
}

# Soft signals - raise suspicion but don't hard-block
SUSPICIOUS_PATTERNS = [
    r"passive income.*blockchain",
    r"automated.*trading.*bot",
    r"crypto.*payment.*gateway",
    r"wallet.*storage.*multi.*crypto",
    r"testnet.*bot",
    r"faucet.*automation",
    r"token.*generator",
    r"\bbot\b.*\bairdrop\b",
    r"defi.*arbitrage",
]

# SEO-stuffed name patterns (keyword-crammed repo names)
SEO_NAME_PATTERNS = [
    r"-[A-Z][a-z]+-[A-Z][a-z]+-[A-Z][a-z]+-[A-Z][a-z]+",  # Multiple-Capitalized-Words-Chained
    r"(Wallet|Crypto|Bot|Api|Sdk|Web3|Blockchain|Defi){3,}",  # Keyword stuffing
    r".{60,}",  # Absurdly long repo names
]

# Known spam actors (add as discovered)
KNOWN_SPAM_OWNERS = {
    "frankrichardhall",  # 12 airdrop bots at identical velocity
    # Add more as patterns emerge
}

# -----------------------------------------------------------------------------
# Data Structures
# -----------------------------------------------------------------------------

@dataclass
class SpamSignal:
    """Individual spam detection signal."""
    signal_type: str
    severity: float  # 0.0 to 1.0
    detail: str

@dataclass
class SpamVerdict:
    """Complete spam analysis for a repo."""
    full_name: str
    velocity_score: float
    is_spam: bool
    spam_probability: float  # 0.0 to 1.0
    signals: List[SpamSignal]
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "velocity_score": self.velocity_score,
            "is_spam": self.is_spam,
            "spam_probability": self.spam_probability,
            "signals": [asdict(s) for s in self.signals],
            "timestamp": self.timestamp,
        }

# -----------------------------------------------------------------------------
# Detection Functions
# -----------------------------------------------------------------------------

def check_keyword_blocklist(description: str, full_name: str) -> Optional[SpamSignal]:
    """Check for hard-blocked keywords."""
    text = f"{description} {full_name}".lower()
    for keyword in KEYWORD_BLOCKLIST:
        if keyword in text:
            return SpamSignal(
                signal_type="keyword_blocklist",
                severity=1.0,
                detail=f"Contains blocked keyword: '{keyword}'"
            )
    return None

def check_spam_name_keywords(full_name: str) -> Optional[SpamSignal]:
    """Check for spam keywords in repo name."""
    repo_name = full_name.split("/")[-1].lower() if "/" in full_name else full_name.lower()
    for keyword in SPAM_NAME_KEYWORDS:
        if keyword in repo_name:
            return SpamSignal(
                signal_type="spam_name_keyword",
                severity=0.85,
                detail=f"Repo name contains spam keyword: '{keyword}'"
            )
    return None

def check_suspicious_patterns(description: str) -> List[SpamSignal]:
    """Check for soft suspicious patterns in description."""
    signals = []
    desc_lower = description.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, desc_lower, re.IGNORECASE):
            signals.append(SpamSignal(
                signal_type="suspicious_pattern",
                severity=0.6,
                detail=f"Matches suspicious pattern: {pattern}"
            ))
    return signals

def check_seo_name(full_name: str) -> Optional[SpamSignal]:
    """Check for SEO-stuffed repo names."""
    repo_name = full_name.split("/")[-1] if "/" in full_name else full_name
    for pattern in SEO_NAME_PATTERNS:
        if re.search(pattern, repo_name):
            return SpamSignal(
                signal_type="seo_name",
                severity=0.7,
                detail=f"Repo name appears SEO-stuffed: {repo_name}"
            )
    return None

def check_known_spam_owner(full_name: str) -> Optional[SpamSignal]:
    """Check if owner is in known spam list."""
    owner = full_name.split("/")[0] if "/" in full_name else ""
    if owner.lower() in {o.lower() for o in KNOWN_SPAM_OWNERS}:
        return SpamSignal(
            signal_type="known_spam_owner",
            severity=0.9,
            detail=f"Owner '{owner}' is flagged as known spam actor"
        )
    return None

def check_owner_concentration(full_name: str, db_path: str, threshold: int = 5) -> Optional[SpamSignal]:
    """Check if owner has suspiciously many high-velocity repos."""
    owner = full_name.split("/")[0] if "/" in full_name else ""
    if not owner:
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE full_name LIKE ? AND velocity_score > 500",
            (f"{owner}/%",)
        )
        count = cursor.fetchone()[0]
        conn.close()

        if count >= threshold:
            return SpamSignal(
                signal_type="owner_concentration",
                severity=min(0.5 + (count - threshold) * 0.1, 0.95),
                detail=f"Owner has {count} high-velocity repos (threshold: {threshold})"
            )
    except Exception as e:
        log.warning(f"DB check failed for owner concentration: {e}")

    return None

def check_velocity_clustering(velocity_score: float, db_path: str, tolerance: float = 5.0) -> Optional[SpamSignal]:
    """Check if velocity score clusters suspiciously with many others."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM repos WHERE ABS(velocity_score - ?) < ?",
            (velocity_score, tolerance)
        )
        count = cursor.fetchone()[0]
        conn.close()

        if count >= 5:  # 5+ repos at nearly identical velocity is suspicious
            return SpamSignal(
                signal_type="velocity_clustering",
                severity=min(0.4 + count * 0.05, 0.8),
                detail=f"{count} repos have velocity within {tolerance} of {velocity_score}"
            )
    except Exception as e:
        log.warning(f"DB check failed for velocity clustering: {e}")

    return None

# -----------------------------------------------------------------------------
# Main Analysis
# -----------------------------------------------------------------------------

def analyze_repo(
    full_name: str,
    velocity_score: float,
    description: str,
    db_path: str = "radar_state.db",
    spam_threshold: float = 0.7
) -> SpamVerdict:
    """
    Analyze a repo for spam signals and return verdict.

    Args:
        full_name: owner/repo format
        velocity_score: calculated velocity
        description: repo description
        db_path: path to radar state database
        spam_threshold: probability above which repo is marked spam

    Returns:
        SpamVerdict with analysis results
    """
    signals: List[SpamSignal] = []
    description = description or ""

    # Run all checks
    if sig := check_keyword_blocklist(description, full_name):
        signals.append(sig)

    signals.extend(check_suspicious_patterns(description))

    if sig := check_seo_name(full_name):
        signals.append(sig)

    if sig := check_spam_name_keywords(full_name):
        signals.append(sig)

    if sig := check_known_spam_owner(full_name):
        signals.append(sig)

    if sig := check_owner_concentration(full_name, db_path):
        signals.append(sig)

    if sig := check_velocity_clustering(velocity_score, db_path):
        signals.append(sig)

    # Calculate spam probability
    if not signals:
        spam_probability = 0.0
    else:
        # Weighted combination - hard blocks dominate
        max_severity = max(s.severity for s in signals)
        avg_severity = sum(s.severity for s in signals) / len(signals)
        spam_probability = 0.7 * max_severity + 0.3 * avg_severity

    return SpamVerdict(
        full_name=full_name,
        velocity_score=velocity_score,
        is_spam=spam_probability >= spam_threshold,
        spam_probability=round(spam_probability, 3),
        signals=signals,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

def analyze_database(
    db_path: str = "radar_state.db",
    spam_threshold: float = 0.7
) -> Tuple[List[SpamVerdict], List[SpamVerdict]]:
    """
    Analyze all repos in database.

    Returns:
        (clean_repos, spam_repos) tuple of verdict lists
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT full_name, velocity_score, description FROM repos")
    rows = cursor.fetchall()
    conn.close()

    clean = []
    spam = []

    for full_name, velocity, description in rows:
        verdict = analyze_repo(full_name, velocity, description or "", db_path, spam_threshold)
        if verdict.is_spam:
            spam.append(verdict)
        else:
            clean.append(verdict)

    log.info(f"Analysis complete: {len(clean)} clean, {len(spam)} spam")
    return clean, spam

def generate_report(
    clean: List[SpamVerdict],
    spam: List[SpamVerdict],
    output_path: str = "spam_analysis_report.json"
) -> dict:
    """Generate comprehensive spam analysis report."""

    # Signal frequency analysis
    signal_counts = {}
    for verdict in spam:
        for sig in verdict.signals:
            signal_counts[sig.signal_type] = signal_counts.get(sig.signal_type, 0) + 1

    # Owner analysis
    spam_owners = {}
    for verdict in spam:
        owner = verdict.full_name.split("/")[0]
        spam_owners[owner] = spam_owners.get(owner, 0) + 1
    top_spam_owners = sorted(spam_owners.items(), key=lambda x: -x[1])[:10]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_repos": len(clean) + len(spam),
            "clean_repos": len(clean),
            "spam_repos": len(spam),
            "spam_percentage": round(100 * len(spam) / (len(clean) + len(spam)), 1) if clean or spam else 0,
        },
        "signal_frequency": signal_counts,
        "top_spam_owners": top_spam_owners,
        "spam_repos": [v.to_dict() for v in sorted(spam, key=lambda x: -x.spam_probability)],
        "borderline_clean": [
            v.to_dict() for v in clean
            if v.spam_probability > 0.3
        ][:20],  # Clean but suspicious
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    log.info(f"Report saved to {output_path}")
    return report

# -----------------------------------------------------------------------------
# CLI Interface
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Repo Radar database for spam")
    parser.add_argument("--db", default="radar_state.db", help="Path to radar database")
    parser.add_argument("--threshold", type=float, default=0.7, help="Spam probability threshold")
    parser.add_argument("--report", default="spam_analysis_report.json", help="Output report path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    print("=" * 70)
    print("Repo Radar Spam Analysis - Adversarial Resilience Layer")
    print("=" * 70)

    clean, spam = analyze_database(args.db, args.threshold)
    report = generate_report(clean, spam, args.report)

    print(f"\nSummary:")
    print(f"  Total repos:  {report['summary']['total_repos']}")
    print(f"  Clean:        {report['summary']['clean_repos']}")
    print(f"  Spam:         {report['summary']['spam_repos']} ({report['summary']['spam_percentage']}%)")

    print(f"\nSignal Frequency:")
    for sig, count in sorted(report['signal_frequency'].items(), key=lambda x: -x[1]):
        print(f"  {sig}: {count}")

    print(f"\nTop Spam Owners:")
    for owner, count in report['top_spam_owners'][:5]:
        print(f"  {owner}: {count} repos")

    if args.verbose and spam:
        print(f"\nSpam Repos (top 10):")
        for v in spam[:10]:
            print(f"  [{v.spam_probability:.0%}] {v.full_name}")
            for sig in v.signals:
                print(f"       └─ {sig.signal_type}: {sig.detail}")

    print(f"\nFull report: {args.report}")
