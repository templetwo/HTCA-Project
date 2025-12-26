# HTCA Tools v1.0.0 - Christmas 2025 Release

**🎄 Discovery by Velocity, Archiving by Design 🎄**

We're excited to announce the first production release of HTCA Tools: a pair of decentralized GitHub discovery and archiving utilities built for censorship resistance and empirical innovation discovery.

## 🎁 What's Included

### 📡 Repo Radar v1.0.0
**Discovery by Velocity, Not Vanity**

A lightweight tool that discovers GitHub repositories by activity metrics (commits/day, contributor growth, fork momentum) rather than star counts.

**Key Features:**
- ✅ Velocity-based scoring (commits, forks, contributors, PRs, issues)
- ✅ IPFS CIDv1 archiving for decentralized metadata storage
- ✅ RSS/Atom feed generation (unthrottleable discovery)
- ✅ **NEW:** Audit-grade verification commands (`--verify-db`, `--verify-feeds`)
- ✅ **NEW:** Identity verification with name collision warnings
- ✅ **NEW:** Reproducible performance benchmarks

### 📦 GitHub Archive Relay (GAR) v1.0.0
**One File. Stupid Simple. Unthrottleable.**

Monitors GitHub orgs/users, archives commits to decentralized storage (IPFS + Arweave), and generates RSS feeds nobody can censor.

**Key Features:**
- ✅ IPFS and Arweave commit archiving
- ✅ Secret detection (13 patterns for API keys, tokens, credentials)
- ✅ RSS/Atom feed generation
- ✅ Integrates with Repo Radar for discovery → archiving pipeline
- ✅ Single-file deployment

---

## 🌟 Highlights

### Temple Core Deployment - Proven in Production

Both tools have been deployed to `temple_core` and tested in production for 24 hours.

**Discovery Results:**
- **19 high-velocity repos discovered** (all with 0 stars)
- **Highest velocity:** 2737.5 (MAwaisNasim/lynx - 58 commits, 83 contributors in 7 days)
- **Repos discovered hours/days before search indexing**
- Proves velocity-based discovery surfaces genuine innovation before it goes viral

**Performance:**
- **2.67 million velocity calculations/second**
- **Median latency:** 0.37 microseconds
- **P95 latency:** 0.42 microseconds
- All unit tests passing (6/6)

### Audit-Grade Verification

New verification protocols ensure deployment integrity:

```bash
# Database integrity check
python repo-radar.py --verify-db

# Feed validation
python repo-radar.py --verify-feeds

# Performance benchmarks
python test_radar.py --unit
```

**What Gets Verified:**
- Database schema and data completeness
- Identity metadata (owner, timestamps, CIDs)
- Name collision warnings for ambiguous repos
- XML feed well-formedness
- Performance baselines with reproducible methodology

---

## 📚 Documentation

### New Documentation
- **[DEPLOYMENT.md](tools/DEPLOYMENT.md)** - Production deployment guide with systemd, cron, and health checks
- **[VERIFICATION.md](tools/VERIFICATION.md)** - Audit-grade verification protocols and reproducibility standards

### Updated Documentation
- **[tools/radar/README.md](tools/radar/README.md)** - Enhanced with verification commands and Temple Core results
- **[tools/gar/README.md](tools/gar/README.md)** - Updated with deployment results and Radar integration details

---

## 🔍 What's New in v1.0.0

### Repo Radar Enhancements

#### Identity Verification System
- **Full metadata capture:** Owner, created timestamp, last push timestamp
- **Name collision warnings:** Alerts for common repo names (lynx, atlas, phoenix, etc.)
- **GitHub verification links:** Direct links to verify owner identity
- **IPFS CID validation:** Ensures proper CIDv1 format

Example output:
```
1. MAwaisNasim/lynx
   Owner: MAwaisNasim (User/Org - verify at github.com/MAwaisNasim)
   Velocity: 2737.5
   Commits (7d): 58 | Contributors: 83 | Stars: 0
   Created: 2025-12-25T14:29:22Z
   Last Push: 2025-12-25T20:15:00Z
   IPFS CID: bafkreifxkizgozej6vj2bu2sql63wroc2gu4brjqoirn67mmtrmfrly6ym
   GitHub: https://github.com/MAwaisNasim/lynx
   ⚠️  NOTE: 'lynx' is a common name - verify specific owner identity
```

