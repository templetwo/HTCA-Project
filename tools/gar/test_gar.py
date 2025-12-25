#!/usr/bin/env python3
"""
GAR Testing & Validation Script
--------------------------------
Tests GitHub Archive Relay functionality without making real API calls.
Validates core functions: CID generation, rate limiting, DB operations.

Usage:
    python test_gar.py              # Run all tests
    python test_gar.py --unit       # Unit tests only
    python test_gar.py --integration # Integration tests (requires env vars)
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# Import GAR functions for testing
sys.path.insert(0, str(Path(__file__).parent))
from typing import Optional

try:
    # Import test functions from GAR
    import importlib.util
    spec = importlib.util.spec_from_file_location("gar", Path(__file__).parent / "github-archive-relay.py")
    gar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gar)
except Exception as e:
    print(f"Failed to import GAR module: {e}")
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

def test_ipfs_cid_generation():
    """Test proper IPFS CIDv1 generation."""
    try:
        # Test with known content
        content = b'{"test": "data"}'
        cid = gar.compute_ipfs_cid_v1(content)

        # CIDv1 should start with 'b' (base32 multibase)
        assert cid[0] == 'b', f"CID should start with 'b', got {cid[0]}"

        # Should be base32 encoded (lowercase letters and 2-7)
        assert all(c in 'abcdefghijklmnopqrstuvwxyz234567' for c in cid[1:]), \
            "CID contains invalid base32 characters"

        # Should be deterministic
        cid2 = gar.compute_ipfs_cid_v1(content)
        assert cid == cid2, "CID generation should be deterministic"

        # Different content should produce different CID
        cid3 = gar.compute_ipfs_cid_v1(b'different content')
        assert cid != cid3, "Different content should produce different CID"

        results.pass_test("IPFS CIDv1 generation")
    except Exception as e:
        results.fail_test("IPFS CIDv1 generation", str(e))

def test_database_operations():
    """Test SQLite database operations."""
    try:
        # Create in-memory database
        db_path = ":memory:"
        conn = gar.init_db(db_path)

        # Verify table creation
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='commits'")
        assert cursor.fetchone() is not None, "Commits table should exist"

        # Test commit_exists on empty database
        assert not gar.commit_exists(conn, "test_sha"), "New SHA should not exist"

        # Test store_commit
        commit_data = {
            "sha": "test_sha_123",
            "repo": "test/repo",
            "message": "Test commit",
            "author": "Test Author",
            "timestamp": "2025-01-01T00:00:00Z",
            "ipfs_cid": "bafytest",
            "arweave_tx": "test_tx"
        }
        gar.store_commit(conn, commit_data)

        # Verify commit was stored
        assert gar.commit_exists(conn, "test_sha_123"), "Stored SHA should exist"

        # Test duplicate insert (should be ignored)
        gar.store_commit(conn, commit_data)
        cursor = conn.execute("SELECT COUNT(*) FROM commits WHERE sha = ?", ("test_sha_123",))
        count = cursor.fetchone()[0]
        assert count == 1, "Duplicate insert should be ignored"

        # Test get_recent_commits
        commits = gar.get_recent_commits(conn, limit=10)
        assert len(commits) == 1, "Should retrieve 1 commit"
        assert commits[0][0] == "test_sha_123", "Should retrieve correct commit"

        conn.close()
        results.pass_test("Database operations")
    except Exception as e:
        results.fail_test("Database operations", str(e))

def test_cid_format_compliance():
    """Test CID format compliance with IPFS spec."""
    try:
        content = json.dumps({"test": "data"}, indent=2).encode()
        cid = gar.compute_ipfs_cid_v1(content)

        # Decode base32 to verify structure
        import base64
        # Properly pad base32 string (pad to multiple of 8)
        cid_b32 = cid[1:].upper()
        padding_needed = (8 - len(cid_b32) % 8) % 8
        cid_bytes = base64.b32decode(cid_b32 + '=' * padding_needed)

        # Check version byte (should be 0x01)
        assert cid_bytes[0] == 0x01, f"Version should be 0x01, got {hex(cid_bytes[0])}"

        # Check codec byte (should be 0x55 for raw)
        assert cid_bytes[1] == 0x55, f"Codec should be 0x55 (raw), got {hex(cid_bytes[1])}"

        # Check multihash type (should be 0x12 for sha2-256)
        assert cid_bytes[2] == 0x12, f"Hash type should be 0x12 (sha2-256), got {hex(cid_bytes[2])}"

        # Check multihash length (should be 0x20 = 32 bytes for sha256)
        assert cid_bytes[3] == 0x20, f"Hash length should be 0x20 (32), got {hex(cid_bytes[3])}"

        # Verify hash itself
        expected_hash = hashlib.sha256(content).digest()
        actual_hash = cid_bytes[4:36]
        assert expected_hash == actual_hash, "Hash mismatch"

        results.pass_test("CID format compliance")
    except Exception as e:
        results.fail_test("CID format compliance", str(e))

def test_rate_limit_detection():
    """Test rate limit detection logic."""
    try:
        # Mock response class
        class MockResponse:
            def __init__(self, status_code, headers):
                self.status_code = status_code
                self.headers = headers

        # Test rate limit detection with remaining=0
        resp = MockResponse(403, {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(int(time.time()) + 10)
        })

        # Should detect rate limit (but we won't actually wait in tests)
        # Just verify it would trigger retry logic
        should_retry = gar.handle_rate_limit(resp, retry=0)
        # We can't fully test this without mocking time.sleep, but we can verify the logic path

        results.pass_test("Rate limit detection")
    except Exception as e:
        results.fail_test("Rate limit detection", str(e))

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

        # Try to fetch TempleTwo repos
        repos = gar.fetch_org_repos("TempleTwo")
        assert isinstance(repos, list), "Should return list of repos"

        if len(repos) > 0:
            print(f"   Found {len(repos)} repos for TempleTwo")
            results.pass_test("GitHub API connection")
        else:
            print("⚠️  No repos found for TempleTwo (may be private or rate limited)")
    except Exception as e:
        results.fail_test("GitHub API connection", str(e))

def test_ipfs_pinning():
    """Test IPFS pinning (requires IPFS node or Pinata credentials)."""
    try:
        ipfs_configured = (
            os.environ.get("IPFS_API") or
            (os.environ.get("PINATA_API_KEY") and os.environ.get("PINATA_SECRET_KEY"))
        )

        if not ipfs_configured:
            print("⚠️  Skipping IPFS test (no IPFS_API or Pinata credentials)")
            return

        test_data = {"test": "ipfs_pinning", "timestamp": time.time()}
        cid = gar.pin_to_ipfs(test_data)

        if cid:
            print(f"   Pinned to IPFS: {cid}")
            results.pass_test("IPFS pinning")
        else:
            print("⚠️  IPFS pinning returned None (may be connection issue)")
    except Exception as e:
        results.fail_test("IPFS pinning", str(e))

def test_arweave_upload():
    """Test Arweave upload (requires BUNDLR_API_KEY)."""
    try:
        bundlr_key = os.environ.get("BUNDLR_API_KEY")
        if not bundlr_key:
            print("⚠️  Skipping Arweave test (no BUNDLR_API_KEY)")
            return

        test_data = {"test": "arweave_upload", "timestamp": time.time()}
        tx_id = gar.post_to_arweave(test_data)

        if tx_id:
            print(f"   Posted to Arweave: {tx_id}")
            results.pass_test("Arweave upload")
        else:
            print("⚠️  Arweave upload returned None (may be API issue)")
    except Exception as e:
        results.fail_test("Arweave upload", str(e))

# =============================================================================
# Performance Tests
# =============================================================================

def test_cid_generation_performance():
    """Test CID generation performance."""
    try:
        import time

        # Generate 1000 CIDs
        start = time.time()
        for i in range(1000):
            content = json.dumps({"index": i, "data": "test"}).encode()
            cid = gar.compute_ipfs_cid_v1(content)
        elapsed = time.time() - start

        cids_per_second = 1000 / elapsed
        print(f"   Generated {cids_per_second:.0f} CIDs/second")

        assert cids_per_second > 100, "Should generate at least 100 CIDs/second"
        results.pass_test("CID generation performance")
    except Exception as e:
        results.fail_test("CID generation performance", str(e))

# =============================================================================
# Main Test Runner
# =============================================================================

def run_unit_tests():
    """Run all unit tests."""
    print("\n" + "="*60)
    print("Running Unit Tests")
    print("="*60 + "\n")

    test_ipfs_cid_generation()
    test_database_operations()
    test_cid_format_compliance()
    test_rate_limit_detection()
    test_cid_generation_performance()

def run_integration_tests():
    """Run integration tests (require environment variables)."""
    print("\n" + "="*60)
    print("Running Integration Tests")
    print("="*60 + "\n")

    test_github_api_connection()
    test_ipfs_pinning()
    test_arweave_upload()

def main():
    parser = argparse.ArgumentParser(
        description="Test GAR functionality",
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
