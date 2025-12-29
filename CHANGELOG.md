# Changelog

All notable changes to HTCA Project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Human evaluation study (n=100+ human judges)
- Cross-lingual validation (Spanish, Mandarin, Arabic)
- Domain expansion (medical, legal, scientific writing)
- Real-time token tracking dashboard
- LangChain/LlamaIndex integration

## [1.0.0] - 2025-01-15

### Added
- Empirical validation across 3 frontier models (Claude Sonnet 4.5, GPT-4o, Gemini 3 Pro)
- Presence-based prompting methodology showing 11-23% token reduction with quality improvement
- Effect size measurements (Cohen's d) ranging from d=0.471 to d=1.212
- Quality metrics validation:
  - Information completeness: d=1.327
  - Presence quality: d=1.972
  - Relational coherence: d=1.237
  - Technical depth: d=1.446
- Validation harness with 15 diverse prompts
- LLM-as-judge evaluation framework
- Statistical analysis tools
- Community files: improved README, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- GitHub Discussions and issue/PR templates

### Documented Limitations
- Small sample size (n=45 total responses)
- LLM-as-judge bias (evaluation by AI, not humans)
- Single-domain testing (primarily technical/coding prompts)

### Research Notes
- HTCA demonstrates that relational presence reduces tokens while improving quality
- Outperforms adversarial "be concise" approaches which achieve higher reduction but degrade quality
- Results consistent across different model architectures
- Human evaluation and cross-lingual replication explicitly encouraged

---

[Unreleased]: https://github.com/templetwo/HTCA-Project/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/templetwo/HTCA-Project/releases/tag/v1.0.0
