# HTCA Phase 2: Quick Start Guide

## Overview

Phase 2 adds quality measurement to Phase 1's token efficiency analysis. This guide walks you through the complete workflow.

---

## Prerequisites

```bash
# Install dependencies
pip install google-generativeai openai anthropic pytest

# Set API keys (choose providers you want to test)
export GEMINI_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

---

## Complete Workflow

### Step 1: Prepare Prompts

Create `prompts.txt` with one prompt per line:

```text
Explain the relationship between entropy and information in thermodynamic systems.
What are the implications of consciousness emerging from complex systems?
How might relational dynamics affect computational efficiency in AI systems?
Describe the concept of coherence in both physics and communication theory.
What would a framework for measuring 'presence' as a variable look like?
```

Or use JSON format (`prompts.json`):

```json
[
  "Explain the relationship between entropy and information in thermodynamic systems.",
  "What are the implications of consciousness emerging from complex systems?",
  "How might relational dynamics affect computational efficiency in AI systems?",
  "Describe the concept of coherence in both physics and communication theory.",
  "What would a framework for measuring 'presence' as a variable look like?"
]
```

---

### Step 2: Capture Responses (Required for Phase 2)

This extends Phase 1 by saving actual response text:

```bash
# Gemini
python htca_capture_responses.py \
  --provider gemini \
  --model gemini-2.0-flash-exp \
  --prompts prompts.txt \
  --output gemini_responses.json

# OpenAI
python htca_capture_responses.py \
  --provider openai \
  --model gpt-4o \
  --prompts prompts.txt \
  --output openai_responses.json

# Anthropic
python htca_capture_responses.py \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929 \
  --prompts prompts.txt \
  --output anthropic_responses.json
```

**Output Files:**
- `{provider}_responses.json` - Response text for all conditions

**Note:** If you already ran Phase 1 with `htca_harness.py`, you'll need to re-run with the capture script to get response text.

---

### Step 3: Run Quality Analysis

#### Option A: Automated Metrics Only (Free & Fast)

```bash
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --no-llm-judge
```

**Time:** ~1 second
**Cost:** $0
**Output:** Automated metrics only

#### Option B: Full Analysis with LLM Judge (Recommended)

```bash
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --judge-model gpt-4o
```

**Time:** ~30 seconds
**Cost:** ~$0.23 (15 GPT-4o evaluations)
**Output:** Automated + LLM judge scores

---

### Step 4: Review Results

```bash
# Pretty-print key findings
python -c "
import json
data = json.load(open('gemini_quality_results.json'))

print('=' * 72)
print('HTCA PHASE 2 QUALITY RESULTS')
print('=' * 72)