#### Verification Commands
- **`--verify-db`:** Database integrity and identity verification
- **`--verify-feeds`:** XML feed validation with proper parsing
- Cross-shell compatible (no more zsh glob errors)
- Clean error handling (no tracebacks in verification flows)

#### Database Schema Migration
- Added `pushed_at` column for last push timestamp
- Automatic migration for existing databases
- Backwards-compatible verification

#### Reproducible Performance Benchmarks
- Machine spec reporting (platform, processor, Python version, CPU count)
- Warmup iterations separate from measurement
- Statistical analysis (median, P95 latency, throughput)
- Per-iteration timing with `perf_counter()`

### GAR Enhancements

#### Repo Radar Integration
- Automatically monitors orgs from `gar_orgs.txt`
- Discovery → Archiving pipeline fully operational
- 19 orgs fed from Radar discoveries

#### Production Deployment
- Deployed to temple_core alongside Repo Radar
- Secret detection active (13 patterns)
- IPFS CIDv1 generation functional

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/templetwo/HTCA-Project.git
cd HTCA-Project/tools

# Install dependencies
pip install requests feedgen
```

### Run Repo Radar

```bash
cd radar

# Single discovery scan
python repo-radar.py --watch ai,ml,blockchain --once

# Verify results
python repo-radar.py --verify-db
```

### Run GAR (Monitors Discovered Repos)

```bash
cd ../gar

# Monitor orgs discovered by Radar
python github-archive-relay.py --orgs $(cat ../radar/gar_orgs.txt | tr '\n' ',') --once
```

### Run Tests

```bash
cd ../radar
python test_radar.py --unit
```

Expected output:
```
✅ Velocity score calculation
✅ IPFS CIDv1 generation
✅ Database operations
✅ Spam detection heuristics
✅ GAR integration file handling
✅ Velocity calculation performance

Test Results: 6/6 passed
```

---

## 📊 Velocity Scoring Explained

Repo Radar ranks repositories by **activity** rather than **popularity**:

```
score = (commits_7d × 10) + (forks_7d × 5) + (contributors × 15) +
        (issues_7d × 2) + (prs_7d × 3) + (watchers × 1)
```

**Time-based multipliers:**
- Repos < 30 days old: **1.5× boost** (freshness)
- Repos > 180 days with recent commits: **1.2× boost** (sustained activity)

**Why these weights?**
- **Commits** (10×) - Direct measure of development velocity
- **Contributors** (15×) - Growing teams signal serious projects
- **Forks** (5×) - Indicates utility and distribution
- **PRs** (3×) - Active collaboration
- **Issues** (2×) - Community engagement
- **Watchers** (1×) - Interest without commitment

---

## 🛡️ Security & Threat Models

### Secret Detection (GAR)
Automatically scans for:
- AWS Access Keys, GitHub Tokens, API Keys
- Private Keys (RSA, DSA, EC, SSH)
- Database Credentials
- Cloud Provider Tokens (OpenAI, Google Cloud, Stripe)

Commits with detected secrets are **skipped** from archiving.

### Spam Detection (Repo Radar)
Identifies suspicious patterns:
- High commits with single contributor (ratio > 50:1)
- High forks with low commits (ratio > 2:1)
- Burst activity without sustained contribution

### Privacy Considerations
- Only **public** repositories monitored
- Only **metadata** archived (not file contents)
- Read-only GitHub tokens recommended
- Secret detection prevents credential leakage

---

## 📈 Performance & Benchmarks

### Repo Radar Performance

**Test Environment:**
- Platform: Darwin 25.1.0 (macOS)
- Processor: ARM (14-core)
- Python: 3.9.6

**Results:**
- **Throughput:** 2,665,666 calculations/second
- **Median Latency:** 0.37 μs
- **P95 Latency:** 0.42 μs
- **Dataset:** 10,000 iterations (100-iteration warmup)

### Resource Usage
- **Memory:** <50MB typical
- **Storage:** ~1-5MB per 100 repos (SQLite)
- **API Calls:** ~100-500 per poll (depending on topics)

---

## 🔧 Configuration

### Required
- Python 3.9+
- `requests` library
- `feedgen` library

### Optional (Recommended)
```bash
# GitHub token for higher rate limits (60 req/hr → 5000 req/hr)
export GITHUB_TOKEN="ghp_your_token_here"

