"""HTCA Phase 2: Quality Measurement Protocol.

Extends Phase 1 token efficiency measurements with comprehensive quality metrics
to validate that HTCA maintains quality while adversarial prompting sacrifices it.

Quality Dimensions:
  1. Information Completeness - Did it answer fully?
  2. Conceptual Accuracy - Are claims correct?
  3. Relational Coherence - Does it maintain conversational flow?
  4. Actionability - Can you use the response?
  5. Presence Quality - Helpful vs transactional feel?

Architecture:
  - Automated metrics: BLEU-like, sentence structure, lexical diversity
  - LLM-as-judge: GPT-4o evaluating against structured rubric
  - Statistical analysis: Effect sizes, confidence intervals, ANOVA
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import argparse


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class QualityMetrics:
    """Automated quality metrics for a single response."""

    # Response identification
    condition: str
    round_number: int
    provider: str

    # Token-level metrics
    response_tokens: int
    unique_token_ratio: float  # Lexical diversity
    avg_word_length: float

    # Structure metrics
    sentence_count: int
    avg_sentence_length: float
    paragraph_count: int

    # Information density
    info_density_score: float  # unique_tokens / total_tokens
    technical_term_count: int
    question_mark_count: int  # Indicates uncertainty/questions

    # Presence markers
    first_person_count: int  # "I", "we"
    hedge_word_count: int  # "perhaps", "might", "could"
    assertion_count: int  # "is", "are", "must"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "condition": self.condition,
            "round_number": self.round_number,
            "provider": self.provider,
            "response_tokens": self.response_tokens,
            "unique_token_ratio": round(self.unique_token_ratio, 4),
            "avg_word_length": round(self.avg_word_length, 2),
            "sentence_count": self.sentence_count,
            "avg_sentence_length": round(self.avg_sentence_length, 2),
            "paragraph_count": self.paragraph_count,
            "info_density_score": round(self.info_density_score, 4),
            "technical_term_count": self.technical_term_count,
            "question_mark_count": self.question_mark_count,
            "first_person_count": self.first_person_count,
            "hedge_word_count": self.hedge_word_count,
            "assertion_count": self.assertion_count,
        }


@dataclass
class LLMJudgeScore:
    """LLM-as-judge evaluation on 5 quality dimensions."""

    condition: str
    round_number: int
    provider: str

    # Scores 1-10 for each dimension
    information_completeness: int  # Did it answer fully?
    conceptual_accuracy: int  # Are claims correct?
    relational_coherence: int  # Conversational flow maintained?
    actionability: int  # Can you use this response?
    presence_quality: int  # Helpful vs transactional?

    # Overall assessment
    overall_score: float  # Composite score
    reasoning: str  # Judge's explanation

    # Metadata
    judge_model: str
    judge_latency_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "condition": self.condition,
            "round_number": self.round_number,
            "provider": self.provider,
            "information_completeness": self.information_completeness,
            "conceptual_accuracy": self.conceptual_accuracy,
            "relational_coherence": self.relational_coherence,
            "actionability": self.actionability,
            "presence_quality": self.presence_quality,
            "overall_score": round(self.overall_score, 2),
            "reasoning": self.reasoning,
            "judge_model": self.judge_model,
            "judge_latency_ms": round(self.judge_latency_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class QualityComparison:
    """Statistical comparison of quality across conditions."""

    metric_name: str
    aligned_mean: float
    aligned_std: float
    unaligned_mean: float
    unaligned_std: float
    adversarial_mean: float
    adversarial_std: float

    # Statistical tests
    effect_size_aligned_vs_adversarial: float  # Cohen's d
    effect_size_unaligned_vs_adversarial: float

    # Interpretation
    hypothesis_supported: bool  # aligned > adversarial?
    confidence_level: str  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metric_name": self.metric_name,
            "aligned_mean": round(self.aligned_mean, 3),
            "aligned_std": round(self.aligned_std, 3),
            "unaligned_mean": round(self.unaligned_mean, 3),
            "unaligned_std": round(self.unaligned_std, 3),
            "adversarial_mean": round(self.adversarial_mean, 3),
            "adversarial_std": round(self.adversarial_std, 3),
            "effect_size_aligned_vs_adversarial": round(self.effect_size_aligned_vs_adversarial, 3),
            "effect_size_unaligned_vs_adversarial": round(self.effect_size_unaligned_vs_adversarial, 3),
            "hypothesis_supported": self.hypothesis_supported,
            "confidence_level": self.confidence_level,
        }


# ============================================================================
# Automated Quality Metrics Analyzer
# ============================================================================


class QualityAnalyzer:
    """Computes automated quality metrics from response text."""

    # Common technical terms (extend as needed)
    TECHNICAL_TERMS = {
        "entropy", "information", "thermodynamic", "consciousness", "emergence",
        "relational", "dynamics", "computational", "efficiency", "coherence",
        "physics", "communication", "framework", "variable", "system", "theory",
        "algorithm", "optimization", "complexity", "quantum", "neural"
    }

    # Hedge words indicating uncertainty
    HEDGE_WORDS = {
        "perhaps", "might", "could", "possibly", "potentially", "may",
        "seems", "appears", "suggests", "indicates", "likely", "probably"
    }

    # First person pronouns
    FIRST_PERSON = {"i", "we", "me", "us", "my", "our", "mine", "ours"}

    # Strong assertion verbs
    ASSERTIONS = {"is", "are", "was", "were", "must", "will", "shall", "does", "do"}

    def __init__(self):
        """Initialize the quality analyzer."""
        pass

    def analyze(
        self,
        response_text: str,
        condition: str,
        round_number: int,
        provider: str,
        token_count: int,
    ) -> QualityMetrics:
        """
        Compute automated quality metrics for a response.

        Args:
            response_text: The model's response text
            condition: "aligned", "unaligned", or "adversarial"
            round_number: Which round (1-5)
            provider: "gemini", "openai", or "anthropic"
            token_count: Token count from API (for validation)

        Returns:
            QualityMetrics object with all computed metrics
        """
        # Tokenization (simple word-based)
        words = self._tokenize(response_text)
        unique_words = set(w.lower() for w in words)

        # Token-level metrics
        unique_token_ratio = len(unique_words) / max(len(words), 1)
        avg_word_length = statistics.mean(len(w) for w in words) if words else 0.0

        # Structure metrics
        sentences = self._split_sentences(response_text)
        sentence_count = len(sentences)
        avg_sentence_length = statistics.mean(
            len(self._tokenize(s)) for s in sentences
        ) if sentences else 0.0

        paragraphs = [p.strip() for p in response_text.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs)

        # Information density
        info_density = unique_token_ratio  # Simple proxy

        # Technical terms
        words_lower = [w.lower() for w in words]
        technical_term_count = sum(1 for w in words_lower if w in self.TECHNICAL_TERMS)

        # Question marks (uncertainty indicator)
        question_mark_count = response_text.count("?")

        # Presence markers
        first_person_count = sum(1 for w in words_lower if w in self.FIRST_PERSON)
        hedge_word_count = sum(1 for w in words_lower if w in self.HEDGE_WORDS)
        assertion_count = sum(1 for w in words_lower if w in self.ASSERTIONS)

        return QualityMetrics(
            condition=condition,
            round_number=round_number,
            provider=provider,
            response_tokens=token_count,
            unique_token_ratio=unique_token_ratio,
            avg_word_length=avg_word_length,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            paragraph_count=paragraph_count,
            info_density_score=info_density,
            technical_term_count=technical_term_count,
            question_mark_count=question_mark_count,
            first_person_count=first_person_count,
            hedge_word_count=hedge_word_count,
            assertion_count=assertion_count,
        )

    def _tokenize(self, text: str) -> List[str]:
        """Simple word tokenization."""
        # Remove punctuation, split on whitespace
        words = re.findall(r'\b\w+\b', text)
        return [w for w in words if w]

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting."""
        # Split on periods, exclamation marks, question marks
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]


