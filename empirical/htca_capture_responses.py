"""HTCA Response Capture Extension.

Extends the Phase 1 harness to capture and save actual response text
for Phase 2 quality analysis. This is a lightweight wrapper that reuses
the existing harness infrastructure.

Usage:
    python htca_capture_responses.py --provider gemini --model gemini-2.0-flash-exp \\
        --prompts prompts.txt --output gemini_responses.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

# Import from existing harness
from htca_harness import (
    HTCATone,
    HTCAExperiment,
    _resolve_client,
    _resolve_tone,
    _load_prompts,
    _load_env_file,
    tone_aligned_prompt,
    unaligned_prompt,
    adversarial_prompt,
)


class ResponseCapture:
    """Captures response text during experiment runs."""

    def __init__(self, provider: str):
        """
        Initialize response capture.

        Args:
            provider: Provider name ("gemini", "openai", "anthropic")
        """
        self.provider = provider
        self.responses: Dict[str, List[str]] = {
            "aligned": [],
            "unaligned": [],
            "adversarial": [],
        }

    def capture_condition(
        self,
        experiment: HTCAExperiment,
        prompts: List[str],
        condition: str,
        tone: Optional[HTCATone] = None,
    ) -> None:
        """
        Run experiment for one condition and capture responses.

        Args:
            experiment: HTCAExperiment instance
            prompts: List of base prompts
            condition: "aligned", "unaligned", or "adversarial"
            tone: HTCATone for aligned condition (optional)
        """
        experiment.reset()

        for prompt in prompts:
            # Build full prompt based on condition
            if condition == "aligned" and tone:
                full_prompt = tone_aligned_prompt(prompt, tone)
            elif condition == "unaligned":
                full_prompt = unaligned_prompt(prompt)
            elif condition == "adversarial":
                full_prompt = adversarial_prompt(prompt)
            else:
                raise ValueError(f"Unknown condition: {condition}")

            # Generate response
            gen = experiment.client.generate(full_prompt)

            # Capture response text
            self.responses[condition].append(gen.text)

            # Print progress
            print(f"  [{condition}] Round {len(self.responses[condition])}/{len(prompts)} completed")

    def export(self, output_path: Union[str, Path]) -> Path:
        """
        Export captured responses to JSON file.

        Args:
            output_path: Where to save the response file

        Returns:
            Path to saved file

        Output schema:
        {
          "capture_timestamp": "ISO datetime",
          "provider": "gemini|openai|anthropic",
          "responses": {
            "aligned": ["response1", "response2", ...],
            "unaligned": ["response1", "response2", ...],
            "adversarial": ["response1", "response2", ...]
          }
        }
        """
        output_path = Path(output_path)

        data = {
            "capture_timestamp": datetime.now().isoformat(),
            "provider": self.provider,
            "responses": self.responses,
        }

        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output_path


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for response capture."""
    parser = argparse.ArgumentParser(
        description="HTCA Response Capture - Extends Phase 1 to save response text"
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=["gemini", "openai", "anthropic"],
        help="Which backend to use",
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name for the chosen provider",
    )
    parser.add_argument(
        "--tone",
        default=HTCATone.SOFT_PRECISION.name,
        help="Aligned condition tone (enum name, e.g. SOFT_PRECISION)",
    )
    parser.add_argument(
        "--prompts",
        required=True,
        help="Prompts file: .txt (one per line) or .json (list[str])",
    )
    parser.add_argument(
        "--output",
        default="responses.json",
        help="Where to save captured responses",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env file to load API keys from",
    )

    args = parser.parse_args(argv)

    # Load environment
    _load_env_file(args.env_file)

    # Setup
    tone = _resolve_tone(args.tone)
    prompts = _load_prompts(args.prompts)
    client = _resolve_client(args.provider, args.model)

    print("=" * 72)
    print("HTCA Response Capture")
    print("=" * 72)
    print(f"Provider: {args.provider}")
    print(f"Model: {args.model}")
    print(f"Tone: {tone.name}")
    print(f"Prompts: {len(prompts)}")
    print()

    # Create experiment and capture
    experiment = HTCAExperiment(client)
    capture = ResponseCapture(provider=args.provider)

    # Run each condition
    for condition in ["aligned", "unaligned", "adversarial"]:
        print(f"\nRunning {condition.upper()} condition...")
        capture.capture_condition(
            experiment=experiment,
            prompts=prompts,
            condition=condition,
            tone=tone if condition == "aligned" else None,
        )

    # Export
    output_path = capture.export(args.output)

    print("\n" + "=" * 72)
    print(f"Responses captured and saved to: {output_path.resolve()}")
    print("=" * 72)

    # Print summary
    print("\nSummary:")
    for condition, responses in capture.responses.items():
        avg_length = sum(len(r) for r in responses) / len(responses) if responses else 0
        print(f"  {condition}: {len(responses)} responses, avg length: {avg_length:.0f} chars")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
