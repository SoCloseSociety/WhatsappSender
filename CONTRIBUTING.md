# Contributing to WhatsApp Bulk Sender

Thank you for your interest in contributing! Here's how you can help.

## How to Contribute

### Reporting Bugs

1. Check existing [Issues](https://github.com/SoCloseSociety/WhatsappSender/issues) first
2. Open a new issue with:
   - Your OS (Windows / macOS / Linux)
   - Python version (`python --version`)
   - WhatsApp provider (Twilio / Meta)
   - Steps to reproduce
   - Error message / logs

### Suggesting Features

Open an issue with the `enhancement` label describing:
- What problem it solves
- How it should work
- Any alternatives you considered

### Submitting Code

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test on your platform
5. Commit with clear messages: `git commit -m "Add: description of change"`
6. Push and open a Pull Request

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small
- Use type hints for function parameters

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/WhatsappSender.git
cd WhatsappSender
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
```

## Contribution Ideas

- Support for new providers (Vonage, MessageBird)
- React/Vue web interface
- Campaign scheduling (deferred sending)
- Media support (images, documents, audio)
- Import from Google Sheets / CRM APIs

## Questions?

Open an issue or start a discussion. We're happy to help!
