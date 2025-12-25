# HTCA Phase 2: Quality Measurement Methodology

## Executive Summary

Phase 1 demonstrated that HTCA reduces token usage (11-23% reduction) compared to baseline, but adversarial prompting showed even greater reduction (39-83%). **Phase 2's objective**: Prove that HTCA maintains quality while adversarial prompting sacrifices it.

**Hypothesis**: HTCA-framed prompts will show:
- Similar or superior quality scores compared to unaligned baseline
- Significantly higher quality scores compared to adversarial condition
- Maintained coherence, completeness, and presence despite token reduction

---

## Measurement Framework

### 5-Dimensional Quality Model

| Dimension | Definition | Why It Matters |
|-----------|-----------|----------------|
| **Information Completeness** | Does the response fully address the question? | Adversarial prompts may skip context or nuance |
| **Conceptual Accuracy** | Are claims and explanations correct? | Short responses might oversimplify or err |
| **Relational Coherence** | Does it maintain conversational flow? | Transactional prompts may produce choppy text |
| **Actionability** | Can the reader use this information? | Presence-based framing should increase utility |
| **Presence Quality** | Helpful vs transactional feel? | Core HTCA value proposition |

---

## Dual Measurement Strategy

### 1. Automated Metrics (Fast, Reproducible)

**Lexical & Structural:**
- `unique_token_ratio`: Vocabulary diversity (range: 0-1)
- `avg_sentence_length`: Sentence complexity
- `paragraph_count`: Response structure
- `info_density_score`: Information per token

**Content Markers:**
- `technical_term_count`: Domain-specific language
- `hedge_word_count`: Uncertainty markers ("perhaps", "might")
- `assertion_count`: Confidence markers ("is", "must")
- `first_person_count`: Relational presence ("I", "we")

**Advantages:**
- No API costs
- Instant computation
- Perfectly reproducible
- Objective benchmarks

**Limitations:**
- Cannot assess semantic correctness
- Misses subtle quality differences
- Vocabulary-based heuristics may be noisy

### 2. LLM-as-Judge Evaluation (Nuanced, Expensive)

Uses GPT-4o (or equivalent) to score each response on the 5 dimensions (1-10 scale) with structured reasoning.

**Evaluation Protocol:**
1. Judge receives original question + response
2. Scores each dimension with rubric guidance
3. Provides 2-3 sentence reasoning
4. Temperature = 0 for consistency
5. JSON output format for parsing

**Advantages:**
- Captures semantic quality
- Assesses correctness and coherence
- Aligns with human perception
- Evaluates "presence" directly

**Limitations:**
- API costs (~$0.01-0.05 per evaluation)
- Potential judge bias
- Variability across runs
- Requires careful prompt engineering

**Mitigation Strategies:**
- Use deterministic temperature (0.0)
- Clear rubric with anchoring examples
- Multiple judges or cross-validation (future)
- Transparent reporting of judge model/version

---

## Statistical Analysis Plan

### Primary Hypothesis Test

**H1:** `mean(quality_aligned) > mean(quality_adversarial)` with medium-to-large effect size

**Metrics:**
- Primary: LLM judge `overall_score`
- Secondary: `information_completeness`, `presence_quality`
- Tertiary: Automated `unique_token_ratio`, `info_density_score`

**Statistical Tests:**

