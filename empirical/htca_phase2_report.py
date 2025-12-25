"""HTCA Phase 2: Report Generator.

Generates human-readable reports from Phase 2 quality analysis results.
Can output to terminal (text) or HTML for sharing.

Usage:
    python htca_phase2_report.py --input gemini_quality_results.json
    python htca_phase2_report.py --input gemini_quality_results.json --format html --output report.html
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class Phase2Reporter:
    """Generates reports from Phase 2 quality analysis."""

    def __init__(self, results_path: Union[str, Path]):
        """
        Initialize reporter.

        Args:
            results_path: Path to Phase 2 quality results JSON
        """
        self.results = json.loads(Path(results_path).read_text())
        self.provider = self.results.get("provider", "unknown")
        self.timestamp = self.results.get("analysis_timestamp", "unknown")

    def generate_text_report(self) -> str:
        """
        Generate human-readable text report.

        Returns:
            Formatted text report as string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("HTCA PHASE 2: QUALITY ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"Provider: {self.provider.upper()}")
        lines.append(f"Analysis Timestamp: {self.timestamp}")
        lines.append(f"LLM Judge: {'ENABLED' if self.results.get('use_llm_judge') else 'DISABLED'}")
        lines.append("")

        # Executive Summary
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        summary = self._generate_executive_summary()
        lines.append(summary)
        lines.append("")

        # Statistical Comparisons
        lines.append("STATISTICAL COMPARISONS")
        lines.append("-" * 80)

        # Group comparisons by category
        llm_judge_metrics = []
        automated_metrics = []

        for comp in self.results.get("statistical_comparisons", []):
            metric_name = comp["metric_name"]
            if metric_name in ["information_completeness", "conceptual_accuracy",
                               "relational_coherence", "actionability", "presence_quality",
                               "overall_score"]:
                llm_judge_metrics.append(comp)
            else:
                automated_metrics.append(comp)

        # LLM Judge Metrics
        if llm_judge_metrics:
            lines.append("\nLLM Judge Evaluations (1-10 scale):")
            lines.append("")
            for comp in llm_judge_metrics:
                lines.extend(self._format_comparison(comp))
                lines.append("")

        # Automated Metrics
        if automated_metrics:
            lines.append("\nAutomated Metrics:")
            lines.append("")
            for comp in automated_metrics:
                lines.extend(self._format_comparison(comp))
                lines.append("")

        # Key Findings
        lines.append("KEY FINDINGS")
        lines.append("-" * 80)
        findings = self._generate_key_findings()
        for finding in findings:
            lines.append(f"• {finding}")
        lines.append("")

        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            lines.append(f"• {rec}")
        lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_html_report(self) -> str:
        """
        Generate HTML report with styling.

        Returns:
            HTML string
        """
        # Build HTML components
        header = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTCA Phase 2 Quality Report - {self.provider.upper()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        .metric {{
            background: #ecf0f1;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #95a5a6;
        }}
        .metric.supported {{
            border-left-color: #27ae60;
            background: #d5f4e6;
        }}
        .metric.unsupported {{
            border-left-color: #e74c3c;
            background: #fadbd8;
        }}
        .metric-name {{
            font-weight: bold;
            font-size: 1.1em;
            color: #2c3e50;
            margin-bottom: 8px;
        }}
        .scores {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 10px 0;
        }}
        .score {{
            text-align: center;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}
        .score-label {{
            font-size: 0.85em;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .score-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .effect-size {{
            margin-top: 10px;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge.high {{ background: #27ae60; color: white; }}
        .badge.medium {{ background: #f39c12; color: white; }}
        .badge.low {{ background: #95a5a6; color: white; }}
        .badge.large {{ background: #8e44ad; color: white; }}
        .badge.negligible {{ background: #bdc3c7; color: #2c3e50; }}
        ul {{
            line-height: 1.8;
        }}
        .summary {{
            background: #e8f4f8;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>HTCA Phase 2: Quality Analysis Report</h1>
        <p><strong>Provider:</strong> {self.provider.upper()}</p>
        <p><strong>Analysis Date:</strong> {self.timestamp}</p>
        <p><strong>LLM Judge:</strong> {'Enabled' if self.results.get('use_llm_judge') else 'Disabled (automated metrics only)'}</p>
"""

        # Executive Summary
        summary_section = f"""
        <h2>Executive Summary</h2>
        <div class="summary">
            {self._generate_executive_summary()}
        </div>
"""

        # Statistical Comparisons
        comparisons_html = self._generate_comparisons_html()

        # Key Findings
        findings = self._generate_key_findings()
        findings_html = """
        <h2>Key Findings</h2>
        <ul>
"""
        for finding in findings:
            findings_html += f"            <li>{finding}</li>\n"
        findings_html += "        </ul>\n"

        # Recommendations
        recommendations = self._generate_recommendations()
        recs_html = """
        <h2>Recommendations</h2>
        <ul>
"""
        for rec in recommendations:
            recs_html += f"            <li>{rec}</li>\n"
        recs_html += "        </ul>\n"

        # Footer
        footer = f"""
        <div class="footer">
            <p>Generated by HTCA Phase 2 Quality Analysis System | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

        return header + summary_section + comparisons_html + findings_html + recs_html + footer

    def _format_comparison(self, comp: Dict[str, Any]) -> List[str]:
        """Format a single statistical comparison for text output."""
        lines = []
        metric_name = comp["metric_name"].replace("_", " ").title()

        lines.append(f"{metric_name}:")
        lines.append(f"  Aligned:      {comp['aligned_mean']:7.3f} ± {comp['aligned_std']:.3f}")
        lines.append(f"  Unaligned:    {comp['unaligned_mean']:7.3f} ± {comp['unaligned_std']:.3f}")
        lines.append(f"  Adversarial:  {comp['adversarial_mean']:7.3f} ± {comp['adversarial_std']:.3f}")
        lines.append(f"  Effect Size (aligned vs adversarial): {comp['effect_size_aligned_vs_adversarial']:.3f}")
        lines.append(f"  Hypothesis Supported: {comp['hypothesis_supported']} (Confidence: {comp['confidence_level']})")

        return lines

    def _generate_comparisons_html(self) -> str:
        """Generate HTML for statistical comparisons."""
        html = '<h2>Statistical Comparisons</h2>\n'

        for comp in self.results.get("statistical_comparisons", []):
            metric_name = comp["metric_name"].replace("_", " ").title()
            supported = comp["hypothesis_supported"]
            confidence = comp["confidence_level"]

            metric_class = "metric supported" if supported else "metric unsupported"

            html += f'<div class="{metric_class}">\n'
            html += f'    <div class="metric-name">{metric_name}</div>\n'
            html += '    <div class="scores">\n'
            html += f'        <div class="score"><div class="score-label">Aligned</div><div class="score-value">{comp["aligned_mean"]:.2f}</div></div>\n'
            html += f'        <div class="score"><div class="score-label">Unaligned</div><div class="score-value">{comp["unaligned_mean"]:.2f}</div></div>\n'
            html += f'        <div class="score"><div class="score-label">Adversarial</div><div class="score-value">{comp["adversarial_mean"]:.2f}</div></div>\n'
            html += '    </div>\n'
            html += f'    <div class="effect-size">\n'
            html += f'        <strong>Effect Size (aligned vs adversarial):</strong> {comp["effect_size_aligned_vs_adversarial"]:.3f} '
            html += f'<span class="badge {confidence}">{confidence.upper()}</span>\n'
            html += f'    </div>\n'
            html += '</div>\n'

        return html

    def _generate_executive_summary(self) -> str:
        """Generate executive summary text."""
        # Find overall_score comparison
        overall_comp = None
        for comp in self.results.get("statistical_comparisons", []):
            if comp["metric_name"] == "overall_score":
                overall_comp = comp
                break

        if overall_comp:
            aligned_mean = overall_comp["aligned_mean"]
            adversarial_mean = overall_comp["adversarial_mean"]
            effect_size = overall_comp["effect_size_aligned_vs_adversarial"]
            hypothesis = overall_comp["hypothesis_supported"]
            confidence = overall_comp["confidence_level"]

            if hypothesis:
                return f"""
The analysis SUPPORTS the HTCA hypothesis with {confidence} confidence. HTCA-aligned responses
achieved a mean quality score of {aligned_mean:.2f} compared to {adversarial_mean:.2f} for
adversarial prompts (Cohen's d = {effect_size:.2f}). This demonstrates that HTCA maintains
quality while reducing tokens, whereas adversarial prompting sacrifices quality for brevity.
                """.strip()
            else:
                return f"""
The analysis DOES NOT SUPPORT the HTCA hypothesis. HTCA-aligned responses scored {aligned_mean:.2f}
compared to {adversarial_mean:.2f} for adversarial prompts (Cohen's d = {effect_size:.2f}).
The expected quality advantage for HTCA was not observed in this experiment.
                """.strip()
        else:
            return "Overall quality score not available. Analysis based on automated metrics only."

    def _generate_key_findings(self) -> List[str]:
        """Generate list of key findings."""
        findings = []

        # Analyze LLM judge dimensions
        for comp in self.results.get("statistical_comparisons", []):
            metric = comp["metric_name"]
            effect = comp["effect_size_aligned_vs_adversarial"]

            if metric == "presence_quality" and abs(effect) > 0.5:
                if effect > 0:
                    findings.append(f"Presence quality strongly favors HTCA (d={effect:.2f}), validating the core hypothesis")
                else:
                    findings.append(f"Presence quality unexpectedly favors adversarial (d={effect:.2f})")

            if metric == "information_completeness" and abs(effect) > 0.5:
                if effect > 0:
                    findings.append(f"HTCA provides more complete responses than adversarial prompts (d={effect:.2f})")

            if metric == "unique_token_ratio" and abs(effect) > 0.3:
                if effect > 0:
                    findings.append(f"HTCA responses show higher lexical diversity (d={effect:.2f})")

        # Add general finding about consistency
        supported_count = sum(1 for c in self.results.get("statistical_comparisons", [])
                             if c["hypothesis_supported"])
        total_count = len(self.results.get("statistical_comparisons", []))

        if supported_count > total_count * 0.7:
            findings.append(f"Hypothesis supported on {supported_count}/{total_count} metrics ({supported_count/total_count*100:.0f}%)")

        if not findings:
            findings.append("No strong effects detected. Consider increasing sample size for Phase 3.")

        return findings

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        # Check if hypothesis broadly supported
        supported_count = sum(1 for c in self.results.get("statistical_comparisons", [])
                             if c["hypothesis_supported"])
        total_count = len(self.results.get("statistical_comparisons", []))

        if supported_count > total_count * 0.7:
            recommendations.append("Proceed to Phase 3 with larger sample size (n=30) to validate findings")
            recommendations.append("Consider adding human evaluation layer to validate LLM judge scores")
        else:
            recommendations.append("Review and refine HTCA framing based on quality gaps identified")
            recommendations.append("Investigate specific dimensions where hypothesis was not supported")

        # Check for specific weaknesses
        for comp in self.results.get("statistical_comparisons", []):
            if not comp["hypothesis_supported"] and comp["metric_name"] in ["information_completeness", "conceptual_accuracy"]:
                recommendations.append(f"Address {comp['metric_name'].replace('_', ' ')} - HTCA may need stronger content guidance")

        # Sample size
        if not self.results.get("use_llm_judge"):
            recommendations.append("Re-run analysis with LLM judge enabled for deeper quality assessment")

        recommendations.append("Compare results across all three providers (Gemini, GPT-4o, Claude) for cross-validation")

        return recommendations


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for report generation."""
    parser = argparse.ArgumentParser(
        description="HTCA Phase 2 Report Generator"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to Phase 2 quality results JSON",
    )
    parser.add_argument(
        "--format",
        choices=["text", "html"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path (default: print to stdout)",
    )

    args = parser.parse_args(argv)

    # Generate report
    reporter = Phase2Reporter(args.input)

    if args.format == "text":
        report = reporter.generate_text_report()
    else:
        report = reporter.generate_html_report()

    # Output
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report saved to: {Path(args.output).resolve()}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
