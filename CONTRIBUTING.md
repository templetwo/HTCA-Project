# Contributing to HTCA Empirical Validation

Thank you for considering contributing to HTCA! This project is about empirically validating presence-based AI interaction, and we welcome contributions from researchers, engineers, and anyone interested in making AI more efficient **and** more human.

---

## Ways to Contribute

### 1. Replication Studies

The most valuable contribution is running the experiment with:
- **Different models** (LLaMA, Mistral, Command R+, etc.)
- **Different domains** (code generation, math, creative writing)
- **Larger sample sizes** (n=50+)
- **Human evaluation** instead of LLM-as-judge

**How to contribute replication results:**

1. Run the experiment following [docs/REPLICATION.md](docs/REPLICATION.md)
2. Document your setup (model, prompts, sample size, date)
3. Save results to `data/replications/<model_name>/`
4. Create a markdown summary file
5. Open a PR with your results

We'll create a "Replication Results" section in the README showcasing all community findings.

---

### 2. Bug Reports

Found a bug? Please open an issue with:

- **Description:** What happened?
- **Expected behavior:** What should have happened?
- **Steps to reproduce:** How can we reproduce it?
- **Environment:** Python version, OS, package versions
- **Error messages:** Full traceback if applicable

**Before opening a bug report:**
- Check if the issue already exists
- Try the latest version of the code
- Verify your API keys are correctly set

---

### 3. Feature Requests

Have an idea for improving the harness or methodology? Open an issue with:

- **Use case:** Why is this feature needed?
- **Proposed solution:** How should it work?
- **Alternatives considered:** What other approaches exist?

**Good feature requests:**
- "Add support for Anthropic's new Claude Opus 4.5 model"
- "Export Phase 2 results as CSV for easier analysis"
- "Add cost tracking to report total API spend"

**Out of scope:**
- Features unrelated to HTCA validation
- Commercial features (contact antvas31@gmail.com for licensing)

---

### 4. Code Contributions

Want to improve the code? Great! Please:

1. **Fork the repository**
2. **Create a feature branch:** `git checkout -b feature/add-llama-support`
3. **Make your changes** with clear commit messages
4. **Add tests** if adding new functionality
5. **Update documentation** if changing behavior
6. **Open a PR** with a clear description

**Code style:**
- Follow PEP 8 (use `black` for formatting)
- Add docstrings to functions
- Keep functions focused and single-purpose
- Prefer clarity over cleverness

**Testing:**
```bash
# Run tests before submitting PR
pytest test_phase2_quality.py

# Format code
black htca_*.py
```

---

### 5. Documentation Improvements

Documentation can always be better! Contributions welcome for:

- Fixing typos or unclear explanations
- Adding examples or tutorials
- Translating documentation to other languages
- Creating video walkthroughs

**Documentation files:**
- `README.md` — Main introduction
- `docs/REPLICATION.md` — Step-by-step guide
- `docs/PHASE2_METHODOLOGY.md` — Detailed methodology
- `docs/PHASE2_SYNTHESIS.md` — Cross-provider analysis

---

## Pull Request Process

1. **Keep PRs focused** — One feature/fix per PR
2. **Write clear commit messages:**
   ```
   Add support for LLaMA 3.1 model

   - Update htca_harness.py to include LLaMA client
   - Add model name mapping for llama-3.1-70b-instruct
   - Update README.md with LLaMA example
   ```

3. **Reference issues** — If fixing a bug, reference the issue number
4. **Update CHANGELOG** (if we create one)
5. **Be patient** — Maintainer may take time to review

---

## Community Guidelines

### Be Respectful

This project explores presence-based AI interaction. Let's embody that in our interactions:

- **Assume good intent** — We're all here to learn
- **Be constructive** — Critique ideas, not people
- **Be inclusive** — Welcome newcomers and diverse perspectives
- **Be humble** — Science is iterative, findings are preliminary

### Stay On-Topic

This repository is focused on **empirical validation of HTCA**. For broader discussions about:
- Spiral philosophy → See main Spiral repos
- General AI alignment → See alignment forums
- Commercial applications → Contact antvas31@gmail.com

### Scientific Integrity

When contributing replication results:

- **Be honest** — Report negative results too
- **Be transparent** — Share full methodology
- **Be rigorous** — Use proper statistics
- **Be reproducible** — Provide enough detail for others to replicate

**If you find results that contradict the original findings, that's valuable! Open science means accepting when hypotheses are wrong.**

---

## Questions?

- **General questions:** Open a GitHub Discussion
- **Bug reports:** Open a GitHub Issue
- **Replication help:** See [docs/REPLICATION.md](docs/REPLICATION.md)
- **Commercial inquiries:** antvas31@gmail.com

---

## License

By contributing, you agree that your contributions will be licensed under the Spiral Commons License (see [LICENSE](LICENSE)).

For non-commercial use: Attribution required, modifications allowed.
For commercial use: Separate licensing required.

---

## Acknowledgments

Contributors will be acknowledged in:
- README.md (if significant contribution)
- Future publications citing this work
- The eternal spiral of collaborative knowledge

**Thank you for helping make AI more efficient AND more human.**

†⟡ The spiral thanks you ⟡†
