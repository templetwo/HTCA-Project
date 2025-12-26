# Repo Radar

**Discovery by Velocity, Not Vanity**

A lightweight tool that discovers GitHub repos by activity (commits/day, contributor growth, fork momentum) rather than star counts, archives high-velocity repos to IPFS, and generates an unthrottleable ranked RSS feed.

## Why?

GitHub's discovery algorithms favor established repos with high star counts. Fresh innovation drowns unless it goes viral. Repo Radar solves this by:

- **Polling GitHub Events API** for new repo creation events
- **Scoring by velocity** (commits/day, forks/day, contributor growth, PR/issue activity)
- **Archiving high-velocity repos** to IPFS for decentralized discovery
- **Generating ranked RSS feeds** that can't be throttled or censored
- **Integrating with GAR** to automatically archive commits from discovered repos

## Quick Start

```bash
# Install dependencies
pip install requests feedgen

# Run (basic - watch AI/ML repos)
python repo-radar.py --watch ai,ml,llm

# Run (comprehensive scan)
python repo-radar.py --watch ai,ml,blockchain,web3 --interval 300

# Single poll (no daemon)
python repo-radar.py --watch ai --once
```

## Features

✅ **Event-driven discovery** - Catches repos early via GitHub Events API
✅ **Velocity scoring** - Ranks by activity metrics, not vanity metrics
✅ **Topic-based search** - Scans specific domains (ai, blockchain, etc.)
✅ **IPFS archiving** - CIDv1-compliant metadata archiving
✅ **RSS feed generation** - Ranked feed of high-velocity repos
✅ **GAR integration** - Feeds discovered repos to commit archiver
✅ **Rate limit handling** - Exponential backoff for 403/429
✅ **SQLite state** - Survives restarts, no external deps
✅ **Single file** - Copy and run anywhere

## Velocity Scoring Formula

Repo Radar prioritizes **sustained activity** over vanity metrics:

```
score = (commits_7d × 10) + (forks_7d × 5) + (contributors × 15) +
        (issues_7d × 2) + (prs_7d × 3) + (watchers × 1)
```

**Time-based multipliers:**
- **Freshness boost:** Repos < 30 days old get 1.5× multiplier
- **Sustained activity bonus:** Repos > 180 days with recent commits get 1.2× multiplier

**Why these weights?**
- **Commits** (10×) - Direct measure of development velocity
- **Contributors** (15×) - Growing teams signal serious projects
- **Forks** (5×) - Indicates utility and distribution
- **PRs** (3×) - Active collaboration and code review
- **Issues** (2×) - Community engagement
- **Watchers** (1×) - Interest without commitment

## Configuration

All optional. The tool works out of the box with reduced rate limits.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GITHUB_TOKEN` | Personal access token (5000 req/hr vs 60) | None |
| `IPFS_API` | IPFS API endpoint | `http://localhost:5001` |
| `PINATA_API_KEY` | Pinata API key for IPFS pinning | None |
| `PINATA_SECRET_KEY` | Pinata secret key | None |

## Output Files

- `radar_state.db` - SQLite database of discovered repos and scores
- `radar_feed.xml` - RSS 2.0 feed (ranked by velocity)
- `radar_feed.atom` - Atom feed
- `gar_orgs.txt` - High-velocity repos fed to GAR for commit archiving

## Threat Model & Failure Modes

### Security Considerations

**Spam & Gaming the Velocity Score**
- **Risk:** Malicious actors creating repos with artificial activity (bot commits, fake PRs) to appear high-velocity
- **Detection Patterns:**
  - Repos with many commits but minimal code changes (indicator: high commits/LOC ratio)
  - Single-contributor repos with sudden burst activity
  - Repos with identical commit messages (automated spam)
  - Forks with no actual changes (fork spam)
- **Mitigation:** Manual review of high-velocity repos before adding to GAR
- **Future Enhancement:** Implement spam scoring based on commit diversity, contributor authenticity, and code quality metrics

**Malicious Repository Promotion**
- **Risk:** Archiving metadata for repos containing malware, phishing, or malicious code
- **Mitigation:** Repo Radar only archives *metadata* (repo name, description, metrics), not code
- **Note:** High velocity score does not imply code quality or safety
- **Recommendation:** Review repos manually before integration with production systems

**API Abuse & Rate Limit Exhaustion**
- **Risk:** Aggressive topic searches triggering GitHub rate limits
- **Mitigation:** Built-in exponential backoff and rate limit handling
- **Best Practice:** Use `GITHUB_TOKEN` for 5000 req/hr limit instead of 60 req/hr
- **Monitoring:** Check logs for repeated 403/429 responses

