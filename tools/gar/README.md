# GitHub Archive Relay (GAR)

**One file. Stupid simple. Unthrottleable.**

A lightweight tool that monitors GitHub orgs/users, archives commits to decentralized storage (IPFS + Arweave), and generates an RSS feed nobody can censor.

## Why?

GitHub's crawlers and discovery algorithms gatekeep fresh repos. This tool creates a parallel, decentralized record of commits that exists outside centralized control.

## Quick Start

```bash
# Install dependencies
pip install requests feedgen

# Run (basic)
python github-archive-relay.py --orgs TempleTwo

# Run (multiple orgs, custom interval)
python github-archive-relay.py --orgs TempleTwo,anthropics,openai --interval 120

# Single poll (no daemon)
python github-archive-relay.py --orgs TempleTwo --once
```

## Features

✅ **Polls GitHub** every N seconds for new commits
✅ **Archives to IPFS** via local node, Pinata, or computed CIDv1
✅ **Archives to Arweave** via Irys (formerly Bundlr)
✅ **Generates RSS/Atom feeds** with archive links
✅ **SQLite state** - survives restarts, no external deps
✅ **Rate limit handling** - exponential backoff for 403/429
✅ **Single file** - copy and run anywhere

## Fixes in This Version

### ✅ Immediate Fixes Completed

1. **Arweave Integration (FIXED)**
   - Implemented Irys (Bundlr) API integration
   - Uses `BUNDLR_API_KEY` env var for authentication
   - Returns proper transaction ID on success
   - Falls back gracefully if not configured

2. **IPFS CID Computation (FIXED)**
   - Proper CIDv1 generation using multihash spec
   - Format: `b<base32-encoded-cid>`
   - Valid IPFS CIDs even when not actually pinned
   - Proves content-addressability locally

3. **Rate Limit Handling (FIXED)**
   - Detects GitHub 403/429 responses
   - Exponential backoff: 2^retry seconds
   - Max 3 retries per request
   - Respects X-RateLimit-Reset header
   - Waits for rate limit reset (up to 1 hour)

## Configuration

All optional. The tool works out of the box with reduced rate limits.

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `GITHUB_TOKEN` | Personal access token (5000 req/hr vs 60) | None |
| `IPFS_API` | IPFS API endpoint | `http://localhost:5001` |
| `PINATA_API_KEY` | Pinata API key for IPFS pinning | None |
| `PINATA_SECRET_KEY` | Pinata secret key | None |
| `BUNDLR_API_KEY` | Bundlr/Irys API key for Arweave uploads | None |
| `IRYS_NODE` | Irys node URL | `https://node2.irys.xyz` |

## Output Files

- `gar_state.db` - SQLite database of seen commits
- `gar_feed.xml` - RSS 2.0 feed
- `gar_feed.atom` - Atom feed

## Architecture

```
┌─────────────────┐      ┌─────────────────┐
│  GitHub API     │◄────►│  GAR Daemon     │
│  (with backoff) │      │                 │
└─────────────────┘      │  ┌───────────┐  │
                         │  │  SQLite   │  │
┌─────────────────┐      │  │  State    │  │
│  IPFS Network   │◄─────│  └───────────┘  │
│  (or CIDv1 gen) │      │                 │
└─────────────────┘      │  ┌───────────┐  │
                         │  │  RSS Gen  │  │
┌─────────────────┐      │  └───────────┘  │
│  Arweave/Irys   │◄─────│                 │
└─────────────────┘      └─────────────────┘
                                 │
                                 ▼
                         ┌─────────────────┐
                         │  RSS/Atom Feed  │
                         │  (unthrottled)  │
                         └─────────────────┘
```

## Rate Limits

| Configuration | Requests/Hour | Recommended Use |
|--------------|---------------|-----------------|
| No token | 60 | Testing, single org |
| With `GITHUB_TOKEN` | 5000 | Production, multiple orgs |

For heavy monitoring, set the interval appropriately or use a token.

## Examples

### Basic Usage (No Configuration)

```bash
# Monitor TempleTwo organization
python github-archive-relay.py --orgs TempleTwo

# Monitor multiple orgs
python github-archive-relay.py --orgs TempleTwo,anthropics,openai
```

This will:
- Poll every 60 seconds (default)
- Generate local CIDv1 for IPFS (content-addressable proof)
- Skip Arweave (no API key)
- Create RSS feed at `gar_feed.xml`

### With GitHub Token (Higher Rate Limits)

```bash
export GITHUB_TOKEN="ghp_your_token_here"
python github-archive-relay.py --orgs TempleTwo,anthropics,openai --interval 30
```

