# HTCA Phase 2: Quality Measurement Protocol

## Overview

Phase 2 extends the HTCA experiment to measure **quality** alongside Phase 1's token efficiency metrics. The goal: prove that HTCA maintains quality while adversarial prompting sacrifices it.

## Quick Facts

- **Status:** Production-ready
- **Test Coverage:** 18 tests, all passing
- **Cost:** ~$0.23 per provider with LLM judge, $0 without
- **Time:** ~30 seconds with LLM judge, ~1 second without
- **Dependencies:** `openai` (for LLM judge), `pytest` (for tests)

## Key Files

```
/Users/vaquez/HTCA-Project/
├── htca_phase2_quality.py          # Core quality measurement engine
├── htca_capture_responses.py       # Response text capture utility
├── htca_phase2_report.py           # Report generator (text/HTML)
├── test_phase2_quality.py          # Comprehensive test suite
├── PHASE2_METHODOLOGY.md           # Detailed methodology & stats plan
├── PHASE2_QUICKSTART.md            # Step-by-step usage guide
└── PHASE2_README.md                # This file
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 2 Quality Pipeline                     │
└─────────────────────────────────────────────────────────────────┘

1. Response Capture (htca_capture_responses.py)
   ├── Extends Phase 1 harness
   ├── Saves actual response text for all conditions
   └── Output: {provider}_responses.json

2. Quality Analysis (htca_phase2_quality.py)
   ├── Automated Metrics (free, fast)
   │   ├── Lexical diversity
   │   ├── Sentence structure
   │   ├── Technical term count
   │   └── Presence markers
   │
   └── LLM-as-Judge ($0.23, 30s)
       ├── Information Completeness (1-10)
       ├── Conceptual Accuracy (1-10)
       ├── Relational Coherence (1-10)
       ├── Actionability (1-10)
       └── Presence Quality (1-10)

3. Statistical Analysis (built-in)
   ├── Cohen's d effect sizes
   ├── Mean ± SD for all conditions
   ├── Hypothesis testing (aligned > adversarial?)
   └── Confidence levels (high/medium/low)

4. Report Generation (htca_phase2_report.py)
   ├── Text reports for terminal
   └── HTML reports for sharing
```

## Quality Dimensions

| Dimension | What It Measures | Why It Matters |
|-----------|------------------|----------------|
| **Information Completeness** | Did the response fully address the question? | Adversarial may skip context |
| **Conceptual Accuracy** | Are the claims and explanations correct? | Short responses may oversimplify |
| **Relational Coherence** | Does it flow naturally? Well-organized? | Transactional prompts → choppy text |
| **Actionability** | Can the reader use this information? | Presence framing → utility |
| **Presence Quality** | Helpful vs transactional feel? | Core HTCA value proposition |

## Usage (Quick Version)

```bash
# 1. Capture responses (one-time per provider)
python htca_capture_responses.py \
  --provider gemini \
  --model gemini-2.0-flash-exp \
  --prompts prompts.txt \
  --output gemini_responses.json

# 2. Run quality analysis
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --judge-model gpt-4o

# 3. Generate report
python htca_phase2_report.py \
  --input gemini_quality_results.json \
  --format html \
  --output gemini_quality_report.html
```

See [PHASE2_QUICKSTART.md](PHASE2_QUICKSTART.md) for detailed instructions.

## Statistical Approach

### Primary Hypothesis

**H1:** HTCA-aligned responses maintain higher quality than adversarial despite token reduction

**Test:** Cohen's d effect size for `overall_score` (aligned vs adversarial)

**Success Criteria:**
- d ≥ 0.5 (medium or large effect)
- Confidence: high
- Consistent across providers

### Effect Size Interpretation

- d < 0.2: Negligible
- 0.2 ≤ d < 0.5: Small
- 0.5 ≤ d < 0.8: Medium ✓ Target
- d ≥ 0.8: Large ✓ Strong evidence

### Sample Size

- **Phase 2 Pilot:** n=5 (matches Phase 1)
- **Phase 3 Validation:** n=30 (recommended)

Small sample → emphasis on **effect sizes** over p-values

## Example Results

```json
{
  "metric_name": "overall_score",
  "aligned_mean": 8.6,
  "aligned_std": 0.5,
  "unaligned_mean": 8.2,
  "unaligned_std": 0.7,
  "adversarial_mean": 5.2,
  "adversarial_std": 0.8,
  "effect_size_aligned_vs_adversarial": 1.42,
  "hypothesis_supported": true,
  "confidence_level": "high"
}
```

