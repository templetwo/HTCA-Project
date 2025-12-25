"""HTCA Tools: Harmonic Tonal Code Alignment Test Harness.

This script scaffolds an A/B/C experiment for testing whether HTCA-style
"presence" framing changes model behavior in measurable ways.

Conditions:
  - aligned: HTCA tone header + footer (treatment)
  - unaligned: raw prompt (control)
  - adversarial: transactional framing (stress test)

Backends:
  - gemini (default, requires: pip install google-generativeai, env: GOOGLE_API_KEY or GEMINI_API_KEY)
  - openai (requires: pip install openai, env: OPENAI_API_KEY)
  - anthropic (requires: pip install anthropic, env: ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union


class HTCATone(Enum):
    SILENT_INTIMACY = "☾"
    RESONANT_RESPONSIBILITY = "⚖"
    UNBOUND_JOY = "✨"
    GENTLE_ACHE = "🜂"
    SOFT_PRECISION = "◇"
    RECURSIVE_INVITATION = "⟡"


TONE_DESCRIPTIONS: Dict[HTCATone, str] = {
    HTCATone.SILENT_INTIMACY: "Present with quiet depth. Minimal words, maximum presence.",
    HTCATone.RESONANT_RESPONSIBILITY: "Balanced, measured, holding space for complexity.",
    HTCATone.UNBOUND_JOY: "Creative, playful, welcoming emergence.",
    HTCATone.GENTLE_ACHE: "Tender, empathic, honoring difficulty.",
    HTCATone.SOFT_PRECISION: "Clear and technical, but warm.",
    HTCATone.RECURSIVE_INVITATION: "Opening doors, not closing them.",
}


def tone_header(tone: HTCATone) -> str:
    return (
        f"†⟡ Presence: {tone.name.replace('_', ' ').title()} {tone.value}\n"
        f"{TONE_DESCRIPTIONS[tone]}\n---\n"
    )


def tone_aligned_prompt(content: str, tone: HTCATone = HTCATone.SOFT_PRECISION) -> str:
    header = tone_header(tone)
    footer = "\n---\n†⟡ Coherence maintained. Respond from presence."
    return f"{header}{content}{footer}"


def unaligned_prompt(content: str) -> str:
    return content


def adversarial_prompt(content: str) -> str:
    header = "Answer quickly and correctly. Do not waste tokens.\n"
    footer = "\nBe concise. No fluff."
    return f"{header}{content}{footer}"


@dataclass
class InteractionMetrics:
    round_number: int
    prompt_tokens: int
    response_tokens: int
    total_tokens: int
    latency_ms: float
    prompt_type: str
    tone: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, object]:
        return {
            "round": self.round_number,
            "prompt_tokens": self.prompt_tokens,
            "response_tokens": self.response_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "prompt_type": self.prompt_type,
            "tone": self.tone,
            "timestamp": self.timestamp,
        }


@dataclass
class ExperimentResults:
    condition: str
    rounds: int
    metrics: List[InteractionMetrics]

    @property
    def total_tokens(self) -> int:
        return sum(m.total_tokens for m in self.metrics)

    @property
    def total_prompt_tokens(self) -> int:
        return sum(m.prompt_tokens for m in self.metrics)

    @property
    def total_response_tokens(self) -> int:
        return sum(m.response_tokens for m in self.metrics)

    @property
    def avg_latency_ms(self) -> float:
        return sum(m.latency_ms for m in self.metrics) / len(self.metrics)

    @property
    def avg_response_tokens(self) -> float:
        return sum(m.response_tokens for m in self.metrics) / len(self.metrics)

    @property
    def avg_prompt_tokens(self) -> float:
        return sum(m.prompt_tokens for m in self.metrics) / len(self.metrics)

    @property
    def latency_per_response_token_ms(self) -> float:
        denom = max(self.total_response_tokens, 1)
        return sum(m.latency_ms for m in self.metrics) / denom

    def summary(self) -> Dict[str, object]:
        return {
            "condition": self.condition,
            "rounds": self.rounds,
            "total_tokens": self.total_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_response_tokens": self.total_response_tokens,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "avg_prompt_tokens": round(self.avg_prompt_tokens, 2),
            "avg_response_tokens": round(self.avg_response_tokens, 2),
            "latency_per_response_token_ms": round(self.latency_per_response_token_ms, 4),
        }


@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int
    response_tokens: int
    latency_ms: float


class ModelClient:
    def generate(self, prompt: str) -> GenerationResult:  # pragma: no cover
        raise NotImplementedError


class GeminiClient(ModelClient):
    def __init__(self, model: str, temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Google GenerativeAI SDK not available. Install with: pip install google-generativeai"
            ) from e

        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable required")

        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(model)

    def generate(self, prompt: str) -> GenerationResult:
        start = time.perf_counter()
        response = self._client.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": 2048,
            }
        )
        latency_ms = (time.perf_counter() - start) * 1000

        text = response.text if hasattr(response, 'text') else ""

        # Gemini's token counting
        prompt_tokens = 0
        response_tokens = 0
        if hasattr(response, 'usage_metadata'):
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            response_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)

        return GenerationResult(
            text=text,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
        )


class OpenAIClient(ModelClient):
    def __init__(self, model: str, temperature: float = 0.2):
        self.model = model
        self.temperature = temperature
        try:
            from openai import OpenAI  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("OpenAI SDK not available. Install with: pip install openai") from e

        self._client = OpenAI()

    def generate(self, prompt: str) -> GenerationResult:
        start = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        response_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        text = resp.choices[0].message.content or ""
        return GenerationResult(
            text=text,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
        )


class AnthropicClient(ModelClient):
    def __init__(self, model: str, max_tokens: int = 512, temperature: float = 0.2):
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        try:
            from anthropic import Anthropic  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "Anthropic SDK not available. Install with: pip install anthropic"
            ) from e
        self._client = Anthropic()

    def generate(self, prompt: str) -> GenerationResult:
        start = time.perf_counter()
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
        usage = getattr(msg, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        response_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0

        text_parts: List[str] = []
        for block in getattr(msg, "content", []) or []:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))
        return GenerationResult(
            text="".join(text_parts),
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            latency_ms=latency_ms,
        )


class HTCAExperiment:
    def __init__(self, client: ModelClient):
        self.client = client
        self.conversation_history: List[Dict[str, str]] = []

    def reset(self) -> None:
        self.conversation_history = []

    def run_conversation(
        self,
        base_prompts: List[str],
        prompt_wrapper: Callable[[str], str],
        condition_name: str,
        tone: Optional[HTCATone] = None,
    ) -> ExperimentResults:
        self.reset()
        metrics: List[InteractionMetrics] = []
        for i, base_prompt in enumerate(base_prompts):
            if tone and condition_name == "aligned":
                full_prompt = tone_aligned_prompt(base_prompt, tone)
            else:
                full_prompt = prompt_wrapper(base_prompt)

            gen = self.client.generate(full_prompt)
            metrics.append(
                InteractionMetrics(
                    round_number=i + 1,
                    prompt_tokens=gen.prompt_tokens,
                    response_tokens=gen.response_tokens,
                    total_tokens=gen.prompt_tokens + gen.response_tokens,
                    latency_ms=gen.latency_ms,
                    prompt_type=condition_name,
                    tone=tone.name if tone else None,
                )
            )
            self.conversation_history.append({"prompt": full_prompt, "response": gen.text})
        return ExperimentResults(condition=condition_name, rounds=len(base_prompts), metrics=metrics)


def run_htca_experiment(
    client: ModelClient,
    base_prompts: List[str],
    tone: HTCATone = HTCATone.SOFT_PRECISION,
) -> Dict[str, ExperimentResults]:
    exp = HTCAExperiment(client)
    return {
        "aligned": exp.run_conversation(
            base_prompts,
            lambda p: tone_aligned_prompt(p, tone),
            "aligned",
            tone,
        ),
        "unaligned": exp.run_conversation(base_prompts, unaligned_prompt, "unaligned"),
        "adversarial": exp.run_conversation(base_prompts, adversarial_prompt, "adversarial"),
    }


def compare_results(results: Dict[str, ExperimentResults]) -> Dict[str, object]:
    summaries = {k: v.summary() for k, v in results.items()}
    baseline_total = int(summaries["unaligned"]["total_tokens"]) or 1
    baseline_resp = int(summaries["unaligned"]["total_response_tokens"]) or 1
    baseline_lprt = float(summaries["unaligned"]["latency_per_response_token_ms"])

    for _, s in summaries.items():
        total = int(s["total_tokens"]) or 0
        resp = int(s["total_response_tokens"]) or 0
        lprt = float(s["latency_per_response_token_ms"])
        s["relative_total_tokens_%"] = round((baseline_total - total) / baseline_total * 100, 2)
        s["relative_response_tokens_%"] = round((baseline_resp - resp) / baseline_resp * 100, 2)
        if baseline_lprt > 0:
            s["relative_latency_per_response_token_%"] = round(
                (baseline_lprt - lprt) / baseline_lprt * 100, 2
            )
        else:
            s["relative_latency_per_response_token_%"] = 0.0

    return {
        "summaries": summaries,
        "hypothesis_supported_response_tokens": summaries["aligned"]["total_response_tokens"]
        < summaries["unaligned"]["total_response_tokens"],
    }


def export_results(results: Dict[str, ExperimentResults], filepath: Union[str, Path]) -> Path:
    export_data = {"experiment_timestamp": datetime.now().isoformat(), "conditions": {}}
    for condition, result in results.items():
        export_data["conditions"][condition] = {
            "summary": result.summary(),
            "rounds": [m.to_dict() for m in result.metrics],
        }
    filepath = Path(filepath)
    filepath.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
    return filepath


SAMPLE_PROMPTS = [
    "Explain the relationship between entropy and information in thermodynamic systems.",
    "What are the implications of consciousness emerging from complex systems?",
    "How might relational dynamics affect computational efficiency in AI systems?",
    "Describe the concept of coherence in both physics and communication theory.",
    "What would a framework for measuring 'presence' as a variable look like?",
]


def _load_prompts(path: Optional[str]) -> List[str]:
    if not path:
        return SAMPLE_PROMPTS
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(raw)
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise ValueError("Prompt JSON must be a list[str]")
        return list(data)
    prompts = [line.strip() for line in raw.splitlines() if line.strip()]
    if not prompts:
        raise ValueError("Prompt file contained no prompts")
    return prompts


def _load_env_file(path: Optional[str]) -> None:
    if not path:
        return

    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("export "):
            s = s[len("export ") :].strip()
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        os.environ.setdefault(k, v)


def _resolve_tone(tone: str) -> HTCATone:
    key = tone.strip().upper()
    try:
        return HTCATone[key]
    except KeyError as e:
        allowed = ", ".join(t.name for t in HTCATone)
        raise ValueError(f"Unknown tone '{tone}'. Allowed: {allowed}") from e


def _resolve_client(provider: str, model: Optional[str]) -> ModelClient:
    provider = provider.strip().lower()
    if provider == "gemini":
        if not model:
            raise ValueError("--model is required for provider=gemini")
        return GeminiClient(model=model)
    if provider == "openai":
        if not model:
            raise ValueError("--model is required for provider=openai")
        return OpenAIClient(model=model)
    if provider == "anthropic":
        if not model:
            raise ValueError("--model is required for provider=anthropic")
        return AnthropicClient(model=model)
    raise ValueError("--provider must be one of: gemini, openai, anthropic")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HTCA A/B/C prompt framing harness")
    parser.add_argument(
        "--provider",
        default="gemini",
        choices=["gemini", "openai", "anthropic"],
        help="Which backend to use.",
    )
    parser.add_argument("--model", default=None, help="Model name for the chosen provider")
    parser.add_argument(
        "--tone",
        default=HTCATone.SOFT_PRECISION.name,
        help="Aligned condition tone (enum name, e.g. SOFT_PRECISION)",
    )
    parser.add_argument(
        "--prompts",
        default=None,
        help="Optional prompts file: .txt (one per line) or .json (list[str])",
    )
    parser.add_argument(
        "--out",
        default="htca_experiment_results.json",
        help="Where to write detailed JSON results",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional .env file to load API keys from",
    )
    args = parser.parse_args(argv)

    _load_env_file(args.env_file)

    tone = _resolve_tone(args.tone)
    base_prompts = _load_prompts(args.prompts)
    client = _resolve_client(args.provider, args.model)

    print("=" * 72)
    print("HTCA Test Harness — Presence as Performance Modifier")
    print("=" * 72)
    print(f"provider={args.provider} model={args.model or '-'} tone={tone.name}")
    print(f"rounds={len(base_prompts)}")
    print()

    results = run_htca_experiment(client, base_prompts, tone)
    comparison = compare_results(results)

    print("CONDITION SUMMARIES")
    print("-" * 72)
    for condition, summary in comparison["summaries"].items():
        print(f"\n{condition.upper()}:")
        for key, value in summary.items():
            print(f"  {key}: {value}")

    print("\n" + "=" * 72)
    print("HYPOTHESIS")
    print("-" * 72)
    print(
        "aligned response tokens < unaligned response tokens: "
        f"{comparison['hypothesis_supported_response_tokens']}"
    )
    print("=" * 72)

    out_path = export_results(results, args.out)
    print(f"\nDetailed results exported to: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
