# HTCA Tools Deployment Guide

**Deploying GAR and Repo Radar to Remote Servers**

This guide covers production deployment of GitHub Archive Relay (GAR) and Repo Radar to remote servers with audit-grade verification protocols.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Deployment](#quick-deployment)
3. [Configuration](#configuration)
4. [Verification](#verification)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Remote Server Requirements

- **OS:** Linux or macOS (tested on Darwin 25.1.0)
- **Python:** 3.9+
- **Storage:** 1GB+ for databases and feeds
- **Network:** Outbound HTTPS (GitHub API, IPFS, Arweave)
- **SSH Access:** Key-based authentication recommended

### Local Machine Requirements

- **rsync** for file deployment
- **SSH client** with configured keys
- **Git** for version control

### Optional Services

- **IPFS Node:** Local or Pinata for content addressing
- **Arweave/Irys:** For permanent archiving (requires `BUNDLR_API_KEY`)

---

## Quick Deployment

### 1. Deploy Tools to Remote Server

```bash
# Set target server
TARGET="tony_studio@192.168.1.195"
REMOTE_DIR="~/htca-tools"

# Deploy GAR
rsync -az tools/gar/ $TARGET:$REMOTE_DIR/gar/

# Deploy Repo Radar
rsync -az tools/radar/ $TARGET:$REMOTE_DIR/radar/
```

### 2. Install Dependencies

```bash
ssh $TARGET << 'EOF'
cd ~/htca-tools/radar
pip3 install requests feedgen

cd ~/htca-tools/gar
pip3 install requests feedgen
EOF
```

### 3. Verify Installation

```bash
# Run unit tests
ssh $TARGET "cd ~/htca-tools/radar && python3 test_radar.py --unit"

# Verify database schema
ssh $TARGET "cd ~/htca-tools/radar && python3 repo-radar.py --verify-db || echo 'No database yet (expected)'"
```

---

## Configuration

### Environment Variables

Create environment configuration on remote server:

```bash
ssh $TARGET "cat > ~/htca-tools/.env << 'ENVEOF'
# GitHub API (5000 req/hr vs 60)
export GITHUB_TOKEN='ghp_your_token_here'

# IPFS Pinning (optional)
export PINATA_API_KEY='your_pinata_key'
export PINATA_SECRET_KEY='your_pinata_secret'

# Arweave Archiving (optional)
export BUNDLR_API_KEY='your_bundlr_key'
ENVEOF"
```

### GitHub Token Setup

1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `public_repo`, `read:org`
4. Copy token and add to `.env`

**Security:** Use read-only tokens with minimal scope.

### Repo Radar Configuration

```bash
ssh $TARGET << 'EOF'
cd ~/htca-tools/radar

# Source environment
source ../.env

# Run discovery scan (single poll)
python3 repo-radar.py --watch ai,ml,blockchain --once

# Verify results
python3 repo-radar.py --verify-db
EOF
```

### GAR Configuration

```bash
ssh $TARGET << 'EOF'
cd ~/htca-tools/gar

# Source environment
source ../.env

# Monitor orgs from Repo Radar discoveries
python3 github-archive-relay.py --orgs $(cat ../radar/gar_orgs.txt | tr '\n' ',') --once
EOF
```

---

## Verification

### Pre-Deployment Verification

**1. Database Integrity Check:**

```bash
ssh $TARGET "cd ~/htca-tools/radar && python3 repo-radar.py --verify-db"
```

Expected output:
```
================================================================================
DATABASE VERIFICATION - TOP 10 HIGH-VELOCITY REPOS
================================================================================

1. [repo-name]
   Owner: [owner] (User/Org - verify at github.com/[owner])
   Velocity: [score]
   Commits (7d): [n] | Contributors: [n] | Stars: [n]
   Created: [timestamp]
   Last Push: [timestamp]
   IPFS CID: [cid]
   GitHub: https://github.com/[owner]/[repo]
   ⚠️  NOTE: '[repo]' is a common name - verify specific owner identity (if applicable)
```

**2. Feed Validation:**

```bash
ssh $TARGET "cd ~/htca-tools/radar && python3 repo-radar.py --verify-feeds"
```

Expected output:
```
✓ Valid XML (parsed successfully, N entries)
```

**3. Unit Test Verification:**

```bash
ssh $TARGET "cd ~/htca-tools/radar && python3 test_radar.py --unit"
```

All tests should pass:
```
✅ Velocity score calculation
✅ IPFS CIDv1 generation
✅ Database operations
✅ Spam detection heuristics
✅ GAR integration file handling
✅ Velocity calculation performance

Test Results: 6/6 passed
```

### Post-Deployment Monitoring

**Check Process Status:**

```bash
# If running as systemd service
ssh $TARGET "systemctl status radar gar"

# If running in tmux/screen
ssh $TARGET "tmux list-sessions"
```

**Check Logs:**

```bash
# Systemd logs
ssh $TARGET "journalctl -u radar -n 50"
ssh $TARGET "journalctl -u gar -n 50"

# File logs
ssh $TARGET "tail -50 ~/htca-tools/radar/radar.log"
```

**Check Database Growth:**

```bash
ssh $TARGET "sqlite3 ~/htca-tools/radar/radar_state.db 'SELECT COUNT(*) FROM repos;'"
```

---

## Monitoring

### Systemd Service Setup

**Repo Radar Service:**

```bash
ssh $TARGET "sudo tee /etc/systemd/system/radar.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Repo Radar - Velocity-Based Discovery
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$HOME/htca-tools/radar
EnvironmentFile=$HOME/htca-tools/.env
ExecStart=/usr/bin/python3 $HOME/htca-tools/radar/repo-radar.py --watch ai,ml,blockchain --interval 300
Restart=always
RestartSec=30
StandardOutput=append:$HOME/htca-tools/radar/radar.log
StandardError=append:$HOME/htca-tools/radar/radar.log

[Install]
WantedBy=multi-user.target
SERVICEEOF"

# Enable and start
ssh $TARGET "sudo systemctl daemon-reload"
ssh $TARGET "sudo systemctl enable radar"
ssh $TARGET "sudo systemctl start radar"
```

**GAR Service:**

```bash
ssh $TARGET "sudo tee /etc/systemd/system/gar.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=GitHub Archive Relay
After=network.target radar.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$HOME/htca-tools/gar
EnvironmentFile=$HOME/htca-tools/.env
ExecStartPre=/bin/sleep 60
ExecStart=/usr/bin/python3 $HOME/htca-tools/gar/github-archive-relay.py --orgs-file ../radar/gar_orgs.txt --interval 300
Restart=always
RestartSec=30
StandardOutput=append:$HOME/htca-tools/gar/gar.log
StandardError=append:$HOME/htca-tools/gar/gar.log

[Install]
WantedBy=multi-user.target
SERVICEEOF"

# Enable and start
ssh $TARGET "sudo systemctl daemon-reload"
ssh $TARGET "sudo systemctl enable gar"
ssh $TARGET "sudo systemctl start gar"
```

### Cron Job Setup (Alternative)

```bash
ssh $TARGET "crontab -l > /tmp/cron.bak 2>/dev/null || true"
ssh $TARGET "cat >> /tmp/cron.new << 'CRONEOF'
# Repo Radar - every 5 minutes
*/5 * * * * cd ~/htca-tools/radar && source ../.env && python3 repo-radar.py --watch ai,ml,blockchain --once >> radar.log 2>&1

# GAR - every 5 minutes (offset by 2 minutes)
2-59/5 * * * * cd ~/htca-tools/gar && source ../.env && python3 github-archive-relay.py --orgs-file ../radar/gar_orgs.txt --once >> gar.log 2>&1

# Daily verification check
0 0 * * * cd ~/htca-tools/radar && python3 repo-radar.py --verify-db >> verify.log 2>&1
CRONEOF"

ssh $TARGET "crontab /tmp/cron.new"
```

### Health Check Script

Create monitoring script:

```bash
ssh $TARGET "cat > ~/htca-tools/health-check.sh << 'CHECKEOF'
#!/bin/bash
set -e

echo "=== HTCA Tools Health Check ==="
echo "Timestamp: $(date)"
echo

# Check Repo Radar database
echo "Repo Radar - Database:"
sqlite3 ~/htca-tools/radar/radar_state.db "SELECT COUNT(*) as total_repos FROM repos;" 2>/dev/null || echo "  ⚠️  No database"
echo

# Check GAR database
echo "GAR - Database:"
sqlite3 ~/htca-tools/gar/gar_state.db "SELECT COUNT(*) as total_commits FROM commits;" 2>/dev/null || echo "  ⚠️  No database"
echo

# Check RSS feeds
echo "RSS Feeds:"
ls -lh ~/htca-tools/radar/*.xml ~/htca-tools/gar/*.xml 2>/dev/null | wc -l | xargs echo "  Feed files:"
echo

# Check logs for errors
echo "Recent Errors (last hour):"
grep -i error ~/htca-tools/radar/radar.log 2>/dev/null | tail -5 || echo "  ✓ No errors"
grep -i error ~/htca-tools/gar/gar.log 2>/dev/null | tail -5 || echo "  ✓ No errors"
CHECKEOF"

ssh $TARGET "chmod +x ~/htca-tools/health-check.sh"
```

Run health check:

```bash
ssh $TARGET "~/htca-tools/health-check.sh"
```

---

## Troubleshooting

### Rate Limiting

**Symptom:**
```
[WARNING] Rate limited. Waiting 3600s until reset...
```

**Solution:**
```bash
# Verify GitHub token is set
ssh $TARGET 'echo $GITHUB_TOKEN'

# If empty, add to .env and restart service
ssh $TARGET "sudo systemctl restart radar gar"
```

### Database Locked

**Symptom:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Check for multiple processes
ssh $TARGET "ps aux | grep -E 'repo-radar|github-archive'"

# Stop duplicate processes
ssh $TARGET "killall python3"

# Restart services
ssh $TARGET "sudo systemctl restart radar gar"
```

### IPFS Connection Failed

**Symptom:**
```
[DEBUG] Local IPFS failed: Connection refused
[DEBUG] Pinata failed: Unauthorized
```

**Solution:**
This is expected if IPFS/Pinata not configured. Tools fall back to local CIDv1 generation (content-addressable proof without network pinning).

To enable IPFS pinning:
```bash
# Option 1: Start local IPFS node
ssh $TARGET "ipfs daemon &"

# Option 2: Configure Pinata
# Add PINATA_API_KEY and PINATA_SECRET_KEY to .env
```

### No Repos Discovered

**Symptom:**
```
Poll complete: 0 new repos
```

**Diagnosis:**
```bash
# Check database
ssh $TARGET "cd ~/htca-tools/radar && python3 repo-radar.py --stats"

# Check logs for rate limits
ssh $TARGET "grep -i 'rate limit' ~/htca-tools/radar/radar.log | tail -10"

# Test manual scan
ssh $TARGET "cd ~/htca-tools/radar && source ../.env && python3 repo-radar.py --watch ai --once"
```

### Verification Failures

**Symptom:**
```
Database verification failed: no such column: pushed_at
```

**Solution:**
This indicates an old database schema. The migration should auto-run on next connection:

```bash
# Force migration by opening database
ssh $TARGET "cd ~/htca-tools/radar && python3 -c 'from pathlib import Path; import sys; sys.path.insert(0, \".\"); import importlib.util; spec = importlib.util.spec_from_file_location(\"radar\", \"repo-radar.py\"); radar = importlib.util.module_from_spec(spec); spec.loader.exec_module(radar); radar.init_db(\"radar_state.db\")'"

# Verify migration
ssh $TARGET "cd ~/htca-tools/radar && python3 repo-radar.py --verify-db"
```

---

## Security Hardening

### File Permissions

```bash
ssh $TARGET "chmod 600 ~/htca-tools/.env"
ssh $TARGET "chmod 700 ~/htca-tools"
```

### Read-Only GitHub Token

Use minimal scope tokens:
- ✅ `public_repo` - Read public repositories
- ✅ `read:org` - Read organization data
- ❌ `repo` - Avoid full repo access
- ❌ `admin:*` - Never use admin scopes

### Database Backups

```bash
# Add to crontab
ssh $TARGET "cat >> /tmp/cron.new << 'CRONEOF'
# Daily database backup
0 2 * * * cp ~/htca-tools/radar/radar_state.db ~/htca-tools/backups/radar_state_$(date +\%Y\%m\%d).db
0 2 * * * cp ~/htca-tools/gar/gar_state.db ~/htca-tools/backups/gar_state_$(date +\%Y\%m\%d).db

# Weekly cleanup (keep 30 days)
0 3 * * 0 find ~/htca-tools/backups -name '*.db' -mtime +30 -delete
CRONEOF"

ssh $TARGET "crontab /tmp/cron.new"
ssh $TARGET "mkdir -p ~/htca-tools/backups"
```

---

## Performance Tuning

### Polling Intervals

**Recommended Settings:**

| Scenario | Radar Interval | GAR Interval | Rationale |
|----------|---------------|--------------|-----------|
| Development | 600s (10min) | 600s | Reduce API calls during testing |
| Production | 300s (5min) | 300s | Balance discovery speed vs rate limits |
| High-volume | 120s (2min) | 180s | Requires `GITHUB_TOKEN` (5000 req/hr) |

### Database Optimization

```bash
# Vacuum databases monthly
ssh $TARGET "sqlite3 ~/htca-tools/radar/radar_state.db 'VACUUM;'"
ssh $TARGET "sqlite3 ~/htca-tools/gar/gar_state.db 'VACUUM;'"
```

### Log Rotation

```bash
ssh $TARGET "sudo tee /etc/logrotate.d/htca-tools > /dev/null << 'ROTATEEOF'
$HOME/htca-tools/*/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    missingok
}
ROTATEEOF"
```

---

## Production Deployment Checklist

- [ ] Environment variables configured (`.env`)
- [ ] GitHub token set (`GITHUB_TOKEN`)
- [ ] Dependencies installed (`requests`, `feedgen`)
- [ ] Unit tests passing (6/6)
- [ ] Database schema migrated (pushed_at column exists)
- [ ] Systemd services configured (or cron jobs)
- [ ] Services enabled and running
- [ ] Logs rotating properly
- [ ] Database backups configured
- [ ] Health check script created
- [ ] Rate limit monitoring active
- [ ] File permissions hardened
- [ ] Verification commands tested (`--verify-db`, `--verify-feeds`)

---

## Temple Core Reference Deployment

**Configuration:**
- Server: temple_core (SSH: tony_studio@192.168.1.195)
- Runtime: Python 3.9.6 on Darwin 25.1.0 (ARM, 14 cores)
- Topics: `ai`
- Interval: 300s

**Results (24 hours):**
- Repos discovered: 19 (0 stars - proving velocity works)
- Highest velocity: 2737.5 (MAwaisNasim/lynx)
- Orgs fed to GAR: 19
- Tests: 6/6 passing
- Performance: 2.6M velocity calcs/sec

**Verification Status:**
- ✅ Database integrity: PASS
- ✅ Feed validation: PASS
- ✅ Performance benchmarks: PASS
- ✅ Spam detection: PASS
- ✅ Identity verification: PASS

---

## Support

For issues or questions:
- **GitHub Issues:** https://github.com/templetwo/HTCA-Project/issues
- **Documentation:** See individual tool READMEs (tools/radar/README.md, tools/gar/README.md)

---

**Built for the Temple. Science meets spirit in code.**

†⟡ Deployment guide for discovery and archiving ⟡†
