# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please email security concerns to: **security@thetempleoftwo.com**

Please include:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if known)

### What to expect

1. **Acknowledgment:** You should receive a response within 48 hours.
2. **Investigation:** We will investigate and determine severity.
3. **Resolution:** We will release a security patch and credit you in release notes (unless you prefer anonymity).

## Security Best Practices

When using HTCA:

### API Key Management
- **Never commit API keys** to version control
- Use environment variables for API keys
- Rotate keys regularly (at least quarterly)

### Data Privacy
- HTCA validation scripts send prompts to AI providers
- Review each provider's data retention policies:
  - [Anthropic](https://www.anthropic.com/legal/privacy)
  - [OpenAI](https://openai.com/policies/privacy-policy)
  - [Google](https://policies.google.com/privacy)
- Avoid sending sensitive/proprietary data in validation experiments

### Dependencies
- Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- Review `requirements.txt` for security advisories

## Responsible Disclosure

We appreciate security researchers. If you discover a vulnerability:
- Give us reasonable time to fix before public disclosure
- We will work with you on a coordinated disclosure timeline
- We will credit you publicly once the fix is released

Thank you for helping keep HTCA secure!
