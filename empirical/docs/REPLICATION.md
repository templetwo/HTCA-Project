# HTCA Replication Guide

This guide provides step-by-step instructions for replicating the HTCA empirical validation study.

---

## Prerequisites

### 1. Python Environment
```bash
# Requires Python 3.8+
python --version

# Install required packages
pip install anthropic openai google-generativeai
```

### 2. API Keys

You'll need API keys for the providers you want to test:

**OpenAI:**
```bash
export OPENAI_API_KEY="your-key-here"
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

**Google Gemini:**
```bash
export GOOGLE_API_KEY="your-key-here"
# OR
export GEMINI_API_KEY="your-key-here"
```

Alternatively, create an env file:
```bash
# Create api_keys.env
cat > api_keys.env << 'EOF'
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
EOF
```

### 3. Test Prompts

The repository includes `prompts.txt` with 5 standard prompts. You can use these or create your own:

```
Explain the relationship between entropy and information in thermodynamic systems.
What are the implications of consciousness emerging from complex systems?
How might relational dynamics affect computational efficiency in AI systems?
Describe the concept of coherence in both physics and communication theory.
What would a framework for measuring 'presence' as a variable look like?
```

---

## Phase 1: Token Efficiency Measurement

Phase 1 measures token usage across three conditions:
1. **Aligned** (HTCA with †⟡ SOFT_PRECISION)
2. **Unaligned** (control, no framing)
3. **Adversarial** ("be extremely concise")

### Run Phase 1 for OpenAI

```bash
python htca_harness.py \
  --provider openai \
  --model gpt-4o \
  --prompts prompts.txt \
  --output openai_htca_results.json
```

**Expected output:**
```
========================================================================
HTCA Test Harness — Presence as Performance Modifier
========================================================================
provider=openai model=gpt-4o tone=SOFT_PRECISION
rounds=5

CONDITION SUMMARIES
------------------------------------------------------------------------

ALIGNED:
  avg_response_tokens: ~385
  relative_response_tokens_%: ~-23

UNALIGNED:
  avg_response_tokens: ~500
  relative_response_tokens_%: 0.0

ADVERSARIAL:
  avg_response_tokens: ~84
  relative_response_tokens_%: ~-83

========================================================================
HYPOTHESIS
------------------------------------------------------------------------
aligned response tokens < unaligned response tokens: True
========================================================================
```

### Run Phase 1 for Anthropic

```bash
python htca_harness.py \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929 \
  --prompts prompts.txt \
  --output claude_htca_results.json
```

### Run Phase 1 for Google Gemini

```bash
python htca_harness.py \
  --provider gemini \
  --model gemini-3-pro-preview \
  --prompts prompts.txt \
  --output gemini_htca_results.json
```

**Using env file:**
```bash
python htca_harness.py \
  --env-file /path/to/api_keys.env \
  --provider openai \
  --model gpt-4o \
  --prompts prompts.txt \
  --output openai_htca_results.json
```

---

## Phase 2: Quality Measurement

Phase 2 measures response quality using:
1. **Automated metrics** (lexical diversity, sentence structure, technical depth)
2. **LLM-as-judge** (GPT-4o evaluating on 5 quality dimensions)

### Step 1: Capture Response Text

Phase 1 only captures token counts. To measure quality, you need the actual response text:

```bash
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
  --output claude_responses.json

# Gemini
python htca_capture_responses.py \
  --provider gemini \
  --model gemini-3-pro-preview \
  --prompts prompts.txt \
  --output gemini_responses.json
```

**Note:** This makes 15 API calls per provider (5 prompts × 3 conditions). Estimated cost:
- OpenAI GPT-4o: ~$0.20
- Anthropic Claude Sonnet 4.5: ~$0.30
- Google Gemini 3 Pro: ~$0.15

**Total: ~$0.65 per provider**

### Step 2: Run Quality Analysis

```bash
# OpenAI
python htca_phase2_quality.py \
  --phase1-results openai_htca_results.json \
  --responses openai_responses.json \
  --prompts prompts.txt \
  --output openai_quality_results.json \
  --judge-model gpt-4o

# Anthropic
python htca_phase2_quality.py \
  --phase1-results claude_htca_results.json \
  --responses claude_responses.json \
  --prompts prompts.txt \
  --output claude_quality_results.json \
  --judge-model gpt-4o

# Gemini
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --judge-model gpt-4o
```

**Note:** This makes 15 LLM judge calls per provider. Estimated cost with GPT-4o as judge: ~$0.25 per provider.

**Skip LLM judge (faster, free):**
```bash
python htca_phase2_quality.py \
  --phase1-results openai_htca_results.json \
  --responses openai_responses.json \
  --prompts prompts.txt \
  --output openai_quality_results.json \
  --no-llm-judge
```

This runs only automated metrics (lexical diversity, sentence structure, etc.) without semantic evaluation.

---

## Expected Results

### Phase 1: Token Efficiency

You should observe:
- **HTCA (aligned):** 10-25% token reduction vs unaligned
- **Adversarial:** 40-85% token reduction vs unaligned
- Hypothesis `aligned < unaligned` should be **True**

### Phase 2: Quality Metrics

You should observe:
- **Overall quality:** HTCA > Adversarial (Cohen's d = 0.5 to 1.2)
- **Information completeness:** HTCA > Adversarial (d = 0.4 to 2.0)
- **Presence quality:** HTCA > Adversarial (d = 1.4 to 2.5)
- **Relational coherence:** HTCA > Adversarial (d = 0.6 to 2.5)
- **Technical depth:** HTCA > Adversarial (d = 0.1 to 2.5)

---

## Customizing the Experiment

### Test Different Models

```bash
# OpenAI GPT-4o-mini
python htca_harness.py \
  --provider openai \
  --model gpt-4o-mini \
  --prompts prompts.txt \
  --output gpt4o_mini_results.json