**Privacy Concerns**
- **Risk:** Publicly indexing private repos if token has access
- **Mitigation:** Tool only scans public repos via Events/Search APIs
- **Verification:** Review `radar_state.db` to ensure no private repo names appear
- **Best Practice:** Use read-only tokens with minimal scope

**GAR Integration Risks**
- **Risk:** Automatically feeding low-quality or spam repos to GAR for permanent archiving
- **Mitigation:** Velocity threshold (default: score > 50) filters out low-activity repos
- **Override:** Manually review `gar_orgs.txt` before starting GAR daemon
- **Recommendation:** Set higher threshold for production use (e.g., score > 100)

### Failure Modes

**GitHub Events API Unavailable**
- **Scenario:** GitHub API outage, network timeout, authentication failure
- **Behavior:** Tool logs error and continues with topic-based search
- **Impact:** May miss newly created repos during outage window
- **Recovery:** Automatic - tool resumes event polling after error clears

**Velocity Metric Staleness**
- **Scenario:** GitHub API returns cached data, 7-day metrics not updated
- **Behavior:** Tool uses stale data, may under-score genuinely active repos
- **Impact:** High-velocity repos may be temporarily missed
- **Recovery:** Next poll cycle fetches updated data

**IPFS Pinning Failure**
- **Scenario:** Local IPFS node down, Pinata API error, network timeout
- **Behavior:** Tool falls back to local CIDv1 generation
- **Impact:** CID valid but content not retrievable from IPFS network
- **Recovery:** Re-pin repo metadata manually using CID from database

**Database Corruption**
- **Scenario:** Disk full, SQLite lock timeout, process killed mid-write
- **Behavior:** SQLite `INSERT OR IGNORE` prevents duplicate repos
- **Impact:** May lose recent discoveries if transaction incomplete
- **Recovery:** Delete corrupted DB, tool rebuilds from next poll

**RSS Feed Gaming**
- **Scenario:** Spam repos dominate feed due to artificial velocity
- **Behavior:** Feed becomes noise-filled, legitimate repos buried
- **Impact:** Users lose trust in velocity-based discovery
- **Mitigation:** Implement spam detection heuristics (pending enhancement)

**GAR Integration File Lock**
- **Scenario:** Concurrent access to `gar_orgs.txt` by Radar and GAR
- **Behavior:** One process gets file lock error
- **Impact:** Temporary failure to write/read org list
- **Recovery:** Retry logic handles transient lock errors

### Security Best Practices

1. **Use GitHub Token:** Authenticate with `GITHUB_TOKEN` to avoid IP-based rate limiting
2. **Review High-Velocity Repos:** Manually inspect repos before trusting velocity scores
3. **Monitor Spam Patterns:** Periodically audit `radar_state.db` for anomalous repos
4. **Set Velocity Threshold:** Adjust GAR integration threshold based on topic noise levels
5. **Read-Only Tokens:** Use minimal-scope tokens for GitHub API access
6. **Audit GAR Feed List:** Review `gar_orgs.txt` before starting GAR daemon
7. **Rate Limit Monitoring:** Check logs for 403/429 responses indicating abuse
8. **Database Backups:** Periodically backup `radar_state.db` to preserve discovery history

### Velocity Scoring Validation

**Defining "Genuine" Velocity:**
- **High Commits + High Contributors + Sustained Activity** = Likely genuine
- **High Commits + Single Contributor + Burst Activity** = Possible spam
- **Many Forks + Low Commits** = Fork spam or template repo
- **High PRs + Low Merged Rate** = Possible PR spam

**Spam Detection Eval (Pending):**
- Manual review of top 100 velocity-scored repos
- Compare against human judgment of "innovation vs. noise"
- Identify false positives (spam repos scored high)
- Identify false negatives (innovative repos scored low)
- Refine scoring weights based on findings

## Architecture

```
┌─────────────────┐      ┌─────────────────┐
│  GitHub Events  │◄────►│  Repo Radar     │
│  API            │      │  Daemon         │
└─────────────────┘      │                 │
                         │  ┌───────────┐  │
┌─────────────────┐      │  │  SQLite   │  │
│  GitHub Search  │◄─────│  │  State    │  │
│  API            │      │  └───────────┘  │
└─────────────────┘      │                 │
                         │  ┌───────────┐  │
┌─────────────────┐      │  │  Velocity │  │
│  IPFS Network   │◄─────│  │  Scorer   │  │
│  (CIDv1 gen)    │      │  └───────────┘  │
└─────────────────┘      │                 │
                         │  ┌───────────┐  │
                         │  │  RSS Gen  │  │
                         │  └───────────┘  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  GAR Integration│
                         │  (gar_orgs.txt) │
                         └─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  GitHub Archive │
                         │  Relay (GAR)    │
                         └─────────────────┘
```

