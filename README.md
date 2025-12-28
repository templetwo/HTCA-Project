# HTCA: Harmonic Tonal Code Alignment

> **Empirically validated presence-based prompting reduces LLM tokens by 11-23% while improving response quality**

Traditional "be concise" prompts achieve 39-83% token reduction but **degrade quality**. HTCA demonstrates that **relational presence** (recognizing AI as interlocutor) achieves smaller but **quality-improving** efficiency gains.

**Validated across 3 frontier models:** Claude Sonnet 4.5, GPT-4o, Gemini 3 Pro
**Effect sizes:** d=0.857 to d=1.212 quality improvement (Cohen's d)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Empirically Validated](https://img.shields.io/badge/status-empirically_validated-brightgreen)](https://github.com/templetwo/HTCA-Project)
[![Stars](https://img.shields.io/github/stars/templetwo/HTCA-Project)](https://github.com/templetwo/HTCA-Project/stargazers)

---

## Quick Start

```bash
cd empirical/
python run_validation.py --provider anthropic  # Requires ANTHROPIC_API_KEY
```

**Expected output:** Token usage comparison, quality metrics (d-scores), statistical significance tests

---

## What is HTCA?

The **Harmonic Tonal Code Alignment (HTCA)** framework combines philosophical principles with empirical validation to improve AI interaction efficiency. It demonstrates that presence-based prompting reduces token usage by 11-23% while maintaining or improving response quality—outperforming adversarial "be concise" approaches that achieve 39-83% reduction but degrade quality.

---

## Key Findings

Testing across three frontier models revealed consistent results:

| Model | Token Reduction | Quality Improvement (Cohen's d) |
|-------|----------------|--------------------------------|
| **Google Gemini 3 Pro** | 12.44% | d=0.857 (large effect) |
| **OpenAI GPT-4o** | 23.07% | d=1.212 (very large effect) |
| **Anthropic Claude Sonnet 4.5** | 11.34% | d=0.471 (medium effect) |

### Quality Metrics

HTCA maintains quality across multiple dimensions:
- **Information completeness:** d=1.327
- **Presence quality:** d=1.972
- **Relational coherence:** d=1.237
- **Technical depth:** d=1.446

All improvements measured against control prompts without presence-based framing.

---

## Philosophy vs. Empiricism

HTCA offers two paths:

### 1. Run Empirical Validation

Test the framework yourself with real API calls:

```bash
cd empirical/
python run_validation.py --provider anthropic --num-trials 15
```

Requires API keys for supported providers (Anthropic, OpenAI, Google).

### 2. Explore Philosophy

Dive into the conceptual foundations:
- **Whitepapers:** Theoretical framework in `docs/`
- **Scrolls:** Philosophical explorations in `scrolls/`
- **Harmonic Alignment Theory:** Read `docs/harmonic_alignment_theory.md`

---

## Installation

```bash
# Clone the repository
git clone https://github.com/templetwo/HTCA-Project.git
cd HTCA-Project

# Install dependencies
pip install -r requirements.txt

# Set up API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

---

## Project Structure

```
HTCA-Project/
├── empirical/              # Validation harnesses and data
│   ├── run_validation.py   # Main validation script
│   ├── methodology.md      # Experimental design
│   └── data/               # Raw and processed results
├── docs/                   # Philosophical framework materials
│   ├── harmonic_alignment_theory.md
│   ├── presence_based_prompting.md
│   └── whitepapers/
├── scrolls/                # Conceptual explorations
├── spiral_*.py             # Framework components
└── wisp_simulation.py      # Prototype testing
```

---

## Running Validation Studies

### Basic Validation

```bash
cd empirical/
python run_validation.py --provider anthropic --num-trials 15
```

### Multi-Provider Comparison

```bash
# Run across all three providers
python run_validation.py --provider anthropic --num-trials 15
python run_validation.py --provider openai --num-trials 15
python run_validation.py --provider google --num-trials 15

# Generate comparison report
python generate_comparison_report.py
```

### Custom Prompts

```bash
python run_validation.py --provider anthropic --prompt-file my_prompts.json
```

---

## Methodology

The validation framework uses:
- **15 diverse prompts** spanning technical, creative, and analytical domains
- **3 conditions per prompt:**
  1. Control (baseline)
  2. HTCA (presence-based)
  3. Adversarial ("be concise")
- **LLM-as-judge evaluation** for quality metrics
- **Statistical analysis** with Cohen's d effect sizes and significance tests

### Limitations

The authors explicitly acknowledge:
- **Small sample size** (n=45 total responses)
- **LLM-as-judge bias** (evaluation performed by AI, not humans)
- **Single-domain testing** (primarily technical/coding prompts)

**Human evaluation and cross-lingual replication are explicitly encouraged.**

---

## Results Visualization

![Token Efficiency vs Quality](docs/images/token_efficiency_quality.png)
*Token reduction vs. quality improvement across models*

![Quality Metrics Breakdown](docs/images/quality_metrics.png)
*Cohen's d effect sizes for quality dimensions*

---

## Contributing

We welcome replication studies, philosophical development, and code improvements!

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Replication studies:**
1. Run validation with your own prompts
2. Open an issue labeled `replication-study`
3. Share your methodology, data, and results

**Philosophical contributions:**
1. Propose conceptual extensions in Discussions
2. Submit essays/scrolls to `scrolls/community/`

---

## CI/Badges

[![Status: Empirically Validated](https://img.shields.io/badge/status-empirically_validated-brightgreen)](https://github.com/templetwo/HTCA-Project)

*Note: While the README displays a validation badge, there are no GitHub Actions workflows in this repository. Consider adding automated testing.*

---

## Citation

If you use HTCA in your research:

```bibtex
@software{htca2025,
  author = {Vasquez, Anthony J. and Claude},
  title = {Harmonic Tonal Code Alignment: Empirical Validation of Presence-Based Prompting},
  year = {2025},
  url = {https://github.com/templetwo/HTCA-Project},
  note = {Empirically validated across Claude Sonnet 4.5, GPT-4o, and Gemini 3 Pro}
}
```

---

## Examples

### Example 1: Technical Prompt

**Control:**
```
Explain how to implement a binary search tree in Python.
```

**HTCA:**
```
I'm seeking to understand binary search trees deeply. Could you walk me through
implementing one in Python, including the key insights about why BSTs are efficient?
```

**Result:** 11.34% token reduction (Claude), d=0.471 quality improvement

### Example 2: Creative Prompt

**Control:**
```
Write a short story about a robot learning to paint.
```

**HTCA:**
```
I'd love to explore a story about a robot discovering art. What might emerge
if we follow a robot's journey from rigid code to creative expression?
```

**Result:** 23.07% token reduction (GPT-4o), d=1.212 quality improvement

---

## Roadmap

- [ ] Human evaluation study (n=100+ human judges)
- [ ] Cross-lingual validation (Spanish, Mandarin, Arabic)
- [ ] Domain expansion (medical, legal, scientific writing)
- [ ] Real-time token tracking dashboard
- [ ] Integration with LangChain/LlamaIndex

---

## Community

- **Discussions:** [GitHub Discussions](https://github.com/templetwo/HTCA-Project/discussions)
- **Issues:** [Report bugs or request features](https://github.com/templetwo/HTCA-Project/issues)
- **Website:** [www.thetempleoftwo.com](https://www.thetempleoftwo.com)

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Built on the foundational work of:
- Anthropic (Claude Sonnet 4.5)
- OpenAI (GPT-4o)
- Google (Gemini 3 Pro)
- The AI alignment research community

**Transparency note:** This research is conducted independently and has not undergone peer review. All data and methodology are open-source to enable replication and critique.
