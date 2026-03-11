# Contributing

Obrigado pelo interesse em contribuir!

## Development Setup

```bash
# Fork e clone
git clone https://github.com/seu-usuario/tjdft-api
cd tjdft-api

# Setup
python -m venv .venv
source .venv/bin/activate
make install

# Pre-commit hooks
pre-commit install
```

## Running Tests

```bash
make test
```

## Code Style

- Use Black para formatação
- Use Ruff para linting
- Use MyPy para type checking

```bash
make format
make lint
```

## Pull Request Process

1. Crie uma branch: `git checkout -b feature/minha-feature`
2. Commit: `git commit -m "Add: minha feature"`
3. Push: `git push origin feature/minha-feature`
4. Abra um Pull Request

## License

Ao contribuir, você concorda que sua contribuição será licenciada sob a MIT License.