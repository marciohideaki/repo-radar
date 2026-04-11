---
description: Analisa e classifica um repositório GitHub via repo-radar CLI (SQLite + LLM), registrando o veredito em PROJECT_EVALUATIONS.md
---

Analise o repositório GitHub informado como argumento usando o CLI `repo-radar`, persistindo em SQLite e registrando a avaliação em `/opt/references/PROJECT_EVALUATIONS.md`.

## Argumento

`$ARGUMENTS` — URL do repositório GitHub a avaliar (ex: `https://github.com/owner/repo`)

## Passos de Execução

### 1. Verificar se repo-radar está instalado

```bash
which repo-radar || pip install -e /opt/references/repo-radar
```

Se o diretório `/opt/references/repo-radar` não existir:
```bash
git clone https://github.com/marciohideaki/repo-radar /opt/references/repo-radar
pip install -e /opt/references/repo-radar
```

### 2. Garantir que o `.env` está configurado

Verifique se existe `/opt/references/repo-radar/.env`. Se não existir, crie a partir do `.env.example` e configure `LLM_PROVIDER` e a API key correspondente ao agente em execução:

- Claude Code → `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY`
- Codex → `LLM_PROVIDER=openai` + `OPENAI_API_KEY`
- Gemini → `LLM_PROVIDER=gemini` + `GEMINI_API_KEY`
- Ollama → `LLM_PROVIDER=ollama`

### 3. Executar a análise

```bash
cd /opt/references/repo-radar
repo-radar add "$ARGUMENTS"
```

O CLI irá:
- Buscar metadados via GitHub API
- Clonar o repositório em `repos/`
- Calcular scores heurísticos (doc, code, coerência, maturidade)
- Consultar o LLM para o veredito final (classificação + rationale)
- Persistir tudo no SQLite (`data/radar.db`) com histórico append-only

### 4. Exibir resultado

```bash
repo-radar show <nome-do-repo>
```

### 5. Exportar para PROJECT_EVALUATIONS.md

Com base nos dados retornados pelo CLI (scores, classificação, rationale, metadados), adicione ou atualize a entrada em `/opt/references/PROJECT_EVALUATIONS.md` seguindo o template exato:

```markdown
## owner/repo

- Local path: `/opt/references/<nome>`
- Status: `adopt` | `partial` | `reject`
- Priority: `high` | `medium` | `low`
- Recommended action: <ação objetiva em uma frase>

#### What To Reuse

- Item concreto com contexto (baseado no rationale do LLM e evidências)

#### What To Avoid

- Item concreto com contexto

#### Risks

- Risco específico

#### Evidence

- `path/to/file`: nota objetiva

#### Notes

- Scores: interest=X doc=X code=X coherence=X maturity=X
- Stars: X | Forks: X | Contributors: X | Releases: X
- Language: X | License: X | LLM: <provider>
- Last push: YYYY-MM-DD
- radar.db: `/opt/references/repo-radar/data/radar.db`
```

**Mapeamento de classificação:**
- `INTERESTING` → `adopt`
- `INCORPORATE` → `partial`
- `WATCH` → `partial` (com nota de monitoramento)
- `REDUNDANT` → `reject`
- `DISCARD` → `reject`

Se o repositório já existir no arquivo, **atualize** a entrada existente em vez de duplicar.

## Regras

- O SQLite é a fonte primária de verdade — PROJECT_EVALUATIONS.md é um relatório derivado.
- Use o rationale do LLM como base para os campos What To Reuse / What To Avoid.
- Cite arquivos reais encontrados no clone para a seção Evidence.
- Sempre inclua os scores numéricos nas Notes para rastreabilidade.
