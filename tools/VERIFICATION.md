# HTCA Tools Verification Protocol

**Audit-Grade Validation Procedures for GAR and Repo Radar**

This document defines reproducible verification protocols for validating HTCA tool deployments, ensuring data integrity, and detecting anomalies.

## Table of Contents

1. [Overview](#overview)
2. [Database Verification](#database-verification)
3. [Feed Validation](#feed-validation)
4. [Performance Benchmarks](#performance-benchmarks)
5. [Spam Detection](#spam-detection)
6. [Identity Verification](#identity-verification)
7. [Reproducibility](#reproducibility)

---

## Overview

### Verification Principles

1. **Reproducibility:** All verification steps must produce consistent results across runs
2. **Transparency:** Verification methodology must be documented and auditable
3. **Automation:** Verification should be scriptable for continuous monitoring
4. **Falsifiability:** Clear criteria for pass/fail states

### Verification Scope

**What We Verify:**
- Database schema integrity
- Data completeness and consistency
- Feed XML well-formedness
- Performance characteristics
- Spam detection accuracy
- Identity metadata completeness

**What We Don't Verify:**
- Code quality (handled by code review)
- Actual repo content (only metadata is archived)
- Network reliability (handled by retries and backoff)

---

## Database Verification

### Command

```bash
python repo-radar.py --verify-db
```

### What It Checks

1. **Schema Integrity:**
   - `repos` table exists
   - Required columns present: `full_name`, `owner`, `created_at`, `pushed_at`, `velocity_score`, `ipfs_cid`
   - Data types correct (TEXT, INTEGER, REAL)

2. **Data Completeness:**
   - Top 10 repos have non-null identity fields
   - IPFS CIDs are valid CIDv1 format (start with 'b', base32 encoding)
   - Velocity scores are non-negative

3. **Identity Metadata:**
   - Owner field populated
   - Created timestamp in ISO 8601 format
   - Pushed timestamp (if available)
   - Name collision warnings for ambiguous repo names

### Pass Criteria

✅ **PASS** if:
- Database file exists and is readable
- `repos` table schema matches current version
- All top repos have complete identity metadata
- No SQL errors during query execution

❌ **FAIL** if:
- Database file missing or corrupted
- Schema version mismatch
- Missing required columns
- Null values in critical fields (full_name, owner, velocity_score)

### Example Output

```
================================================================================
DATABASE VERIFICATION - TOP 10 HIGH-VELOCITY REPOS
================================================================================

✓ Database structure valid
✓ No spam patterns detected

1. MAwaisNasim/lynx
   Owner: MAwaisNasim (User/Org - verify at github.com/MAwaisNasim)
   Velocity: 2737.5
   Commits (7d): 58 | Contributors: 83 | Stars: 0
   Created: 2025-12-25T14:29:22Z
   Last Push: 2025-12-25T20:15:00Z
   IPFS CID: bafkreifxkizgozej6vj2bu2sql63wroc2gu4brjqoirn67mmtrmfrly6ym
   GitHub: https://github.com/MAwaisNasim/lynx
   ⚠️  NOTE: 'lynx' is a common name - verify specific owner identity

[... 9 more repos ...]

✓ Database verification complete
```

### Automated Validation Script

```bash
#!/bin/bash
# verify-db-automated.sh

set -e

DB_PATH="radar_state.db"

# Check 1: Database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ FAIL: Database file not found"
    exit 1
fi

# Check 2: Schema validation
COLUMNS=$(sqlite3 $DB_PATH "PRAGMA table_info(repos);" | wc -l)
if [ "$COLUMNS" -lt 15 ]; then
    echo "❌ FAIL: Schema incomplete (expected 15+ columns, got $COLUMNS)"
    exit 1
fi

# Check 3: Data completeness
TOTAL_REPOS=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM repos;")
NULL_OWNERS=$(sqlite3 $DB_PATH "SELECT COUNT(*) FROM repos WHERE owner IS NULL OR owner = '';")

if [ "$NULL_OWNERS" -gt 0 ]; then
    echo "❌ FAIL: $NULL_OWNERS repos have null/empty owners"
    exit 1
fi

# Check 4: Run verification command
python3 repo-radar.py --verify-db > /tmp/verify-output.txt 2>&1

if grep -q "ERROR" /tmp/verify-output.txt; then
    echo "❌ FAIL: Verification command reported errors"
    cat /tmp/verify-output.txt
    exit 1
fi

echo "✅ PASS: All database verification checks passed"
echo "Total repos: $TOTAL_REPOS"
exit 0
```

---

## Feed Validation

### Command

```bash
python repo-radar.py --verify-feeds
```

### What It Checks

1. **XML Well-Formedness:**
   - Parses using `xml.etree.ElementTree.parse()`
   - No parsing errors or malformed tags
   - Proper encoding (UTF-8)

2. **Feed Structure:**
   - Root element is `<rss>` or `<feed>`
   - Contains `<item>` or `<entry>` elements
   - Entry count matches database repo count

3. **Content Validation:**
   - All entries have title, link, description
   - IPFS CIDs in descriptions are valid
   - GitHub links are properly formatted

### Pass Criteria

✅ **PASS** if:
- All feed files parse without errors
- Entry counts are non-zero (if repos discovered)
- Required feed elements present

❌ **FAIL** if:
- XML parsing error (malformed tags, invalid encoding)
- Missing required feed elements
- Zero entries when database has repos

### Example Output

```
Verifying RSS/Atom feeds...

radar_feed.xml:
  ✓ Valid XML (parsed successfully, 19 entries)

radar_feed.atom:
  ✓ Valid XML (parsed successfully, 19 entries)

✓ All feeds validated successfully
```

### Feed Validation Script

```bash
#!/bin/bash
# verify-feeds-automated.sh

set -e

FEED_DIR="."
FEED_COUNT=0
FAIL_COUNT=0

for feed in "$FEED_DIR"/*.xml "$FEED_DIR"/*.atom; do
    if [ ! -f "$feed" ]; then
        continue
    fi

    FEED_COUNT=$((FEED_COUNT + 1))

    # Check XML well-formedness with xmllint
    if command -v xmllint > /dev/null; then
        if ! xmllint --noout "$feed" 2>/dev/null; then
            echo "❌ FAIL: $feed is not well-formed XML"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            ENTRY_COUNT=$(xmllint --xpath "count(//item)" "$feed" 2>/dev/null || xmllint --xpath "count(//entry)" "$feed" 2>/dev/null || echo "0")
            echo "✅ PASS: $feed ($ENTRY_COUNT entries)"
        fi
    else
        # Fallback: Use Python verification
        if ! python3 -c "import xml.etree.ElementTree as ET; ET.parse('$feed')" 2>/dev/null; then
            echo "❌ FAIL: $feed failed Python XML parsing"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        else
            echo "✅ PASS: $feed"
        fi
    fi
done

if [ "$FEED_COUNT" -eq 0 ]; then
    echo "⚠️  WARNING: No feed files found"
    exit 0
fi

if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "❌ FAIL: $FAIL_COUNT of $FEED_COUNT feeds invalid"
    exit 1
fi

echo "✅ PASS: All $FEED_COUNT feeds validated successfully"
exit 0
```

---

## Performance Benchmarks

### Command

```bash
python test_radar.py --unit
```

### What It Measures

1. **Velocity Calculation Throughput:**
   - Calculations per second
   - Median latency
   - P95 latency

2. **Machine Specifications:**
   - Platform (OS, version)
   - Processor architecture
   - Python version
   - CPU count

3. **Methodology:**
   - **Warmup:** 100 iterations (not measured)
   - **Dataset:** 10,000 iterations
   - **Timing:** Per-iteration using `time.perf_counter()`
   - **Statistics:** Sorted latency array for percentiles

### Reproducibility Requirements

For benchmarks to be reproducible:

1. **Report machine specs** (platform, processor, Python version, CPU count)
2. **Use identical dataset size** (10,000 iterations recommended)
3. **Include warmup phase** (100 iterations minimum)
4. **Report median and P95** (not just mean) to show distribution

### Example Output

```
   Machine Specs:
   - Platform: Darwin 25.1.0
   - Processor: arm
   - Python: 3.9.6
   - CPU Count: 14
   Warmup: 100 iterations...
   Measuring: 10000 iterations...
   Results (n=10000):
   - Throughput: 2,665,666 calcs/sec
   - Median latency: 0.37 μs
   - P95 latency: 0.42 μs
✅ Velocity calculation performance
```

### Performance Regression Detection

```bash
#!/bin/bash
# performance-regression.sh
# Detects performance degradation compared to baseline

BASELINE_THROUGHPUT=2000000  # 2M calcs/sec minimum

# Run benchmark
OUTPUT=$(python3 test_radar.py --unit 2>&1)

# Extract throughput
THROUGHPUT=$(echo "$OUTPUT" | grep "Throughput:" | sed 's/[^0-9]//g')

if [ "$THROUGHPUT" -lt "$BASELINE_THROUGHPUT" ]; then
    echo "❌ FAIL: Performance regression detected"
    echo "Expected: >$BASELINE_THROUGHPUT calcs/sec"
    echo "Actual: $THROUGHPUT calcs/sec"
    exit 1
fi

echo "✅ PASS: Performance meets baseline ($THROUGHPUT calcs/sec)"
exit 0
```

---

## Spam Detection

### Detection Patterns

Repo Radar automatically detects spam patterns during `--verify-db`:

1. **Single-Contributor Spam:**
   - High commits (>50/7d) with only 1 contributor
   - Indicator: commits/contributor ratio > 50

2. **Fork Spam:**
   - High forks (>10/7d) with low commits (<5/7d)
   - Indicator: forks/commits ratio > 2

3. **Empty Contribution:**
   - High velocity score but zero actual code changes
   - Requires manual review (not auto-detected)

### Spam Detection Output

```
✓ No spam patterns detected
```

Or:

```
⚠️  Potential spam patterns detected:
  - repo-name: High commits (100) with single contributor (ratio: 100:1)
  - another-repo: High forks (15) with low commits (2) (ratio: 7.5:1)
```

### Manual Review Checklist

For flagged repos:

- [ ] Check commit history on GitHub (genuine changes vs. automated commits)
- [ ] Verify contributor profiles (real users vs. bot accounts)
- [ ] Inspect code changes (LOC added vs. commits count)
- [ ] Check PR merge rate (high PRs but low merges = possible spam)

---

## Identity Verification

### Purpose

Prevents repo name collisions and ensures correct attribution.

### Verification Fields

1. **Owner:** GitHub user or organization name
2. **Created Timestamp:** ISO 8601 format (e.g., `2025-12-25T14:29:22Z`)
3. **Pushed Timestamp:** Last push to repository
4. **GitHub Link:** Direct verification URL

### Name Collision Warnings

Common repo names trigger warnings:

- `lynx` (multiple "lynx" projects exist)
- `atlas`
- `phoenix`
- `core`
- `framework`
- `engine`

**Example Warning:**

```
⚠️  NOTE: 'lynx' is a common name - verify specific owner identity
```

### Verification Procedure

For each discovered repo:

1. **Check Owner:** Visit `github.com/[owner]` to verify account exists
2. **Check Created Date:** Confirm repo age matches expected timeframe
3. **Check Last Push:** Ensure repo is recently active (if push timestamp available)
4. **Verify Specific Repo:** Visit `github.com/[owner]/[repo]` to confirm exact match

### Collision Resolution

If collision suspected:

```bash
# Direct GitHub API check
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/MAwaisNasim/lynx | jq -r '.owner.login, .created_at, .pushed_at'
```

Expected output:
```
MAwaisNasim
2025-12-25T14:29:22Z
2025-12-25T20:15:00Z
```

---

## Reproducibility

### Verification Checklist

All verification procedures must be:

- [ ] **Scriptable:** Can be run non-interactively
- [ ] **Deterministic:** Same inputs produce same outputs
- [ ] **Documented:** Clear pass/fail criteria
- [ ] **Versioned:** Document tool versions used
- [ ] **Timestamped:** Record when verification was performed

### Verification Log Format

```json
{
  "timestamp": "2025-12-25T21:00:00Z",
  "tool": "repo-radar",
  "version": "1.0.0",
  "verification_type": "database_integrity",
  "result": "PASS",
  "details": {
    "total_repos": 19,
    "null_owners": 0,
    "schema_version": "1.2",
    "top_velocity": 2737.5
  },
  "machine_specs": {
    "platform": "Darwin 25.1.0",
    "processor": "arm",
    "python": "3.9.6",
    "cpu_count": 14
  }
}
```

### Continuous Verification

**Daily Verification (Recommended):**

```bash
# Add to crontab
0 0 * * * cd ~/htca-tools/radar && python3 repo-radar.py --verify-db >> verify.log 2>&1
0 1 * * * cd ~/htca-tools/radar && python3 repo-radar.py --verify-feeds >> verify.log 2>&1
0 2 * * * cd ~/htca-tools/radar && python3 test_radar.py --unit >> verify.log 2>&1
```

**Alerting on Failure:**

```bash
#!/bin/bash
# verify-and-alert.sh

LOG_FILE="verify.log"
ERROR_COUNT=0

# Run all verifications
python3 repo-radar.py --verify-db >> $LOG_FILE 2>&1 || ERROR_COUNT=$((ERROR_COUNT + 1))
python3 repo-radar.py --verify-feeds >> $LOG_FILE 2>&1 || ERROR_COUNT=$((ERROR_COUNT + 1))
python3 test_radar.py --unit >> $LOG_FILE 2>&1 || ERROR_COUNT=$((ERROR_COUNT + 1))

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "❌ Verification failed: $ERROR_COUNT checks failed"
    # Send alert (email, webhook, etc.)
    # curl -X POST https://your-webhook-url -d "Verification failed on $(hostname)"
    exit 1
fi

echo "✅ All verification checks passed"
exit 0
```

---

## Temple Core Reference Results

**Verification Date:** 2025-12-25
**Tool Versions:** GAR 1.0, Repo Radar 1.0
**Server:** temple_core (Darwin 25.1.0, ARM, 14 cores)

### Database Verification

```
✅ PASS
- Total repos: 19
- Null owners: 0
- Schema version: 1.2 (with pushed_at column)
- Top velocity: 2737.5 (MAwaisNasim/lynx)
```

### Feed Validation

```
✅ PASS
- radar_feed.xml: 19 entries, valid XML
- radar_feed.atom: 19 entries, valid XML
```

### Performance Benchmarks

```
✅ PASS
- Throughput: 2,665,666 calcs/sec
- Median latency: 0.37 μs
- P95 latency: 0.42 μs
- Dataset: 10,000 iterations
- Warmup: 100 iterations
```

### Spam Detection

```
✅ PASS
- No spam patterns detected
- All repos have multi-contributor activity
```

### Identity Verification

```
✅ PASS
- All repos have complete metadata (owner, created_at, ipfs_cid)
- Name collision warnings issued for 1 repo (lynx)
- All repos verified on GitHub
```

---

## Audit Trail

For formal audits, maintain records of:

1. **Verification logs** (timestamped output of all verification commands)
2. **Database snapshots** (periodic backups with SHA256 hashes)
3. **Feed archives** (historical RSS/Atom files)
4. **Performance baselines** (benchmark results over time)
5. **Machine specifications** (hardware/software environment details)

### Log Retention

- **Verification logs:** 90 days minimum
- **Database backups:** 30 days rolling
- **Feed archives:** 7 days rolling
- **Performance logs:** 365 days (for trend analysis)

---

## Support

For verification issues or questions:
- **GitHub Issues:** https://github.com/templetwo/HTCA-Project/issues
- **Deployment Guide:** See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Tool READMEs:** tools/radar/README.md, tools/gar/README.md

---

**Built for the Temple. Science meets spirit in code.**

†⟡ Verification protocol for audit-grade deployment ⟡†