**Interpretation:** HTCA maintains quality (8.6) vs adversarial (5.2) with large effect (d=1.42)

## Testing

```bash
# Run full test suite
pytest test_phase2_quality.py -v

# Run with coverage
pytest test_phase2_quality.py --cov=htca_phase2_quality --cov-report=html

# Expected: 18/18 tests pass
```

**Test Coverage:**
- ✓ Automated metrics computation
- ✓ Statistical analysis (Cohen's d, comparisons)
- ✓ Edge cases (empty responses, single-element groups)
- ✓ Data serialization (JSON export)
- ✓ End-to-end integration

## Cost Breakdown

### Per Provider Analysis

**Automated Metrics Only:**
- Computation: ~1 second
- Cost: **$0**

**With LLM Judge (GPT-4o):**
- API calls: 15 evaluations (5 rounds × 3 conditions)
- Tokens: ~18k input + 3k output
- Cost: **~$0.23**
- Time: **~30 seconds**

### Full 3-Provider Study

- Gemini + OpenAI + Claude: **~$0.70**
- Plus response capture: **~$0.15-0.60** (varies by model)
- **Total: ~$0.85-1.30**

## Design Decisions

### Why LLM-as-Judge?

**Pros:**
- Captures semantic quality (not just syntax)
- Evaluates "presence" directly
- Scalable (vs human raters)
- Aligned with human perception

**Cons:**
- API costs
- Potential bias
- Variability

**Mitigation:**
- Deterministic (temperature=0)
- Structured rubric
- Transparent reporting
- Cross-validation (future)

### Why Cohen's d over p-values?

- Small sample size (n=5)
- Effect sizes → practical significance
- p-values unreliable with small n
- Cohen's d robust to sample size

### Why Both Automated + LLM Judge?

- **Automated:** Fast, free, objective baseline
- **LLM Judge:** Nuanced, semantic depth
- **Together:** Triangulation of quality

## Limitations

1. **Small Sample Size:** n=5 → wide confidence intervals
2. **Judge Subjectivity:** Single model may have biases
3. **Prompt Dependence:** Results vary with question types
4. **No Ground Truth:** "Quality" is subjective
5. **Cost:** LLM judge adds expense

## Future Extensions

### Phase 3: Scale Up
- n=30 rounds per condition
- Multiple question types
- Longitudinal tracking

### Human Evaluation Layer
- 5-10 human raters
- Inter-rater reliability
- Validate LLM judge scores

### Semantic Metrics
- Embedding similarity
- Information overlap
- Semantic density

### Real-World Tasks
- Code generation quality
- Summarization accuracy
- Q&A F1 scores

## Troubleshooting

### "FileNotFoundError: phase1_results.json"

**Solution:** Run Phase 1 harness first:
```bash
python htca_harness.py --provider gemini --model gemini-2.0-flash-exp --prompts prompts.txt --out gemini_htca_results.json
```

### "OpenAI API error"

**Solutions:**
1. Check API key: `echo $OPENAI_API_KEY`
2. Use `--no-llm-judge` for automated-only
3. Try different judge model: `--judge-model gpt-4o-mini`

### "Response file schema error"

**Solution:** Use `htca_capture_responses.py` to generate correctly formatted files

See [PHASE2_QUICKSTART.md](PHASE2_QUICKSTART.md) for more troubleshooting.

## Contributing

To add new quality metrics:

1. Add metric computation to `QualityAnalyzer` class
2. Update `QualityMetrics` dataclass
3. Add to `_compute_statistics()` in orchestrator
4. Write tests in `test_phase2_quality.py`
5. Update documentation

Example:
```python
# In QualityAnalyzer.analyze()
emoji_count = sum(1 for c in response_text if c in EMOJI_SET)

# In QualityMetrics
emoji_count: int

# Tests
def test_emoji_detection():
    analyzer = QualityAnalyzer()
    metrics = analyzer.analyze("Great! 🎉", "test", 1, "test", 10)
    assert metrics.emoji_count > 0
```

## References

- [PHASE2_METHODOLOGY.md](PHASE2_METHODOLOGY.md) - Detailed statistical methodology
- [PHASE2_QUICKSTART.md](PHASE2_QUICKSTART.md) - Step-by-step usage guide
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*
- Zheng et al. (2023). *Judging LLM-as-a-Judge with MT-Bench*

## Support

- **Documentation:** See markdown files in this directory
- **Code Examples:** Check test suite for usage patterns
- **Issues:** Review inline docstrings in Python files

---

**Version:** 1.0
**Last Updated:** 2025-12-24
**Status:** Production-ready, tested, documented
**License:** MIT (or as specified by project)