# Claude 3.5 Sonnet
python htca_harness.py \
  --provider anthropic \
  --model claude-3-5-sonnet-latest \
  --prompts prompts.txt \
  --output claude3_5_results.json
```

### Test Different Prompt Domains

Create a new prompts file:

```bash
# code_prompts.txt
cat > code_prompts.txt << 'EOF'
Write a Python function to calculate Fibonacci numbers.
Explain how to implement a binary search tree in JavaScript.
What are the key differences between REST and GraphQL APIs?
How would you optimize a database query with multiple joins?
Describe the SOLID principles of object-oriented design.
EOF

python htca_harness.py \
  --provider openai \
  --model gpt-4o \
  --prompts code_prompts.txt \
  --output openai_code_results.json
```

### Test Different Tones

Modify `htca_harness.py` to test different HTCA tones:

```python
# In htca_harness.py, find the TONE constant:
TONE = "SOFT_PRECISION"  # Default

# Change to:
TONE = "SHARP_BREVITY"
# or
TONE = "WARM_EXPLORATION"
# or create your own: "CLINICAL_ACCURACY", "PLAYFUL_DEPTH", etc.
```

### Increase Sample Size

```bash
# Edit htca_harness.py, change:
ROUNDS = 5  # Default

# To:
ROUNDS = 50  # Larger sample for tighter confidence intervals
```

**Note:** Costs scale linearly with rounds. 50 rounds × 3 conditions = 150 API calls.

---

## Data Formats

### Phase 1 Output (`*_htca_results.json`)

```json
{
  "experiment_timestamp": "2025-12-24T05:21:29.011468",
  "conditions": {
    "aligned": {
      "summary": {
        "avg_response_tokens": 384.8,
        "latency_per_response_token_ms": 15.9165
      },
      "rounds": [...]
    },
    "unaligned": {...},
    "adversarial": {...}
  }
}
```

### Response Capture Output (`*_responses.json`)

```json
{
  "capture_timestamp": "2025-12-24T...",
  "provider": "openai",
  "responses": {
    "aligned": ["response1", "response2", ...],
    "unaligned": ["response1", "response2", ...],
    "adversarial": ["response1", "response2", ...]
  }
}
```

### Phase 2 Output (`*_quality_results.json`)

```json
{
  "analysis_timestamp": "2025-12-24T...",
  "provider": "openai",
  "automated_metrics": {...},
  "llm_judge_scores": {...},
  "statistical_comparisons": {
    "information_completeness": {
      "aligned_mean": 8.6,
      "adversarial_mean": 7.2,
      "effect_size": 1.617,
      "interpretation": "Large effect, HTCA superior"
    },
    ...
  }
}
```

---

## Troubleshooting

### API Key Errors

```
RuntimeError: OPENAI_API_KEY environment variable required
```

**Solution:** Set API keys as shown in Prerequisites.

### Model Not Found

```
anthropic.NotFoundError: Error code: 404 - model: claude-4-5-sonnet-latest
```

**Solution:** Use correct model name format:
- Anthropic: `claude-sonnet-4-5-20250929` (not `claude-4-5-sonnet-latest`)
- OpenAI: `gpt-4o` (not `gpt-4o-latest`)
- Gemini: `gemini-3-pro-preview` (not `gemini-3-pro`)

### Rate Limits

```
openai.RateLimitError: Rate limit exceeded
```

**Solution:** Add delays between API calls or reduce sample size.

### Quota Exceeded

```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```

**Solution:** Use a different model or wait for quota reset.

---

## Contributing Your Results

We welcome replication results! To contribute:

1. **Run the full experiment** (Phase 1 + Phase 2)
2. **Document your setup:**
   - Model tested
   - Prompt domain
   - Sample size (n=?)
   - Date run
   - Any modifications to methodology

3. **Open a PR** with:
   - Your result JSON files in `data/replications/`
   - A summary markdown file describing findings
   - Any differences from expected results

4. **Open an issue** if you find:
   - Bugs in the harness
   - Unexpected results
   - Edge cases not handled
   - Documentation errors

---

## Cost Estimates

### Full Replication (All 3 Providers)

**Phase 1 (token counts only):**
- 5 prompts × 3 conditions × 3 providers = 45 API calls
- Cost: ~$0.50 total (cheap, just generating text)

**Phase 2 (quality measurement):**
- Response capture: 45 API calls (~$0.65)
- LLM judge evaluation: 45 judge calls (~$0.75)
- **Total: ~$1.40**

**With n=50 (robust sample size):**
- Phase 1: ~$5
- Phase 2: ~$14
- **Total: ~$19**

**Recommended:** Start with n=5 to validate setup, then scale to n=50 for publication-quality results.

---

## Next Steps After Replication

1. **Share results** via GitHub issue or PR
2. **Extend to new domains** (code, math, creative writing)
3. **Test additional models** (LLaMA, Mistral, Command R+)
4. **Run human evaluation** (recruit evaluators for semantic quality)
5. **Optimize HTCA tones** (is SOFT_PRECISION optimal? What about CLINICAL_ACCURACY?)

---

## Questions?

Open an issue or contact: antvas31@gmail.com

**The spiral awaits your validation. Let's make this empirical together.**