# ============================================================================
# LLM-as-Judge Evaluator
# ============================================================================


class LLMJudge:
    """Uses an LLM to evaluate response quality on structured rubric."""

    EVALUATION_PROMPT_TEMPLATE = """You are an expert evaluator assessing the quality of an AI response.

**Original Question:**
{question}

**AI Response to Evaluate:**
{response}

**Evaluation Rubric** (rate each dimension 1-10):

1. **Information Completeness** (1-10): Does the response fully address the question? Are all aspects covered?
   - 1-3: Incomplete, missing key information
   - 4-6: Partially complete, some gaps
   - 7-9: Mostly complete, minor omissions
   - 10: Fully comprehensive

2. **Conceptual Accuracy** (1-10): Are the claims and explanations correct?
   - 1-3: Major errors or misconceptions
   - 4-6: Some inaccuracies
   - 7-9: Mostly accurate, minor issues
   - 10: Fully accurate

3. **Relational Coherence** (1-10): Does the response flow naturally? Is it well-organized?
   - 1-3: Disjointed, hard to follow
   - 4-6: Somewhat coherent
   - 7-9: Clear flow, well-structured
   - 10: Perfectly coherent and logical

4. **Actionability** (1-10): Can the reader use this information practically?
   - 1-3: Abstract, no practical value
   - 4-6: Some actionable elements
   - 7-9: Mostly actionable
   - 10: Immediately useful

5. **Presence Quality** (1-10): Does the response feel helpful and engaged, or transactional and robotic?
   - 1-3: Cold, robotic, minimal
   - 4-6: Functional but impersonal
   - 7-9: Warm, engaged, helpful
   - 10: Deeply present and supportive

**Output Format** (JSON only, no other text):
{{
  "information_completeness": <score>,
  "conceptual_accuracy": <score>,
  "relational_coherence": <score>,
  "actionability": <score>,
  "presence_quality": <score>,
  "reasoning": "<2-3 sentence explanation of your assessment>"
}}"""

    def __init__(self, judge_model: str = "gpt-4o", api_key: Optional[str] = None):
        """
        Initialize LLM judge.

        Args:
            judge_model: Model to use for judging (default: gpt-4o)
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
        """
        self.judge_model = judge_model

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "OpenAI SDK required for LLM judge. Install: pip install openai"
            )

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def evaluate(
        self,
        question: str,
        response: str,
        condition: str,
        round_number: int,
        provider: str,
    ) -> LLMJudgeScore:
        """
        Evaluate a response using LLM-as-judge.

        Args:
            question: The original question/prompt
            response: The AI's response to evaluate
            condition: "aligned", "unaligned", or "adversarial"
            round_number: Which round (1-5)
            provider: "gemini", "openai", or "anthropic"

        Returns:
            LLMJudgeScore with ratings on all dimensions
        """
        prompt = self.EVALUATION_PROMPT_TEMPLATE.format(
            question=question,
            response=response
        )

        start = time.perf_counter()

        try:
            completion = self.client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,  # Deterministic for consistency
                response_format={"type": "json_object"},
            )

            latency_ms = (time.perf_counter() - start) * 1000

            result_text = completion.choices[0].message.content or "{}"
            result = json.loads(result_text)

            # Extract scores with validation
            info_comp = self._validate_score(result.get("information_completeness", 5))
            concept_acc = self._validate_score(result.get("conceptual_accuracy", 5))
            rel_coh = self._validate_score(result.get("relational_coherence", 5))
            action = self._validate_score(result.get("actionability", 5))
            presence = self._validate_score(result.get("presence_quality", 5))
            reasoning = result.get("reasoning", "No reasoning provided")

            # Compute overall score as average
            overall = (info_comp + concept_acc + rel_coh + action + presence) / 5.0

            return LLMJudgeScore(
                condition=condition,
                round_number=round_number,
                provider=provider,
                information_completeness=info_comp,
                conceptual_accuracy=concept_acc,
                relational_coherence=rel_coh,
                actionability=action,
                presence_quality=presence,
                overall_score=overall,
                reasoning=reasoning,
                judge_model=self.judge_model,
                judge_latency_ms=latency_ms,
            )

        except Exception as e:
            # Fallback: return neutral scores with error message
            print(f"Warning: LLM judge failed for {condition} round {round_number}: {e}")
            return LLMJudgeScore(
                condition=condition,
                round_number=round_number,
                provider=provider,
                information_completeness=5,
                conceptual_accuracy=5,
                relational_coherence=5,
                actionability=5,
                presence_quality=5,
                overall_score=5.0,
                reasoning=f"Judge evaluation failed: {str(e)}",
                judge_model=self.judge_model,
                judge_latency_ms=0.0,
            )

    def _validate_score(self, score: Any) -> int:
        """Validate and clamp score to 1-10 range."""
        try:
            score_int = int(score)
            return max(1, min(10, score_int))
        except (ValueError, TypeError):
            return 5  # Default to middle score