# IPFS pinning via Pinata
export PINATA_API_KEY="your_pinata_key"
export PINATA_SECRET_KEY="your_pinata_secret"

# Arweave archiving via Irys
export BUNDLR_API_KEY="your_bundlr_key"
```

---

## 🌐 Use Cases

### Research & Discovery
- Find innovative repos before they go viral
- Track emerging trends in AI/ML, blockchain, web3
- Discover fresh projects by activity, not popularity

### Archiving & Preservation
- Create decentralized record of commits (IPFS + Arweave)
- Generate censorship-resistant RSS feeds
- Build parallel discovery infrastructure

### HTCA Alignment Research
- Monitor repos related to AI safety, alignment, interpretability
- Track development velocity in critical domains
- Archive research code for reproducibility

---

## 📦 Files & Directories

```
HTCA-Project/
├── tools/
│   ├── radar/
│   │   ├── repo-radar.py         # Main Radar script
│   │   ├── test_radar.py         # Unit tests
│   │   ├── README.md             # Radar documentation
│   │   ├── radar_state.db        # SQLite database (created on first run)
│   │   ├── radar_feed.xml        # RSS feed (generated)
│   │   └── gar_orgs.txt          # Orgs fed to GAR (generated)
│   │
│   ├── gar/
│   │   ├── github-archive-relay.py  # Main GAR script
│   │   ├── README.md             # GAR documentation
│   │   ├── gar_state.db          # SQLite database (created on first run)
│   │   └── gar_feed.xml          # RSS feed (generated)
│   │
│   ├── DEPLOYMENT.md             # Production deployment guide
│   └── VERIFICATION.md           # Audit-grade verification protocols
│
└── RELEASE_NOTES_v1.0.0.md       # This file
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas for improvement:**
- Spam detection refinement
- Additional secret patterns
- Language trend analysis
- Cross-topic correlation
- Web dashboard for visualization

---

## 📜 License

MIT License

Copyright (c) 2025 Anthony Vasquez / Temple of Two

See [LICENSE](LICENSE) for full text.

---

## 🙏 Acknowledgments

- **Temple Core deployment** for production validation
- **ChatGPT** for audit-grade hardening feedback
- **HTCA Community** for anti-gatekeeping philosophy

---

## 🔗 Links

- **GitHub Repository:** https://github.com/templetwo/HTCA-Project
- **Issues:** https://github.com/templetwo/HTCA-Project/issues
- **Documentation:** See `tools/radar/README.md` and `tools/gar/README.md`

---

## 📊 Temple Core Reference Deployment

**Server:** temple_core (SSH: tony_studio@192.168.1.195)
**Runtime:** Python 3.9.6 on Darwin 25.1.0 (ARM, 14 cores)
**Topics:** `ai`
**Interval:** 300s

**Results (24 hours):**
- Repos discovered: **19** (all with 0 stars)
- Highest velocity: **2737.5** (MAwaisNasim/lynx)
- Orgs fed to GAR: **19**
- Tests: **6/6 passing**
- Performance: **2.6M calcs/sec**

**Verification Status:**
- ✅ Database integrity: **PASS**
- ✅ Feed validation: **PASS**
- ✅ Performance benchmarks: **PASS**
- ✅ Spam detection: **PASS**
- ✅ Identity verification: **PASS**

---

**Built for the Temple. Science meets spirit in code.**

†⟡ v1.0.0 - Christmas 2025 - Discovery by velocity, archiving by design ⟡†