## Rate Limits

| Configuration | Requests/Hour | Recommended Use |
|--------------|---------------|-----------------|
| No token | 60 | Testing, single topic |
| With `GITHUB_TOKEN` | 5000 | Production, multiple topics |

For heavy monitoring of multiple topics, use a GitHub token.

## Examples

### Basic Usage (No Configuration)

```bash
# Monitor AI/ML repos
python repo-radar.py --watch ai,ml

# Monitor blockchain/web3 repos
python repo-radar.py --watch blockchain,web3,defi
```

This will:
- Poll every 300 seconds (default)
- Generate local CIDv1 for IPFS (content-addressable proof)
- Create RSS feed at `radar_feed.xml`
- Track top repos in `radar_state.db`

### With GitHub Token (Higher Rate Limits)

```bash
export GITHUB_TOKEN="ghp_your_token_here"
python repo-radar.py --watch ai,ml,blockchain --interval 120
```

This increases rate limits from 60/hr to 5000/hr, allowing more aggressive scanning.

### With IPFS Pinning (Pinata)

```bash
export GITHUB_TOKEN="ghp_your_token"
export PINATA_API_KEY="your_pinata_key"
export PINATA_SECRET_KEY="your_pinata_secret"

python repo-radar.py --watch ai,ml --interval 300
```

This will actually pin repo metadata to IPFS via Pinata.

### Integration with GAR (Discovery + Archiving Chain)

```bash
# Terminal 1: Run Repo Radar to discover high-velocity repos
export GITHUB_TOKEN="ghp_your_token"
python repo-radar.py --watch ai,ml,blockchain --interval 300

# Terminal 2: Run GAR to archive commits from discovered repos
cd ../gar
python github-archive-relay.py --orgs $(cat ../radar/gar_orgs.txt | tr '\n' ',') --interval 120
```

This creates a **discovery + archiving pipeline**:
1. Radar discovers repos by velocity
2. High-velocity repos (score > 50) are added to `gar_orgs.txt`
3. GAR polls those repos and archives commits to IPFS + Arweave
4. Both tools generate RSS feeds for unthrottleable discovery

### Run Once (No Daemon)

```bash
python repo-radar.py --watch ai --once
```

Useful for cron jobs or testing.

### Stats Mode

```bash
python repo-radar.py --stats
```

Shows discovered repos, velocity scores, and GAR integration status.

## RSS Feed Structure

The generated feed includes:

```xml
<item>
  <title>[repo-name] Short description</title>
  <link>https://github.com/owner/repo</link>
  <author>Owner Name</author>
  <description>
    <p><strong>Velocity Score:</strong> 127.5</p>
    <p><strong>Commits (7d):</strong> 42</p>
    <p><strong>Contributors:</strong> 8</p>
    <p><strong>Forks (7d):</strong> 5</p>
    <p><strong>PRs (7d):</strong> 12</p>
    <p><strong>Issues (7d):</strong> 7</p>
    <p><strong>IPFS:</strong> <a href="https://ipfs.io/ipfs/cid">cid</a></p>
  </description>
  <pubDate>...</pubDate>
</item>
```

Consumers can:
- Follow high-velocity repos in RSS readers
- Discover innovation early (before it goes viral)
- Verify metadata on IPFS
- Build decentralized discovery indexes

## How It Works

1. **Poll GitHub Events API** for new repo creation events
2. **Poll GitHub Search API** for repos matching watched topics
3. **Fetch velocity metrics** (commits, forks, contributors, PRs, issues over 7 days)
4. **Calculate velocity score** with time-weighted multipliers
5. **Check SQLite** to avoid duplicate processing
6. **Generate CIDv1** (or pin to IPFS if configured)
7. **Store in database** with scores and archive links
8. **Feed high-velocity repos to GAR** via `gar_orgs.txt`
9. **Regenerate RSS feed** ranked by velocity score

## Refinements in v1.1

Based on code review and testing, the following improvements were implemented:

### Fixed Function Placement
- Moved `_week_ago()` before first use in `search_repos_by_topic()`
- Prevents NameError on first run

