# Testes de Prompts - TJDFT API

Avaliação automatizada de prompts usando [Promptfoo](https://promptfoo.dev).

## Instalação

```bash
# Via npm (recomendado)
npm install -g promptfoo

# Ou via npx (sem instalação)
npx promptfoo eval
```

## Estrutura

```
tests/prompts/
├── promptfooconfig.yaml    # Configuração principal
├── datasets/
│   ├── resumo_cases.yaml   # Testes de resumo
│   ├── comparar_cases.yaml # Testes de comparação
│   └── explicar_cases.yaml # Testes de explicação
├── results/                # Resultados das avaliações
└── README.md
```

## Uso

### Avaliar todos os prompts

```bash
cd /root/projetos/tjdft-api
npx promptfoo eval
```

### Ver UI interativa

```bash
npx promptfoo view
```

### Testar apenas um tipo

```bash
# Apenas resumos
npx promptfoo eval --tests tests/prompts/datasets/resumo_cases.yaml

# Apenas comparações
npx promptfoo eval --tests tests/prompts/datasets/comparar_cases.yaml
```

### Comparar modelos

```bash
# Apenas GPT-4o
npx promptfoo eval --providers openai:gpt-4o

# Apenas GPT-4o-mini
npx promptfoo eval --providers openai:gpt-4o-mini
```

## Variáveis de Ambiente

```bash
# Obrigatório
export OPENAI_API_KEY=sk-...

# Opcional (para outros providers)
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-...
```

## CI/CD

Os testes rodam automaticamente em PRs que modificam prompts:

```yaml
# .github/workflows/prompt-eval.yml
name: Prompt Evaluation
on:
  pull_request:
    paths:
      - 'tests/prompts/**'

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm install -g promptfoo
      - run: cd tests/prompts && promptfoo eval --max-concurrency 3
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Adicionando Novos Testes

1. Crie um arquivo em `datasets/`:

```yaml
- description: "Meu novo teste"
  vars:
    ementa: "Texto da ementa..."
  assert:
    - type: is-json
    - type: llm-rubric
      value: "Critério de avaliação..."
```

2. Adicione o prompt correspondente em `promptfooconfig.yaml`:

```yaml
prompts:
  - id: meu-novo-prompt
    raw: |
      Instrução do prompt...
      {{variavel}}
```

## Interpretação dos Resultados

- **Score 1-2**: Prompt inadequado, refazer
- **Score 3**: Aceitável, pode melhorar
- **Score 4-5**: Bom, pronto para produção

## Links Úteis

- [Documentação Promptfoo](https://promptfoo.dev/docs/)
- [Tipos de Assertion](https://promptfoo.dev/docs/configuration/expected-outputs/)
- [LLM-as-Judge](https://promptfoo.dev/docs/configuration/expected-outputs/#llm-rubric)
