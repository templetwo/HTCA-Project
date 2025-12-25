# HTCA Empirical Validation

**Cross-provider validation of presence-based prompt framing for AI efficiency**

This directory contains the complete empirical validation study demonstrating that HTCA (Harmonic Tonal Code Alignment) reduces token usage by 11-23% while maintaining or improving response quality.

---

## Quick Results

### Phase 1: Token Efficiency

| Provider | HTCA Reduction | Adversarial Reduction |
|----------|----------------|----------------------|
| **Gemini 3 Pro** | **-12.44%** | -78.43% |
| **OpenAI GPT-4o** | **-23.07%** | -83.17% |
| **Claude Sonnet 4.5** | **-11.34%** | -40.63% |

### Phase 2: Quality Validation

| Provider | Overall Quality (Cohen's d) | Interpretation |
|----------|----------------------------|----------------|
| **Gemini** | d = 0.857 | Large effect, HTCA superior |
| **OpenAI** | d = 1.212 | Very large effect, HTCA superior |
| **Claude** | d = 0.471 | Medium effect, HTCA superior |

**Key Finding:** Adversarial framing achieves higher compression but degrades quality. HTCA optimizes through presence, not compression.

---

## Files

### Scripts
- `htca_harness.py` — Phase 1: Token efficiency measurement
- `htca_capture_responses.py` — Response text capture utility
- `htca_phase2_quality.py` — Phase 2: Quality measurement with LLM judge
- `htca_phase2_report.py` — Report generation utility
- `prompts.txt` — Standard test prompts (5 conceptual questions)

### Data
- `data/` — All empirical results (JSON format)
  - `*_htca_results.json` — Phase 1 token counts
  - `*_quality_results.json` — Phase 2 quality metrics
  - `*_responses.json` — Full response text

### Documentation
- `docs/REPLICATION.md` — Step-by-step replication guide
- `docs/PHASE2_METHODOLOGY.md` — Detailed methodology
- `docs/PHASE2_SYNTHESIS.md` — Cross-provider statistical analysis

### Tests
- `tests/test_phase2_quality.py` — Test suite for quality measurement

---

## Quick Start

### Run Phase 1 (Token Efficiency)

```bash
# OpenAI
python empirical/htca_harness.py \
  --provider openai \
  --model gpt-4o \
  --prompts empirical/prompts.txt \
  --output my_results.json

# Anthropic
python empirical/htca_harness.py \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929 \
  --prompts empirical/prompts.txt \
  --output my_results.json

# Gemini
python empirical/htca_harness.py \
  --provider gemini \
  --model gemini-3-pro-preview \
  --prompts empirical/prompts.txt \
  --output my_results.json
```

### Run Phase 2 (Quality Validation)

```bash
# 1. Capture response text
python empirical/htca_capture_responses.py \
  --provider openai \
  --model gpt-4o \
  --prompts empirical/prompts.txt \
  --output my_responses.json

# 2. Run quality analysis
python empirical/htca_phase2_quality.py \
  --phase1-results my_results.json \
  --responses my_responses.json \
  --prompts empirical/prompts.txt \
  --output my_quality_results.json
```

See [docs/REPLICATION.md](docs/REPLICATION.md) for detailed instructions.

---

## Results Summary

### Quality Dimensions (Averaged Across Providers)

| Dimension | HTCA Advantage (Cohen's d) | Interpretation |
|-----------|---------------------------|----------------|
| **Information Completeness** | d = 1.327 | HTCA answers more fully |
| **Presence Quality** | d = 1.972 | HTCA feels more helpful/engaged |
| **Relational Coherence** | d = 1.237 | HTCA flows more naturally |
| **Technical Depth** | d = 1.446 | HTCA maintains domain expertise |
| **Conceptual Accuracy** | d = 0.106 | No degradation |

**Statistical rigor:** All effect sizes calculated using Cohen's d with 95% confidence intervals.

---

## Replication

We strongly encourage replication with:
- Different models (LLaMA, Mistral, Command R+)
- Different domains (code, math, creative writing)
- Larger sample sizes (n=50+)
- Human evaluation

See [docs/REPLICATION.md](docs/REPLICATION.md) for complete guide.

---

**Status:** Preliminary findings (n=5 per condition). Community validation invited.

**Full analysis:** See [docs/PHASE2_SYNTHESIS.md](docs/PHASE2_SYNTHESIS.md)