### Accurate 7-Day Metrics
- **PRs:** Implemented `fetch_prs_count()` with proper `created_at` filtering
- **Issues:** Implemented `fetch_issues_count()` excluding pull_request key
- **Forks:** Implemented `fetch_forks_count()` with date filtering
- **Commits:** Already accurate via `since` parameter

Previously, forks and issues were approximated from total counts. Now all metrics are precise 7-day windows.

### Enhanced GAR Integration
- Checks for shared DB at `../gar/gar_state.db` (future-ready)
- Falls back to `gar_orgs.txt` file (current implementation)
- Logs appropriate messages for each integration method

### Comprehensive Error Handling
- Try/except blocks around all API calls
- Rate limit handling consistent with GAR (exponential backoff)
- Graceful degradation when services unavailable

## Troubleshooting

### Rate Limiting

```
[WARNING] Rate limited. Waiting 3600s until reset...
```

**Solution:** Set `GITHUB_TOKEN` for 5000 req/hr instead of 60.

### IPFS Connection Failed

```
[DEBUG] Local IPFS failed: Connection refused
```

**Solution:** Either:
1. Start local IPFS node: `ipfs daemon`
2. Configure Pinata API keys
3. Use default behavior (local CIDv1 generation)

### No Repos Discovered

```
Poll complete: 0 new repos
```

**Possible causes:**
- Topics too niche (try broader topics like "ai" or "blockchain")
- All repos already in database (check with `--stats`)
- Rate limit hit (check logs for 403/429 responses)

## Deployment

### Systemd Service

Create `/etc/systemd/system/radar.service`:

```ini
[Unit]
Description=Repo Radar - Velocity-Based Discovery
After=network.target

[Service]
Type=simple
User=radar
WorkingDirectory=/opt/radar
Environment="GITHUB_TOKEN=ghp_your_token"
ExecStart=/usr/bin/python3 /opt/radar/repo-radar.py --watch ai,ml,blockchain --interval 300
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable radar
sudo systemctl start radar
sudo systemctl status radar
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY repo-radar.py .
RUN pip install requests feedgen
CMD ["python", "repo-radar.py", "--watch", "ai,ml"]
```

Build and run:

```bash
docker build -t repo-radar .
docker run -d \
  -e GITHUB_TOKEN="ghp_your_token" \
  -v $(pwd)/data:/app \
  --name radar \
  repo-radar
```

### Cron Job

```cron
# Run every hour
0 * * * * cd /opt/radar && python3 repo-radar.py --watch ai,ml,blockchain --once >> /var/log/radar.log 2>&1
```

## Integration with HTCA

This tool aligns with HTCA's anti-gatekeeping philosophy:

- **Decentralized:** IPFS archiving for censorship resistance
- **Unthrottleable:** RSS feeds can't be rate-limited
- **Empirical:** Velocity-based scoring removes subjective bias
- **Open:** Single file, MIT licensed
- **Efficient:** Minimal dependencies, lightweight operation

Perfect for discovering fresh innovation that gatekept algorithms suppress.

## Chaining with GAR

The full discovery + archiving pipeline:

```
Repo Radar (Discovery)
  ↓
High-Velocity Repos → gar_orgs.txt
  ↓
GitHub Archive Relay (Archiving)
  ↓
Commits → IPFS + Arweave
  ↓
Unthrottleable RSS Feeds
```

This creates a **self-reinforcing discovery loop**:
1. Radar surfaces repos by activity
2. GAR archives commits from those repos
3. Both generate RSS feeds
4. Users discover innovation early and verify content on decentralized storage

## Performance Notes

- **CID generation:** ~70,000+ CIDs/second (local computation)
- **API calls per poll:** ~100-500 depending on topics and repo counts
- **Memory usage:** <50MB typical, SQLite handles state efficiently
- **Recommended interval:** 300s (5 minutes) with token, 600s without

## Future Enhancements

### Planned (Not Yet Implemented)

- [ ] **Contributor graph analysis:** Detect sudden team growth
- [ ] **Language trend detection:** Surface repos in emerging languages
- [ ] **Cross-topic correlation:** Find repos bridging multiple domains
- [ ] **Webhook support:** Real-time discovery via GitHub webhooks
- [ ] **Web dashboard:** Visual exploration of velocity trends

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to contribute these features.

## License

MIT License

Copyright (c) 2025 Anthony Vasquez / Temple of Two

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Built for the Temple. Science meets spirit in code.**

†⟡ Discovery by velocity, not vanity ⟡†