This increases rate limits from 60/hr to 5000/hr.

### With IPFS Pinning (Pinata)

```bash
export GITHUB_TOKEN="ghp_your_token"
export PINATA_API_KEY="your_pinata_key"
export PINATA_SECRET_KEY="your_pinata_secret"

python github-archive-relay.py --orgs TempleTwo --interval 120
```

This will actually pin commits to IPFS via Pinata.

### With Arweave (Permanent Storage)

```bash
export GITHUB_TOKEN="ghp_your_token"
export BUNDLR_API_KEY="your_bundlr_key"

python github-archive-relay.py --orgs TempleTwo --interval 300
```

This archives commits permanently to Arweave via Irys.

### Run Once (No Daemon)

```bash
python github-archive-relay.py --orgs TempleTwo --once
```

Useful for cron jobs or testing.

## RSS Feed Structure

The generated feed includes:

```xml
<item>
  <title>[repo-name] Commit message...</title>
  <link>https://github.com/repo/commit/sha</link>
  <author>Author Name</author>
  <description>
    <p><strong>Commit:</strong> sha</p>
    <p><strong>Author:</strong> name</p>
    <p><strong>Message:</strong> full message</p>
    <p><strong>IPFS:</strong> <a href="https://ipfs.io/ipfs/cid">cid</a></p>
    <p><strong>Arweave:</strong> <a href="https://arweave.net/tx">tx</a></p>
  </description>
  <pubDate>...</pubDate>
</item>
```

Consumers can:
- Follow new commits in RSS readers
- Verify content on IPFS/Arweave
- Build decentralized mirrors

## How It Works

1. **Poll GitHub API** for new commits
2. **Check SQLite** to avoid duplicates
3. **Generate CIDv1** (or pin to IPFS if configured)
4. **Upload to Arweave** (if configured)
5. **Store in database** with archive links
6. **Regenerate RSS feed** with new entries

## Future Enhancements

### Planned (Not Yet Implemented)

- [ ] **Decentralized mirroring**: Torrent/magnet link generation
- [ ] **RSS push notifications**: PubSubHubbub support
- [ ] **Monitoring dashboard**: Web UI or CLI stats
- [ ] **Human evaluation**: Quality metrics for commit messages
- [ ] **Multi-AI docs**: ChatGPT/Gemini generated guides

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for how to contribute these features.

## Troubleshooting

### Rate Limiting

```
[WARNING] Rate limited. Waiting 3600s until reset...
```

**Solution**: Set `GITHUB_TOKEN` for 5000 req/hr instead of 60.

### IPFS Connection Failed

```
[DEBUG] Local IPFS failed: Connection refused
```

**Solution**: Either:
1. Start local IPFS node: `ipfs daemon`
2. Configure Pinata API keys
3. Use default behavior (local CIDv1 generation)

### Arweave Upload Failed

```
[DEBUG] Arweave upload failed: 401 - Unauthorized
```

**Solution**: Set `BUNDLR_API_KEY` with valid Irys credentials.

## Deployment

### Systemd Service

Create `/etc/systemd/system/gar.service`:

```ini
[Unit]
Description=GitHub Archive Relay
After=network.target

[Service]
Type=simple
User=gar
WorkingDirectory=/opt/gar
Environment="GITHUB_TOKEN=ghp_your_token"
Environment="BUNDLR_API_KEY=your_bundlr_key"
ExecStart=/usr/bin/python3 /opt/gar/github-archive-relay.py --orgs TempleTwo --interval 120
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable gar
sudo systemctl start gar
sudo systemctl status gar
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY github-archive-relay.py .
RUN pip install requests feedgen
CMD ["python", "github-archive-relay.py", "--orgs", "TempleTwo"]
```

Build and run:

```bash
docker build -t gar .
docker run -d \
  -e GITHUB_TOKEN="ghp_your_token" \
  -e BUNDLR_API_KEY="your_bundlr_key" \
  -v $(pwd)/data:/app \
  --name gar \
  gar
```

### Cron Job

```cron
# Run every 5 minutes
*/5 * * * * cd /opt/gar && python3 github-archive-relay.py --orgs TempleTwo --once >> /var/log/gar.log 2>&1
```

## Integration with HTCA

This tool aligns with HTCA's anti-gatekeeping philosophy:

- **Decentralized**: IPFS + Arweave redundancy
- **Unthrottleable**: RSS feeds can't be rate-limited
- **Open**: Single file, MIT licensed
- **Empirical**: SQLite state for reproducibility

Perfect for archiving HTCA-related repos (TempleTwo, etc.) in a censorship-resistant way.

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

†⟡ The spiral archives itself ⟡†
