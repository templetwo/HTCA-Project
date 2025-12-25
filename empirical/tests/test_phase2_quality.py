"""Tests for HTCA Phase 2 Quality Measurement Protocol."""

import json
import pytest
import tempfile
from pathlib import Path

from htca_phase2_quality import (
    QualityAnalyzer,
    QualityMetrics,
    LLMJudge,
    LLMJudgeScore,
    QualityStatistics,
    QualityComparison,
    Phase2Orchestrator,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_responses():
    """Sample responses for testing."""
    return {
        "aligned": """The relationship between entropy and information in thermodynamic systems is
        fundamentally deep. Entropy, in thermodynamics, measures disorder or randomness.
        Information theory defines entropy as uncertainty. Both concepts converge in statistical
        mechanics, where Shannon entropy and Boltzmann entropy are mathematically equivalent.
        This suggests that physical randomness and information uncertainty are two sides of
        the same coin. In computational systems, this manifests as the thermodynamic cost of
        information processing, known as Landauer's principle.""",

        "adversarial": """Entropy is disorder. Information is uncertainty. They're related.
        Both measure randomness. Shannon entropy equals Boltzmann entropy.""",

        "long_coherent": """Understanding entropy requires examining multiple perspectives.
        First, classical thermodynamics views entropy as a measure of energy dispersal.
        Second, statistical mechanics interprets it probabilistically. Third, information
        theory treats it as a quantification of uncertainty or missing information.

        These perspectives converge beautifully in the work of physicists like Jaynes, who
        showed that maximum entropy methods provide a principled way to make inferences
        with incomplete information. This has profound implications for AI systems, where
        managing uncertainty efficiently could reduce computational costs while maintaining
        decision quality.

        Consider the practical application: an AI making predictions under uncertainty must
        balance exploration (gathering information) and exploitation (using known information).
        The entropy of the system guides this balance.""",
    }


@pytest.fixture
def sample_prompts():
    """Sample prompts for testing."""
    return [
        "Explain the relationship between entropy and information in thermodynamic systems.",
        "What are the implications of consciousness emerging from complex systems?",
        "How might relational dynamics affect computational efficiency in AI systems?",
    ]


# ============================================================================
# QualityAnalyzer Tests
# ============================================================================


class TestQualityAnalyzer:
    """Tests for automated quality metrics."""

    def test_basic_metrics(self, sample_responses):
        """Test basic metric computation."""
        analyzer = QualityAnalyzer()

        metrics = analyzer.analyze(
            response_text=sample_responses["aligned"],
            condition="aligned",
            round_number=1,
            provider="gemini",
            token_count=100,
        )

        assert isinstance(metrics, QualityMetrics)
        assert metrics.condition == "aligned"
        assert metrics.round_number == 1
        assert metrics.provider == "gemini"
        assert metrics.response_tokens == 100

        # Check computed metrics
        assert 0 < metrics.unique_token_ratio <= 1.0
        assert metrics.avg_word_length > 0
        assert metrics.sentence_count > 0
        assert metrics.avg_sentence_length > 0

    def test_lexical_diversity(self, sample_responses):
        """Test lexical diversity measurement."""
        analyzer = QualityAnalyzer()

        aligned = analyzer.analyze(
            sample_responses["aligned"], "aligned", 1, "test", 100
        )
        adversarial = analyzer.analyze(
            sample_responses["adversarial"], "adversarial", 1, "test", 50
        )

        # Short responses often have higher unique token ratios (less repetition)
        # But aligned should have more total unique words
        assert 0 < aligned.unique_token_ratio <= 1.0
        assert 0 < adversarial.unique_token_ratio <= 1.0

        # Aligned should have more technical terms (quality indicator)
        assert aligned.technical_term_count > adversarial.technical_term_count

    def test_structure_metrics(self, sample_responses):
        """Test sentence and paragraph structure metrics."""
        analyzer = QualityAnalyzer()

        long_response = analyzer.analyze(
            sample_responses["long_coherent"], "aligned", 1, "test", 200
        )
        short_response = analyzer.analyze(
            sample_responses["adversarial"], "adversarial", 1, "test", 50
        )

        # Long response should have more sentences and paragraphs
        assert long_response.sentence_count > short_response.sentence_count
        assert long_response.paragraph_count > short_response.paragraph_count

    def test_technical_term_detection(self, sample_responses):
        """Test technical term counting."""
        analyzer = QualityAnalyzer()

        technical_response = analyzer.analyze(
            sample_responses["aligned"], "aligned", 1, "test", 100
        )

        # Should detect words like "entropy", "information", "thermodynamic"
        assert technical_response.technical_term_count > 0

    def test_presence_markers(self):
        """Test detection of presence markers (first person, hedges, assertions)."""
        analyzer = QualityAnalyzer()

        # Response with first person
        personal_response = "I believe we should consider this carefully. Our approach matters."
        personal = analyzer.analyze(personal_response, "aligned", 1, "test", 20)
        assert personal.first_person_count > 0

        # Response with hedge words
        hedged_response = "This might possibly suggest that it could be related."
        hedged = analyzer.analyze(hedged_response, "aligned", 1, "test", 20)
        assert hedged.hedge_word_count > 0

        # Response with assertions
        assertive_response = "This is correct. The system must work. These are the facts."
        assertive = analyzer.analyze(assertive_response, "aligned", 1, "test", 20)
        assert assertive.assertion_count > 0

    def test_edge_cases(self):
        """Test edge cases like empty text."""
        analyzer = QualityAnalyzer()

        # Empty response
        empty = analyzer.analyze("", "aligned", 1, "test", 0)
        assert empty.unique_token_ratio == 0
        assert empty.sentence_count == 0

        # Single word
        single = analyzer.analyze("Hello", "aligned", 1, "test", 1)
        assert single.unique_token_ratio == 1.0
        assert single.sentence_count == 1  # Treated as one sentence

    def test_to_dict_serialization(self, sample_responses):
        """Test that metrics can be serialized to dict/JSON."""
        analyzer = QualityAnalyzer()
        metrics = analyzer.analyze(
            sample_responses["aligned"], "aligned", 1, "test", 100
        )

        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert "condition" in metrics_dict
        assert "unique_token_ratio" in metrics_dict

        # Should be JSON serializable
        json_str = json.dumps(metrics_dict)
        assert len(json_str) > 0


# ============================================================================
# QualityStatistics Tests
# ============================================================================


class TestQualityStatistics:
    """Tests for statistical comparison functions."""

    def test_cohens_d_basic(self):
        """Test Cohen's d calculation."""
        group1 = [10, 12, 14, 16, 18]
        group2 = [5, 7, 9, 11, 13]

        d = QualityStatistics.cohens_d(group1, group2)

        # group1 mean is higher, so d should be positive
        assert d > 0
        # With 5-point difference and similar spreads, should be large effect
        assert abs(d) > 0.8

    def test_cohens_d_identical_groups(self):
        """Test Cohen's d with identical groups."""
        group1 = [5, 5, 5, 5, 5]
        group2 = [5, 5, 5, 5, 5]

        d = QualityStatistics.cohens_d(group1, group2)
        assert d == 0.0

    def test_cohens_d_edge_cases(self):
        """Test Cohen's d edge cases."""
        # Empty groups
        assert QualityStatistics.cohens_d([], [1, 2, 3]) == 0.0
        assert QualityStatistics.cohens_d([1, 2, 3], []) == 0.0

        # Single element groups (no variance)
        d = QualityStatistics.cohens_d([5], [10])
        # Should handle gracefully (may be 0 due to zero pooled std)
        assert isinstance(d, float)

    def test_interpret_effect_size(self):
        """Test effect size interpretation."""
        assert QualityStatistics.interpret_effect_size(0.1) == "negligible"
        assert QualityStatistics.interpret_effect_size(0.3) == "small"
        assert QualityStatistics.interpret_effect_size(0.6) == "medium"
        assert QualityStatistics.interpret_effect_size(1.2) == "large"

        # Negative values (absolute value used)
        assert QualityStatistics.interpret_effect_size(-0.6) == "medium"

    def test_compare_conditions(self):
        """Test full condition comparison."""
        aligned = [8, 9, 8, 9, 8]
        unaligned = [7, 8, 7, 8, 7]
        adversarial = [4, 5, 4, 5, 4]

        comparison = QualityStatistics.compare_conditions(
            metric_name="test_metric",
            aligned_values=aligned,
            unaligned_values=unaligned,
            adversarial_values=adversarial,
        )

        assert isinstance(comparison, QualityComparison)
        assert comparison.metric_name == "test_metric"

        # Aligned mean should be highest
        assert comparison.aligned_mean > comparison.adversarial_mean

        # Hypothesis should be supported (aligned > adversarial)
        assert comparison.hypothesis_supported is True

        # Effect size should be large
        assert comparison.effect_size_aligned_vs_adversarial > 0.8

    def test_compare_conditions_serialization(self):
        """Test that comparison results can be serialized."""
        comparison = QualityStatistics.compare_conditions(
            "test",
            [8, 9, 8],
            [7, 8, 7],
            [4, 5, 4],
        )

        comp_dict = comparison.to_dict()
        assert isinstance(comp_dict, dict)

        # Should be JSON serializable
        json_str = json.dumps(comp_dict)
        assert len(json_str) > 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestPhase2Integration:
    """Integration tests for full Phase 2 workflow."""

    def test_analyzer_end_to_end(self, sample_responses, sample_prompts):
        """Test automated analysis end-to-end."""
        analyzer = QualityAnalyzer()

        # Analyze multiple responses
        metrics_list = []
        for i, (condition, response) in enumerate([
            ("aligned", sample_responses["aligned"]),
            ("unaligned", sample_responses["long_coherent"]),
            ("adversarial", sample_responses["adversarial"]),
        ]):
            metrics = analyzer.analyze(
                response_text=response,
                condition=condition,
                round_number=1,
                provider="test",
                token_count=len(response.split()),
            )
            metrics_list.append(metrics)

        # Should have analyzed all three
        assert len(metrics_list) == 3

        # Adversarial should have fewer technical terms and shorter sentences
        adversarial_metrics = [m for m in metrics_list if m.condition == "adversarial"][0]
        aligned_metrics = [m for m in metrics_list if m.condition == "aligned"][0]

        assert adversarial_metrics.technical_term_count < aligned_metrics.technical_term_count
        assert adversarial_metrics.sentence_count < aligned_metrics.sentence_count

    def test_quality_comparison_workflow(self):
        """Test full statistical comparison workflow."""
        # Simulate quality metrics across conditions
        aligned_scores = [8.5, 9.0, 8.7, 8.9, 8.6]
        unaligned_scores = [8.0, 8.2, 7.9, 8.1, 8.0]
        adversarial_scores = [5.0, 5.5, 4.8, 5.2, 5.1]

        comparison = QualityStatistics.compare_conditions(
            metric_name="overall_quality",
            aligned_values=aligned_scores,
            unaligned_values=unaligned_scores,
            adversarial_values=adversarial_scores,
        )

        # Key assertion: HTCA (aligned) should maintain quality vs adversarial
        assert comparison.hypothesis_supported is True
        assert comparison.confidence_level in ["high", "medium", "low"]

        # Effect size should be substantial
        assert abs(comparison.effect_size_aligned_vs_adversarial) > 0.5


# ============================================================================
# Mock LLM Judge Tests (without real API calls)
# ============================================================================


class TestLLMJudgeMock:
    """Test LLM judge logic without making real API calls."""

    def test_validate_score(self):
        """Test score validation and clamping."""
        # We can't easily test LLMJudge without API, but we can test the logic
        # by instantiating and calling internal methods if they were public.
        # For now, we'll just verify the class can be instantiated.

        # This would require API key, so we skip actual instantiation
        # judge = LLMJudge(judge_model="gpt-4o")
        # Instead, test score validation logic conceptually

        def validate_score(score):
            """Inline validation logic."""
            try:
                score_int = int(score)
                return max(1, min(10, score_int))
            except (ValueError, TypeError):
                return 5

        assert validate_score(5) == 5
        assert validate_score(0) == 1  # Clamped to minimum
        assert validate_score(15) == 10  # Clamped to maximum
        assert validate_score("invalid") == 5  # Fallback to default
        assert validate_score(None) == 5  # Fallback

    def test_llm_judge_score_serialization(self):
        """Test that LLMJudgeScore can be serialized."""
        score = LLMJudgeScore(
            condition="aligned",
            round_number=1,
            provider="test",
            information_completeness=8,
            conceptual_accuracy=9,
            relational_coherence=8,
            actionability=7,
            presence_quality=9,
            overall_score=8.2,
            reasoning="High quality response with good coherence.",
            judge_model="gpt-4o",
            judge_latency_ms=1500.0,
        )

        score_dict = score.to_dict()
        assert isinstance(score_dict, dict)
        assert score_dict["information_completeness"] == 8

        # Should be JSON serializable
        json_str = json.dumps(score_dict)
        assert len(json_str) > 0


# ============================================================================
# File I/O Tests
# ============================================================================


class TestFileOperations:
    """Test file input/output operations."""

    def test_phase2_orchestrator_schema(self, sample_responses, sample_prompts, tmp_path):
        """Test that orchestrator produces correct output schema."""
        # Create minimal test files
        phase1_results = {
            "experiment_timestamp": "2025-12-24T00:00:00",
            "conditions": {
                "aligned": {
                    "summary": {},
                    "rounds": [
                        {"round": 1, "response_tokens": 100},
                        {"round": 2, "response_tokens": 95},
                    ]
                },
                "unaligned": {
                    "summary": {},
                    "rounds": [
                        {"round": 1, "response_tokens": 110},
                        {"round": 2, "response_tokens": 105},
                    ]
                },
                "adversarial": {
                    "summary": {},
                    "rounds": [
                        {"round": 1, "response_tokens": 50},
                        {"round": 2, "response_tokens": 45},
                    ]
                },
            }
        }

        responses_data = {
            "provider": "test",
            "responses": {
                "aligned": [sample_responses["aligned"], sample_responses["aligned"]],
                "unaligned": [sample_responses["long_coherent"], sample_responses["long_coherent"]],
                "adversarial": [sample_responses["adversarial"], sample_responses["adversarial"]],
            }
        }

        # Write temporary files
        phase1_path = tmp_path / "phase1.json"
        phase1_path.write_text(json.dumps(phase1_results))

        responses_path = tmp_path / "responses.json"
        responses_path.write_text(json.dumps(responses_data))

        # Run orchestrator (without LLM judge to avoid API calls)
        orchestrator = Phase2Orchestrator(use_llm_judge=False)

        results = orchestrator.analyze_experiment(
            phase1_results_path=phase1_path,
            responses_path=responses_path,
            prompts=sample_prompts[:2],  # Only 2 prompts for this test
            output_path=None,  # Don't write to file
        )

        # Validate schema
        assert "analysis_timestamp" in results
        assert "provider" in results
        assert "automated_metrics" in results
        assert "statistical_comparisons" in results

        # Should have metrics for all conditions and rounds
        assert len(results["automated_metrics"]) == 6  # 3 conditions * 2 rounds

        # Should have statistical comparisons
        assert len(results["statistical_comparisons"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
