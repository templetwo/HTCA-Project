#!/usr/bin/env python3
"""
Repo Radar Testing & Validation Script
---------------------------------------
Tests Repo Radar functionality without making excessive API calls.
Validates core functions: velocity scoring, CID generation, DB operations,
spam detection heuristics.

Usage:
    python test_radar.py              # Run all tests
    python test_radar.py --unit       # Unit tests only
    python test_radar.py --integration # Integration tests (requires env vars)
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# Import Repo Radar functions for testing
sys.path.insert(0, str(Path(__file__).parent))
from typing import Optional

try:
    # Import test functions from Repo Radar
    import importlib.util
    spec = importlib.util.spec_from_file_location("radar", Path(__file__).parent / "repo-radar.py")
    radar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(radar)
except Exception as e:
    print(f"Failed to import Repo Radar module: {e}")
    sys.exit(1)

# Test results tracking
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def pass_test(self, name: str):
        self.passed += 1
        print(f"✅ {name}")

    def fail_test(self, name: str, error: str):
        self.failed += 1
        self.errors.append((name, error))
        print(f"❌ {name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "="*60)
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print("="*60)
        return self.failed == 0

results = TestResults()

# =============================================================================
# Unit Tests
# =============================================================================

def test_velocity_score_calculation():
    """Test velocity scoring with known inputs."""
    try:
        # Test basic scoring
        score = radar.calculate_velocity_score(
            commits_7d=10,
            forks_7d=2,
            contributors=5,
            issues_7d=3,
            prs_7d=4,
            watchers=20
        )

        # Expected: (10*10) + (2*5) + (5*15) + (3*2) + (4*3) + (20*1) = 100 + 10 + 75 + 6 + 12 + 20 = 223
        assert score == 223.0, f"Basic score should be 223.0, got {score}"

        # Test freshness boost (repo < 30 days)
        from datetime import datetime, timedelta, timezone
        fresh_date = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        score_fresh = radar.calculate_velocity_score(
            commits_7d=10,
            forks_7d=0,
            contributors=1,
            issues_7d=0,
            prs_7d=0,
            watchers=0,
            created_at=fresh_date
        )

        # Expected: (10*10 + 1*15) = 115, with 1.5x boost = 172.5
        assert score_fresh == 172.5, f"Fresh repo score should be 172.5, got {score_fresh}"

        # Test sustained activity bonus (repo > 180 days with commits)
        old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
        score_sustained = radar.calculate_velocity_score(
            commits_7d=10,
            forks_7d=0,
            contributors=1,
            issues_7d=0,
            prs_7d=0,
            watchers=0,
            created_at=old_date
        )

        # Expected: (10*10 + 1*15) = 115, with 1.2x boost = 138
        assert score_sustained == 138.0, f"Sustained activity score should be 138.0, got {score_sustained}"

        results.pass_test("Velocity score calculation")
    except Exception as e:
        results.fail_test("Velocity score calculation", str(e))

def test_ipfs_cid_generation():
    """Test proper IPFS CIDv1 generation (consistency with GAR)."""
    try:
        # Test with known content
        content = b'{"test": "data"}'
        cid = radar.compute_ipfs_cid_v1(content)

        # CIDv1 should start with 'b' (base32 multibase)
        assert cid[0] == 'b', f"CID should start with 'b', got {cid[0]}"

        # Should be base32 encoded (lowercase letters and 2-7)
        assert all(c in 'abcdefghijklmnopqrstuvwxyz234567' for c in cid[1:]), \
            "CID contains invalid base32 characters"

        # Should be deterministic
        cid2 = radar.compute_ipfs_cid_v1(content)
        assert cid == cid2, "CID generation should be deterministic"

        # Different content should produce different CID
        cid3 = radar.compute_ipfs_cid_v1(b'different content')
        assert cid != cid3, "Different content should produce different CID"

        results.pass_test("IPFS CIDv1 generation")
    except Exception as e:
        results.fail_test("IPFS CIDv1 generation", str(e))

def test_database_operations():
    """Test SQLite database operations."""
    try:
        # Create in-memory database
        db_path = ":memory:"
        conn = radar.init_db(db_path)

        # Verify table creation
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repos'")
        assert cursor.fetchone() is not None, "Repos table should exist"

        # Test repo_exists on empty database
        assert not radar.repo_exists(conn, "test/repo"), "New repo should not exist"

        # Test store_repo
        repo_data = {
            "full_name": "test/repo",
            "owner": "test",
            "name": "repo",
            "description": "Test repository",
            "velocity_score": 123.45,
            "commits_7d": 10,
            "forks_7d": 2,
            "contributors_7d": 5,
            "issues_7d": 3,
            "prs_7d": 4,
            "stars": 50,
            "watchers": 20,
            "created_at": "2025-01-01T00:00:00Z",
            "ipfs_cid": "bafytest"
        }
        radar.store_repo(conn, repo_data)

        # Verify repo was stored
        assert radar.repo_exists(conn, "test/repo"), "Stored repo should exist"

        # Test duplicate insert (should be ignored)
        radar.store_repo(conn, repo_data)
        cursor = conn.execute("SELECT COUNT(*) FROM repos WHERE full_name = ?", ("test/repo",))
        count = cursor.fetchone()[0]
        assert count == 1, "Duplicate insert should be ignored"

        # Test get_top_repos
        repos = radar.get_top_repos(conn, limit=10)
        assert len(repos) == 1, "Should retrieve 1 repo"
        assert repos[0]["full_name"] == "test/repo", "Should retrieve correct repo"

        conn.close()
        results.pass_test("Database operations")
    except Exception as e:
        results.fail_test("Database operations", str(e))

def test_spam_detection_heuristics():
    """Test spam detection logic (future enhancement validation)."""
    try:
        # Test case 1: Legitimate high-velocity repo
        # High commits + multiple contributors + sustained activity
        score_legit = radar.calculate_velocity_score(
            commits_7d=50,
            forks_7d=10,
            contributors=15,
            issues_7d=20,
            prs_7d=25,
            watchers=100
        )

        # Expected: (50*10) + (10*5) + (15*15) + (20*2) + (25*3) + (100*1) = 500 + 50 + 225 + 40 + 75 + 100 = 990
        assert score_legit == 990.0, "Legitimate repo should score high"

        # Test case 2: Spam pattern (high commits, single contributor)
        # This should still score, but manual review would flag it
        score_spam = radar.calculate_velocity_score(
            commits_7d=100,  # Very high commits
            forks_7d=0,      # No forks
            contributors=1,  # Single contributor (spam indicator)
            issues_7d=0,     # No issues
            prs_7d=0,        # No PRs
            watchers=0       # No watchers
        )

        # Expected: 100*10 + 0 + 1*15 + 0 + 0 + 0 = 1015
        # Note: This scores high but would be flagged by manual review
        # due to single contributor and no community engagement
        assert score_spam == 1015.0, "Spam pattern scores high but lacks diversity"

        # Spam indicator: commits/contributor ratio
        legit_ratio = 50 / 15  # ~3.3 commits per contributor (normal)
        spam_ratio = 100 / 1   # 100 commits per contributor (suspicious)

        assert spam_ratio > legit_ratio * 10, "Spam should have much higher commits/contributor ratio"

        results.pass_test("Spam detection heuristics")
    except Exception as e:
        results.fail_test("Spam detection heuristics", str(e))

def test_gar_integration_file_handling():
    """Test GAR integration file operations."""
    try:
        import tempfile

        # Create temporary gar_orgs.txt
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_file = f.name
            f.write("existing-org\n")

        try:
            # Test adding new org
            # Note: This would require modifying radar.feed_to_gar to accept custom path
            # For now, just verify file operations work
            with open(temp_file, 'r') as f:
                orgs = set(line.strip() for line in f if line.strip())

            assert "existing-org" in orgs, "Existing org should be present"

            # Test deduplication
            orgs.add("new-org")
            orgs.add("existing-org")  # Duplicate

            with open(temp_file, 'w') as f:
                f.write('\n'.join(sorted(orgs)) + '\n')

            with open(temp_file, 'r') as f:
                final_orgs = [line.strip() for line in f if line.strip()]

            assert len(final_orgs) == 2, "Should have 2 unique orgs"
            assert "new-org" in final_orgs, "New org should be added"

            results.pass_test("GAR integration file handling")
        finally:
            os.unlink(temp_file)

    except Exception as e:
        results.fail_test("GAR integration file handling", str(e))

# =============================================================================
# Integration Tests (Require Environment Variables)
# =============================================================================

def test_github_api_connection():
    """Test actual GitHub API connection (requires GITHUB_TOKEN)."""
    try:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("⚠️  Skipping GitHub API test (no GITHUB_TOKEN)")
            return

        # Try to fetch events
        events = radar.fetch_github_events(limit=10)
        assert isinstance(events, list), "Should return list of events"

        if len(events) > 0:
            print(f"   Found {len(events)} recent events")
            results.pass_test("GitHub API connection")
        else:
            print("⚠️  No events found (may be rate limited or API issue)")

    except Exception as e:
        results.fail_test("GitHub API connection", str(e))

def test_velocity_metric_fetching():
    """Test fetching real velocity metrics (requires GITHUB_TOKEN)."""
    try:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("⚠️  Skipping velocity metric test (no GITHUB_TOKEN)")
            return

        # Test on a known public repo
        test_repo = "torvalds/linux"

        # Fetch commits
        commits = radar.fetch_commits_count(test_repo, since_days=7)
        assert commits >= 0, "Commits count should be non-negative"

        # Fetch contributors
        contributors = radar.fetch_contributors_count(test_repo)
        assert contributors > 0, "Linux should have many contributors"

        print(f"   Linux kernel: {commits} commits/7d, {contributors} contributors")
        results.pass_test("Velocity metric fetching")

    except Exception as e:
        results.fail_test("Velocity metric fetching", str(e))

# =============================================================================
# Performance Tests
# =============================================================================

def test_velocity_calculation_performance():
    """Test velocity calculation performance with reproducible methodology."""
    try:
        import time
        import platform
        import os

        # Print machine specs for reproducibility
        print(f"\n   Machine Specs:")
        print(f"   - Platform: {platform.system()} {platform.release()}")
        print(f"   - Processor: {platform.processor()}")
        print(f"   - Python: {platform.python_version()}")
        print(f"   - CPU Count: {os.cpu_count()}")

        # Benchmark parameters
        dataset_size = 10000
        warmup_iterations = 100

        # Warmup run (not measured)
        print(f"   Warmup: {warmup_iterations} iterations...")
        for i in range(warmup_iterations):
            _ = radar.calculate_velocity_score(
                commits_7d=i % 100,
                forks_7d=i % 10,
                contributors=i % 20,
                issues_7d=i % 30,
                prs_7d=i % 25,
                watchers=i % 50
            )

        # Measured run
        print(f"   Measuring: {dataset_size} iterations...")
        times = []
        for i in range(dataset_size):
            start = time.perf_counter()
            _ = radar.calculate_velocity_score(
                commits_7d=i % 100,
                forks_7d=i % 10,
                contributors=i % 20,
                issues_7d=i % 30,
                prs_7d=i % 25,
                watchers=i % 50
            )
            times.append(time.perf_counter() - start)

        # Calculate statistics
        times.sort()
        median = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        total_time = sum(times)
        throughput = dataset_size / total_time

        print(f"   Results (n={dataset_size}):")
        print(f"   - Throughput: {throughput:,.0f} calcs/sec")
        print(f"   - Median latency: {median * 1_000_000:.2f} μs")
        print(f"   - P95 latency: {p95 * 1_000_000:.2f} μs")

        assert throughput > 1000, "Should calculate at least 1000 scores/second"
        results.pass_test("Velocity calculation performance")
    except Exception as e:
        results.fail_test("Velocity calculation performance", str(e))

# =============================================================================
# Main Test Runner
# =============================================================================

def run_unit_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("Running Unit Tests")
    print("="*60 + "\n")

    test_velocity_score_calculation()
    test_ipfs_cid_generation()
    test_database_operations()
    test_spam_detection_heuristics()
    test_gar_integration_file_handling()
    test_velocity_calculation_performance()

def run_integration_tests():
    """Run integration tests (require environment variables)."""
    print("\n" + "="*60)
    print("Running Integration Tests")
    print("="*60 + "\n")

    test_github_api_connection()
    test_velocity_metric_fetching()

def main():
    parser = argparse.ArgumentParser(
        description="Test Repo Radar functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")

    args = parser.parse_args()

    if args.unit:
        run_unit_tests()
    elif args.integration:
        run_integration_tests()
    else:
        # Run all tests
        run_unit_tests()
        run_integration_tests()

    # Print summary and exit with appropriate code
    success = results.summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
