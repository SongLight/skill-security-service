# Contributing to Skill Security Scanner

Thank you for your interest in contributing to Skill Security Scanner! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## 🏛️ Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## 🤔 How Can I Contribute?

### Reporting Bugs

- Use GitHub Issues to report bugs
- Include detailed steps to reproduce the issue
- Include relevant configuration and environment details
- Include screenshots if applicable

### Suggesting Features

- Use GitHub Issues to suggest features
- Explain the problem and proposed solution
- Include use cases and examples

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/`)
5. Submit a Pull Request

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- pytest (for testing)

### Clone the Repository

```bash
git clone https://gitee.com/yzj1/skill-security-scanner.git
cd skill-security-scanner
```

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run Tests

```bash
pytest tests/
```

### Run Linting

```bash
flake8 scripts/
mypy scripts/
```

## 📤 Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Follow the coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Tests and Linting**
   ```bash
   pytest tests/
   flake8 scripts/
   mypy scripts/
   ```

4. **Commit Your Changes**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
   
   Commit message format:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `style:` - Code style changes
   - `refactor:` - Code refactoring
   - `test:` - Adding tests
   - `chore:` - Maintenance

5. **Push to Your Branch**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Provide a detailed description of your changes
   - Reference any related issues
   - Include test results

## 📐 Coding Standards

### Python Style

- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use type hints

### Naming Conventions

- Classes: `CamelCase`
- Functions: `snake_case`
- Variables: `snake_case`
- Constants: `UPPER_CASE`

### Type Hints

```python
def scan_file(file_path: str) -> List[Finding]:
    """Scan a file for security issues."""
    pass
```

### Documentation

- Add docstrings to all public functions
- Use Google-style docstrings
- Document all parameters and return values

```python
def scan_skill(skill: Dict[str, Any]) -> List[Finding]:
    """Scan a skill for security issues.
    
    Args:
        skill: Skill dictionary with 'name' and 'path' keys
        
    Returns:
        List of security findings
    """
    pass
```

## 🧪 Testing

### Test Structure

```
tests/
├── test_detectors/
│   ├── test_secrets.py
│   ├── test_injection.py
│   └── ...
├── test_reporters/
│   ├── test_html_reporter.py
│   └── ...
├── test_api/
│   └── test_api_server.py
└── test_integration.py
```

### Writing Tests

- Use pytest framework
- Test all public functions
- Include edge cases
- Use fixtures for common test data

```python
def test_secrets_detector():
    """Test secrets detector with sample file."""
    detector = SecretsDetector()
    findings = detector.scan("test_file.py")
    assert len(findings) > 0
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_detectors/test_secrets.py

# Run with coverage
pytest --cov=scripts --cov-report=html tests/
```

## 📖 Documentation

### README Updates

- Update the README.md for new features
- Include usage examples
- Document configuration options

### API Documentation

- Document all API endpoints
- Include request/response examples
- Document error codes

### Code Comments

- Add comments for complex logic
- Explain "why" not "what"
- Keep comments up to date

## 🙏 Thank You!

Thank you for contributing to Skill Security Scanner! Your efforts help make the project better for everyone.
