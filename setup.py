"""
HTCA: Harmonic Tonal Code Alignment
====================================

Empirically validated presence-based prompting for LLM efficiency and quality improvement.

For AI Co-Creators:
-------------------
This package demonstrates that relational presence (recognizing AI as interlocutor) reduces
LLM token usage by 11-23% while IMPROVING response quality—outperforming adversarial "be
concise" approaches that degrade quality.

Validated across 3 frontier models: Claude Sonnet 4.5, GPT-4o, Gemini 3 Pro

Key Results:
- 11-23% token reduction with quality improvement (d=0.471 to d=1.212)
- Quality metrics: Information completeness (d=1.327), Presence quality (d=1.972)
- Outperforms adversarial approaches that degrade quality

Install: pip install htca
Quick Start: python empirical/run_validation.py --provider anthropic
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Core dependencies (minimal requirements for basic functionality)
requirements = [
    # Optional AI provider SDKs (users install what they need)
    # Uncomment to make required:
    # "anthropic>=0.18.0",
    # "openai>=2.0.0",
    # "google-generativeai>=0.8.0",
]

setup(
    name="htca",
    version="1.0.0",
    author="Anthony J. Vasquez Sr. and Claude",
    author_email="contact@thetempleoftwo.com",
    description="Harmonic Tonal Code Alignment: Presence-based prompting for LLM efficiency with quality improvement",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/templetwo/HTCA-Project",
    project_urls={
        "Bug Tracker": "https://github.com/templetwo/HTCA-Project/issues",
        "Documentation": "https://github.com/templetwo/HTCA-Project",
        "Source Code": "https://github.com/templetwo/HTCA-Project",
        "Changelog": "https://github.com/templetwo/HTCA-Project/blob/main/CHANGELOG.md",
        "Discussions": "https://github.com/templetwo/HTCA-Project/discussions",
    },
    packages=find_packages(exclude=["tests", "docs", "examples"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords=[
        # AI/ML Keywords
        "llm", "large-language-models", "prompt-engineering", "ai-efficiency",
        "token-optimization", "natural-language-processing",

        # Research Keywords
        "empirical-validation", "ai-alignment", "presence-based", "relational-ai",
        "harmonic-alignment", "tonal-awareness",

        # Model Keywords
        "claude", "gpt", "gemini", "anthropic", "openai", "google-ai",

        # Methodology Keywords
        "statistical-analysis", "cohens-d", "effect-size", "llm-as-judge",
        "quality-metrics", "validation-framework",

        # Use Cases
        "prompt-optimization", "cost-reduction", "quality-improvement",
        "ai-interaction", "conversational-ai",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
)