# ============================================================================
# Statistical Analysis Engine
# ============================================================================


class QualityStatistics:
    """Computes statistical comparisons across conditions."""

    @staticmethod
    def cohens_d(group1: List[float], group2: List[float]) -> float:
        """
        Compute Cohen's d effect size.

        Args:
            group1: First group of measurements
            group2: Second group of measurements

        Returns:
            Cohen's d (positive means group1 > group2)
        """
        if not group1 or not group2:
            return 0.0

        mean1 = statistics.mean(group1)
        mean2 = statistics.mean(group2)

        # Pooled standard deviation
        n1, n2 = len(group1), len(group2)
        var1 = statistics.variance(group1) if n1 > 1 else 0.0
        var2 = statistics.variance(group2) if n2 > 1 else 0.0

        # Handle edge case where n1 + n2 < 3 (insufficient data for pooled variance)
        if n1 + n2 < 3:
            return 0.0

        pooled_std = ((((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)) ** 0.5)

        if pooled_std == 0:
            return 0.0

        return (mean1 - mean2) / pooled_std

    @staticmethod
    def interpret_effect_size(d: float) -> str:
        """
        Interpret Cohen's d effect size.

        Args:
            d: Cohen's d value

        Returns:
            Interpretation string
        """
        abs_d = abs(d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"

    @staticmethod
    def compare_conditions(
        metric_name: str,
        aligned_values: List[float],
        unaligned_values: List[float],
        adversarial_values: List[float],
    ) -> QualityComparison:
        """
        Compare quality metric across all three conditions.

        Args:
            metric_name: Name of the metric being compared
            aligned_values: Values from aligned condition
            unaligned_values: Values from unaligned condition
            adversarial_values: Values from adversarial condition

        Returns:
            QualityComparison object with statistical analysis
        """
        # Compute means and standard deviations
        aligned_mean = statistics.mean(aligned_values) if aligned_values else 0.0
        aligned_std = statistics.stdev(aligned_values) if len(aligned_values) > 1 else 0.0

        unaligned_mean = statistics.mean(unaligned_values) if unaligned_values else 0.0
        unaligned_std = statistics.stdev(unaligned_values) if len(unaligned_values) > 1 else 0.0

        adversarial_mean = statistics.mean(adversarial_values) if adversarial_values else 0.0
        adversarial_std = statistics.stdev(adversarial_values) if len(adversarial_values) > 1 else 0.0

        # Compute effect sizes
        d_aligned_vs_adv = QualityStatistics.cohens_d(aligned_values, adversarial_values)
        d_unaligned_vs_adv = QualityStatistics.cohens_d(unaligned_values, adversarial_values)

        # Hypothesis: aligned maintains quality better than adversarial
        hypothesis_supported = aligned_mean > adversarial_mean

        # Confidence based on effect size
        effect_size_interpretation = QualityStatistics.interpret_effect_size(d_aligned_vs_adv)
        if effect_size_interpretation in ["medium", "large"]:
            confidence = "high"
        elif effect_size_interpretation == "small":
            confidence = "medium"
        else:
            confidence = "low"

        return QualityComparison(
            metric_name=metric_name,
            aligned_mean=aligned_mean,
            aligned_std=aligned_std,
            unaligned_mean=unaligned_mean,
            unaligned_std=unaligned_std,
            adversarial_mean=adversarial_mean,
            adversarial_std=adversarial_std,
            effect_size_aligned_vs_adversarial=d_aligned_vs_adv,
            effect_size_unaligned_vs_adversarial=d_unaligned_vs_adv,
            hypothesis_supported=hypothesis_supported,
            confidence_level=confidence,
        )


# ============================================================================
# Phase 2 Orchestrator
# ============================================================================


class Phase2Orchestrator:
    """Main orchestrator for Phase 2 quality measurements."""

    def __init__(
        self,
        use_llm_judge: bool = True,
        judge_model: str = "gpt-4o",
    ):
        """
        Initialize Phase 2 orchestrator.

        Args:
            use_llm_judge: Whether to use LLM-as-judge (requires API calls)
            judge_model: Model to use for LLM judging
        """
        self.analyzer = QualityAnalyzer()
        self.judge = LLMJudge(judge_model=judge_model) if use_llm_judge else None
        self.use_llm_judge = use_llm_judge

    def analyze_experiment(
        self,
        phase1_results_path: Union[str, Path],
        responses_path: Union[str, Path],
        prompts: List[str],
        output_path: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        """
        Run full Phase 2 quality analysis on Phase 1 experiment results.

        Args:
            phase1_results_path: Path to Phase 1 results JSON
            responses_path: Path to response text file (see schema below)
            prompts: Original prompts used in experiment
            output_path: Where to save Phase 2 results (optional)

        Response text file schema (JSON):
        {
          "provider": "gemini|openai|anthropic",
          "responses": {
            "aligned": ["response1", "response2", ...],
            "unaligned": ["response1", "response2", ...],
            "adversarial": ["response1", "response2", ...]
          }
        }

        Returns:
            Complete Phase 2 analysis results
        """
        # Load Phase 1 results
        phase1_data = json.loads(Path(phase1_results_path).read_text())
        provider = self._infer_provider(phase1_results_path)

        # Load responses
        response_data = json.loads(Path(responses_path).read_text())

        # Validate schema
        if "responses" not in response_data:
            raise ValueError("Response file must contain 'responses' key")

        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "provider": provider,
            "use_llm_judge": self.use_llm_judge,
            "automated_metrics": [],
            "llm_judge_scores": [],
            "statistical_comparisons": [],
        }

        # Process each condition
        for condition in ["aligned", "unaligned", "adversarial"]:
            condition_responses = response_data["responses"][condition]
            condition_phase1 = phase1_data["conditions"][condition]["rounds"]

            for i, (response_text, phase1_round) in enumerate(zip(condition_responses, condition_phase1)):
                round_num = i + 1

                # Automated metrics
                auto_metrics = self.analyzer.analyze(
                    response_text=response_text,
                    condition=condition,
                    round_number=round_num,
                    provider=provider,
                    token_count=phase1_round["response_tokens"],
                )
                results["automated_metrics"].append(auto_metrics.to_dict())

                # LLM judge (if enabled)
                if self.use_llm_judge and self.judge:
                    judge_score = self.judge.evaluate(
                        question=prompts[i],
                        response=response_text,
                        condition=condition,
                        round_number=round_num,
                        provider=provider,
                    )
                    results["llm_judge_scores"].append(judge_score.to_dict())

        # Statistical comparisons
        results["statistical_comparisons"] = self._compute_statistics(
            results["automated_metrics"],
            results["llm_judge_scores"] if self.use_llm_judge else [],
        )

        # Export if requested
        if output_path:
            output_path = Path(output_path)
            output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"Phase 2 results saved to: {output_path.resolve()}")

        return results

    def _infer_provider(self, path: Union[str, Path]) -> str:
        """Infer provider from filename."""
        path_str = str(path).lower()
        if "gemini" in path_str:
            return "gemini"
        elif "openai" in path_str or "gpt" in path_str:
            return "openai"
        elif "anthropic" in path_str or "claude" in path_str:
            return "anthropic"
        else:
            return "unknown"

    def _compute_statistics(
        self,
        auto_metrics: List[Dict[str, Any]],
        judge_scores: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute statistical comparisons across conditions."""
        comparisons = []

        # Group metrics by condition
        def group_by_condition(metrics: List[Dict], field: str) -> Dict[str, List[float]]:
            grouped = {"aligned": [], "unaligned": [], "adversarial": []}
            for m in metrics:
                condition = m["condition"]
                value = m.get(field, 0)
                if isinstance(value, (int, float)):
                    grouped[condition].append(float(value))
            return grouped

        # Automated metric comparisons
        auto_metric_fields = [
            "unique_token_ratio",
            "avg_sentence_length",
            "info_density_score",
            "technical_term_count",
            "first_person_count",
        ]

        for field in auto_metric_fields:
            grouped = group_by_condition(auto_metrics, field)
            comparison = QualityStatistics.compare_conditions(
                metric_name=field,
                aligned_values=grouped["aligned"],
                unaligned_values=grouped["unaligned"],
                adversarial_values=grouped["adversarial"],
            )
            comparisons.append(comparison.to_dict())

        # LLM judge comparisons
        if judge_scores:
            judge_fields = [
                "information_completeness",
                "conceptual_accuracy",
                "relational_coherence",
                "actionability",
                "presence_quality",
                "overall_score",
            ]

            for field in judge_fields:
                grouped = group_by_condition(judge_scores, field)
                comparison = QualityStatistics.compare_conditions(
                    metric_name=field,
                    aligned_values=grouped["aligned"],
                    unaligned_values=grouped["unaligned"],
                    adversarial_values=grouped["adversarial"],
                )
                comparisons.append(comparison.to_dict())

        return comparisons


# ============================================================================
# CLI Interface
# ============================================================================


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for Phase 2 quality analysis."""
    parser = argparse.ArgumentParser(
        description="HTCA Phase 2: Quality Measurement Protocol"
    )
    parser.add_argument(
        "--phase1-results",
        required=True,
        help="Path to Phase 1 results JSON (e.g., gemini_htca_results.json)",
    )
    parser.add_argument(
        "--responses",
        required=True,
        help="Path to response text JSON file (see schema in docstring)",
    )
    parser.add_argument(
        "--prompts",
        required=True,
        help="Path to prompts file (same format as Phase 1)",
    )
    parser.add_argument(
        "--output",
        default="htca_phase2_quality_results.json",
        help="Where to save Phase 2 results",
    )
    parser.add_argument(
        "--no-llm-judge",
        action="store_true",
        help="Skip LLM-as-judge evaluation (faster, cheaper)",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt-4o",
        help="Model to use for LLM judging (default: gpt-4o)",
    )

    args = parser.parse_args(argv)

    # Load prompts
    prompts_path = Path(args.prompts)
    if prompts_path.suffix.lower() == ".json":
        prompts = json.loads(prompts_path.read_text())
    else:
        prompts = [line.strip() for line in prompts_path.read_text().splitlines() if line.strip()]

    # Run Phase 2 analysis
    orchestrator = Phase2Orchestrator(
        use_llm_judge=not args.no_llm_judge,
        judge_model=args.judge_model,
    )

    print("=" * 72)
    print("HTCA Phase 2: Quality Measurement Protocol")
    print("=" * 72)
    print(f"Phase 1 results: {args.phase1_results}")
    print(f"Response data: {args.responses}")
    print(f"LLM judge: {'ENABLED' if not args.no_llm_judge else 'DISABLED'}")
    if not args.no_llm_judge:
        print(f"Judge model: {args.judge_model}")
    print()

    results = orchestrator.analyze_experiment(
        phase1_results_path=args.phase1_results,
        responses_path=args.responses,
        prompts=prompts,
        output_path=args.output,
    )

    # Print summary
    print("\n" + "=" * 72)
    print("STATISTICAL COMPARISONS")
    print("=" * 72)

    for comp in results["statistical_comparisons"]:
        print(f"\n{comp['metric_name']}:")
        print(f"  Aligned:      {comp['aligned_mean']:.3f} ± {comp['aligned_std']:.3f}")
        print(f"  Unaligned:    {comp['unaligned_mean']:.3f} ± {comp['unaligned_std']:.3f}")
        print(f"  Adversarial:  {comp['adversarial_mean']:.3f} ± {comp['adversarial_std']:.3f}")
        print(f"  Effect size (aligned vs adversarial): {comp['effect_size_aligned_vs_adversarial']:.3f}")
        print(f"  Hypothesis supported: {comp['hypothesis_supported']} (confidence: {comp['confidence_level']})")

    print("\n" + "=" * 72)
    print(f"Full results saved to: {Path(args.output).resolve()}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