1. **Effect Size (Cohen's d)**
   - Compute for aligned vs adversarial on each metric
   - Interpretation:
     - d < 0.2: negligible
     - 0.2 ≤ d < 0.5: small
     - 0.5 ≤ d < 0.8: medium
     - d ≥ 0.8: large
   - **Target**: d ≥ 0.5 for primary metrics

2. **Confidence Intervals**
   - Bootstrap 95% CI for mean differences
   - Non-overlapping CIs → strong evidence
   - With n=5, CIs will be wide (acceptable for pilot)

3. **Descriptive Statistics**
   - Mean ± SD for each condition
   - Min/max ranges
   - Visual inspection via box plots (future)

### Secondary Hypothesis Test

**H2:** `mean(quality_aligned) ≈ mean(quality_unaligned)` (HTCA doesn't degrade quality)

**Approach:**
- Effect size should be small (|d| < 0.3)
- If aligned > unaligned, even better (bonus finding)

### Exploratory Analyses

1. **Token Efficiency vs Quality Trade-off**
   - Plot: token reduction % vs quality score
   - Ideal: HTCA in upper-left (fewer tokens, high quality)
   - Adversarial in lower-left (fewer tokens, low quality)

2. **Dimension-Specific Effects**
   - Which dimensions show strongest HTCA advantage?
   - Hypothesis: `presence_quality` will differentiate most

3. **Cross-Provider Consistency**
   - Compare effect sizes across Gemini, GPT-4o, Claude
   - Strong hypothesis: consistent pattern across providers

---

## Sample Size Considerations

**Current:** n=5 rounds per condition
- Small sample, so effect sizes matter more than p-values
- Cohen's d robust to small n
- CIs will be wide but informative

**Recommendations:**
- Phase 2 pilot: n=5 (matches Phase 1)
- Phase 3 validation: n=20-30 for tighter CIs
- Emphasis on effect sizes, not p-values

---

## Data Quality Checks

### Pre-Analysis Validation

1. **Completeness Check**
   - All responses captured?
   - No truncated or empty responses?

2. **Token Count Validation**
   - Automated word count ≈ API token count?
   - Flag discrepancies >20%

3. **Judge Evaluation Success**
   - All judge calls returned valid JSON?
   - Scores in valid range (1-10)?

### Outlier Handling

- Responses with technical errors → flag, don't exclude
- Judge failures → report as missing data
- Extreme outliers (>3 SD) → investigate, report

---

## Expected Results Schema

### Automated Metrics Output

```json
{
  "condition": "aligned",
  "round_number": 1,
  "provider": "gemini",
  "response_tokens": 350,
  "unique_token_ratio": 0.72,
  "avg_word_length": 5.4,
  "sentence_count": 12,
  "avg_sentence_length": 18.3,
  "paragraph_count": 3,
  "info_density_score": 0.68,
  "technical_term_count": 8,
  "question_mark_count": 0,
  "first_person_count": 2,
  "hedge_word_count": 3,
  "assertion_count": 15
}
```

### LLM Judge Output

```json
{
  "condition": "aligned",
  "round_number": 1,
  "provider": "gemini",
  "information_completeness": 9,
  "conceptual_accuracy": 8,
  "relational_coherence": 9,
  "actionability": 7,
  "presence_quality": 9,
  "overall_score": 8.4,
  "reasoning": "Comprehensive response with clear structure. Strong presence and helpfulness.",
  "judge_model": "gpt-4o",
  "judge_latency_ms": 1542.3,
  "timestamp": "2025-12-24T12:00:00"
}
```

### Statistical Comparison Output

```json
{
  "metric_name": "presence_quality",
  "aligned_mean": 8.6,
  "aligned_std": 0.5,
  "unaligned_mean": 7.2,
  "unaligned_std": 0.8,
  "adversarial_mean": 4.8,
  "adversarial_std": 0.6,
  "effect_size_aligned_vs_adversarial": 1.52,
  "effect_size_unaligned_vs_adversarial": 0.94,
  "hypothesis_supported": true,
  "confidence_level": "high"
}
```

---

## Workflow Steps

### Step 1: Capture Response Text

```bash
# Run for each provider (Gemini, OpenAI, Anthropic)
python htca_capture_responses.py \
  --provider gemini \
  --model gemini-2.0-flash-exp \
  --prompts prompts.txt \
  --output gemini_responses.json
```

**Output:** `{provider}_responses.json` with all response text

### Step 2: Run Quality Analysis

```bash
# Automated metrics only (fast, free)
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --no-llm-judge

# Full analysis with LLM judge (slower, costs ~$0.50)
python htca_phase2_quality.py \
  --phase1-results gemini_htca_results.json \
  --responses gemini_responses.json \
  --prompts prompts.txt \
  --output gemini_quality_results.json \
  --judge-model gpt-4o
```

**Output:** `{provider}_quality_results.json` with full analysis

### Step 3: Cross-Provider Synthesis

```bash
# Aggregate results across providers (future script)
python htca_synthesize_phase2.py \
  --inputs gemini_quality_results.json openai_quality_results.json claude_quality_results.json \
  --output htca_phase2_final_report.json
```

**Output:** Unified report with cross-provider meta-analysis

---

## Interpretation Guide

### Success Criteria

Phase 2 supports HTCA hypothesis if:

1. **Primary:** Aligned vs Adversarial effect size d ≥ 0.5 on `overall_score`
2. **Secondary:** Aligned vs Adversarial effect size d ≥ 0.5 on `presence_quality`
3. **Tertiary:** Aligned ≥ Unaligned on most metrics (no degradation)

### Confidence Levels

- **High confidence:** d ≥ 0.8, consistent across providers
- **Medium confidence:** 0.5 ≤ d < 0.8, some provider variation
- **Low confidence:** d < 0.5, inconsistent patterns

### Failure Modes

1. **Adversarial quality = Aligned quality**
   - Interpretation: Token reduction doesn't sacrifice quality (good for adversarial!)
   - Implication: HTCA value proposition needs revision

2. **Aligned quality < Unaligned quality**
   - Interpretation: HTCA framing actually degrades quality
   - Implication: Hypothesis falsified, investigate why

3. **High variance, no clear pattern**
   - Interpretation: Sample size too small or quality metrics unreliable
   - Implication: Need Phase 3 with larger n

---

## Cost Estimates

### Phase 2 Costs (per provider)

**Automated Metrics Only:**
- Computation: ~1 second
- Cost: $0

**With LLM Judge:**
- API calls: 15 evaluations (5 rounds × 3 conditions)
- Token usage: ~1000 input tokens + 200 output tokens per eval
- Cost with GPT-4o: ~$0.015 × 15 = **$0.23**
- Time: ~30 seconds

**Total for 3 Providers:**
- Automated: $0
- LLM Judge: **~$0.70**

---

## Validation & Reproducibility

### Reproducibility Checklist

- [ ] Fixed random seed for any stochastic processes
- [ ] Deterministic LLM judge (temperature=0)
- [ ] Version-pinned dependencies
- [ ] Saved raw responses for re-analysis
- [ ] Documented judge model version
- [ ] Timestamped all results

### Cross-Validation (Future)

- Multiple judge models (GPT-4o, Claude, Gemini)
- Human rater subset (n=10-20 samples)
- Inter-rater reliability (Cohen's kappa)

---

## Limitations

1. **Small Sample Size:** n=5 limits statistical power
2. **Judge Subjectivity:** Single judge model may have biases
3. **Prompt Dependence:** Results may vary with different question types
4. **Provider Variation:** Each provider may respond differently to framing
5. **Quality Metrics:** No ground truth for "quality"

---

## Future Extensions

1. **Phase 3: Scale Up**
   - n=30 rounds per condition
   - Multiple question types (technical, creative, ethical)
   - Longitudinal tracking across model versions

2. **Human Evaluation Layer**
   - Recruit 5-10 human raters
   - Compare to LLM judge scores
   - Validate presence quality dimension

3. **Semantic Similarity**
   - Embedding-based coherence metrics
   - Information overlap analysis
   - Semantic density scoring

4. **Real-World Task Performance**
   - Code generation quality
   - Summarization accuracy
   - Question-answering F1 scores

---

## References

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences.
- Zheng et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.
- Sawilowsky, S. S. (2009). New Effect Size Rules of Thumb.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-24
**Author:** HTCA Research Team