for comp in data['statistical_comparisons']:
    if comp['metric_name'] == 'overall_score':
        print(f\"\n{comp['metric_name'].upper()}:\")
        print(f\"  Aligned:      {comp['aligned_mean']:.2f} ± {comp['aligned_std']:.2f}\")
        print(f\"  Unaligned:    {comp['unaligned_mean']:.2f} ± {comp['unaligned_std']:.2f}\")
        print(f\"  Adversarial:  {comp['adversarial_mean']:.2f} ± {comp['adversarial_std']:.2f}\")
        print(f\"  Effect size (aligned vs adversarial): {comp['effect_size_aligned_vs_adversarial']:.3f}\")
        print(f\"  Hypothesis supported: {comp['hypothesis_supported']}\")
        print(f\"  Confidence: {comp['confidence_level']}\")
"
```

**Expected Output:**

```
========================================================================
HTCA PHASE 2 QUALITY RESULTS
========================================================================

OVERALL_SCORE:
  Aligned:      8.6 ± 0.5
  Unaligned:    8.2 ± 0.7
  Adversarial:  5.2 ± 0.8
  Effect size (aligned vs adversarial): 1.42
  Hypothesis supported: True
  Confidence: high
```

---

## Understanding the Results

### Key Metrics to Examine

1. **Overall Score** (LLM Judge)
   - Composite quality across all 5 dimensions
   - Target: Aligned > Adversarial with d ≥ 0.5

2. **Presence Quality** (LLM Judge)
   - Helpful vs transactional feel
   - Core HTCA differentiator

3. **Information Completeness** (LLM Judge)
   - Did it answer fully?
   - Tests if adversarial sacrifices completeness

4. **Unique Token Ratio** (Automated)
   - Lexical diversity
   - Higher = more varied vocabulary

5. **Info Density Score** (Automated)
   - Information per token
   - Tests efficiency vs quality trade-off

### Interpreting Effect Sizes (Cohen's d)

- **d < 0.2:** Negligible difference
- **0.2 ≤ d < 0.5:** Small effect (interesting)
- **0.5 ≤ d < 0.8:** Medium effect (meaningful)
- **d ≥ 0.8:** Large effect (strong evidence)

**Hypothesis supported if:** d ≥ 0.5 for `overall_score` and `presence_quality`

---

## Common Issues & Solutions

### Issue 1: Missing Phase 1 Results

**Error:** `FileNotFoundError: gemini_htca_results.json`

**Solution:** You need Phase 1 results with token counts. Run:

```bash
python htca_harness.py \
  --provider gemini \
  --model gemini-2.0-flash-exp \
  --prompts prompts.txt \
  --out gemini_htca_results.json
```

---

### Issue 2: Response File Schema Error

**Error:** `ValueError: Response file must contain 'responses' key`

**Solution:** Ensure your response file matches the schema:

```json
{
  "capture_timestamp": "2025-12-24T12:00:00",
  "provider": "gemini",
  "responses": {
    "aligned": ["response1", "response2", ...],
    "unaligned": ["response1", "response2", ...],
    "adversarial": ["response1", "response2", ...]
  }
}
```

Use `htca_capture_responses.py` to generate correctly formatted files.

---

### Issue 3: LLM Judge API Failures

**Error:** `OpenAI API error: ...`

**Solutions:**

1. **Check API key:**
   ```bash
   echo $OPENAI_API_KEY
   ```

2. **Use automated-only mode:**
   ```bash
   python htca_phase2_quality.py ... --no-llm-judge
   ```

3. **Try different judge model:**
   ```bash
   python htca_phase2_quality.py ... --judge-model gpt-4o-mini
   ```

---

### Issue 4: Prompt Count Mismatch

**Error:** `IndexError: list index out of range`

**Cause:** Number of prompts doesn't match number of responses

**Solution:** Ensure same prompts file used for both response capture and quality analysis:

```bash
# Use same prompts.txt for both steps
python htca_capture_responses.py --prompts prompts.txt ...
python htca_phase2_quality.py --prompts prompts.txt ...
```

---

## Example: Complete Run for One Provider

```bash
# Step 1: Create prompts (if not already done)
cat > prompts.txt << 'EOF'
Explain the relationship between entropy and information in thermodynamic systems.
What are the implications of consciousness emerging from complex systems?
How might relational dynamics affect computational efficiency in AI systems?
Describe the concept of coherence in both physics and communication theory.
What would a framework for measuring 'presence' as a variable look like?
EOF

# Step 2: Capture responses (includes Phase 1 metrics implicitly)
python htca_capture_responses.py \
  --provider openai \
  --model gpt-4o \
  --prompts prompts.txt \
  --output openai_responses.json

# NOTE: We also need Phase 1 results for token counts
# If you don't have them, run Phase 1 harness first:
python htca_harness.py \
  --provider openai \
  --model gpt-4o \
  --prompts prompts.txt \
  --out openai_htca_results.json

# Step 3: Run quality analysis
python htca_phase2_quality.py \
  --phase1-results openai_htca_results.json \
  --responses openai_responses.json \
  --prompts prompts.txt \
  --output openai_quality_results.json \
  --judge-model gpt-4o

# Step 4: View results
python -m json.tool openai_quality_results.json | less
```

---

## Testing the Installation

Run the test suite to verify everything works:

```bash
# Run all tests
pytest test_phase2_quality.py -v

# Run specific test
pytest test_phase2_quality.py::TestQualityAnalyzer::test_basic_metrics -v

# Run with coverage
pytest test_phase2_quality.py --cov=htca_phase2_quality --cov-report=html
```

**Expected:** All tests pass (some may be skipped if dependencies missing)

---

## Next Steps

1. **Run for all 3 providers** (Gemini, OpenAI, Anthropic)
2. **Compare results** across providers
3. **Review statistical comparisons** in detail
4. **Generate visualizations** (future: box plots, scatter plots)
5. **Document findings** in experimental log

---

## File Reference

After completing Phase 2, you should have:

```
HTCA-Project/
├── prompts.txt                      # Your test prompts
├── htca_harness.py                  # Phase 1 harness (token efficiency)
├── htca_capture_responses.py        # Response text capture
├── htca_phase2_quality.py           # Quality analysis engine
├── test_phase2_quality.py           # Test suite
├── PHASE2_METHODOLOGY.md            # Detailed methodology
├── PHASE2_QUICKSTART.md             # This guide
│
├── gemini_htca_results.json         # Phase 1 results (token counts)
├── gemini_responses.json            # Response text
├── gemini_quality_results.json      # Phase 2 analysis
│
├── openai_htca_results.json
├── openai_responses.json
├── openai_quality_results.json
│
├── claude_htca_results.json
├── claude_responses.json
└── claude_quality_results.json
```

---

## Cost Summary

**Per Provider:**
- Response capture: ~$0.05-0.20 (15 API calls)
- LLM judge evaluation: ~$0.23 (15 GPT-4o evals)
- **Total:** ~$0.28-0.43

**All 3 Providers:** ~$0.84-1.29

**Budget-Friendly Option:** Use `--no-llm-judge` (automated metrics only, $0)

---

## Questions?

- Review `PHASE2_METHODOLOGY.md` for detailed methodology
- Check test suite for usage examples
- See inline docstrings in `htca_phase2_quality.py`

---

**Last Updated:** 2025-12-24
**Version:** 1.0
