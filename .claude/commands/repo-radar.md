---
description: Analisa e classifica um repositório GitHub, registrando o veredito em PROJECT_EVALUATIONS.md
---

Analise o repositório GitHub informado como argumento e registre a avaliação em `/opt/references/PROJECT_EVALUATIONS.md`.

## Argumento

`$ARGUMENTS` — URL do repositório GitHub a avaliar (ex: `https://github.com/owner/repo`)

## Passos de Execução

### 1. Coletar metadados via GitHub API

Use o MCP do GitHub ou `curl` para obter:
- Stars, forks, open issues, contributors, releases
- Linguagem principal e todas as linguagens
- Data do último push (para calcular atividade)
- Tópicos, licença, se está arquivado ou é fork
- Descrição e URL

### 2. Clonar o repositório localmente

```bash
git clone --depth=1 <clone_url> /tmp/radar-<repo-name>
```

Se o diretório já existir, faça `git pull` para atualizar.

### 3. Análise heurística local (sem custo de API)

Inspecione o conteúdo clonado e pontue cada dimensão de 0 a 100:

#### Score de Documentação (peso 20%)
- README presente e substancial (+10/5/5/5)
- CHANGELOG presente (+10)
- Pasta `docs/` ou `wiki/` (+10)
- Pasta `examples/` ou `demo/` (+10)
- LICENSE presente (+10)
- CONTRIBUTING / CODE_OF_CONDUCT (+10)
- `.github/` presente (+5)
- API docs / swagger / openapi (+5)

#### Score de Código/Estrutura (peso 30%)
- Diretório de testes (`tests/`, `spec/`, `__tests__/`) (+15/+5 se >5 arquivos)
- CI/CD configurado (GitHub Actions, CircleCI, Travis) (+15)
- Dockerfile (+7) e docker-compose (+3)
- Package manager detectado (package.json, requirements.txt, go.mod, etc.) (+10)
- Estrutura organizada (`src/`, `lib/`, `cmd/`) (+10)
- Config de lint/format (+5)

#### Score de Coerência README↔Código (peso 20%)
Base: 50. Para cada item mencionado no README, verificar se existe no código (+pts se existe, -pts/2 se não existe):
- Docker mencionado → Dockerfile
- Testes mencionados → pasta de testes
- Instalação descrita → manifesto de dependências
- CLI mencionado → pasta cmd/bin
- API mencionada → pasta api/routes
- Config mencionada → arquivos de config
- CI/CD mencionado → config de CI

#### Score de Maturidade (peso 30%)
- Stars: ≥50k=25, ≥500=18, ≥50=10, ≥5=5
- Atividade (dias desde último push): ≤30d=20, ≤90d=15, ≤365d=8, ≤730d=3
- Forks: ≥500=15, ≥50=10, ≥5=5
- Releases: ≥5=15, ≥1=8
- Contribuidores: ≥20=15, ≥3=8
- Penalidades: arquivado=score*0.3, fork=-10

**Interest Score** = doc×0.2 + code×0.3 + coherence×0.2 + maturity×0.3

### 4. Formular o veredito

Com base nos scores e na sua análise do código e README, classifique:

| Classe | Critério |
|--------|----------|
| `adopt` | Alto potencial, maduro, docs coerentes. Vale adotar agora. |
| `partial` | Contém algo concreto para portar/usar, mas não o todo. |
| `reject` | Abandonado, baixa qualidade, docs enganosas, ou irrelevante. |

Identifique:
- **What To Reuse**: o que tem valor concreto para portar
- **What To Avoid**: riscos, acoplamentos, más práticas
- **Risks**: riscos de adopção
- **Evidence**: arquivos/trechos específicos que embasam o veredito

### 5. Registrar em PROJECT_EVALUATIONS.md

Adicione ou atualize a entrada do repositório em `/opt/references/PROJECT_EVALUATIONS.md` seguindo o template exato:

```markdown
## owner/repo

- Local path: `/opt/references/<nome>`
- Status: `adopt` | `partial` | `reject`
- Priority: `high` | `medium` | `low`
- Recommended action: <ação objetiva em uma frase>

#### What To Reuse

- Item concreto com contexto

#### What To Avoid

- Item concreto com contexto

#### Risks

- Risco específico

#### Evidence

- `path/to/file`: nota objetiva

#### Notes

- Scores: interest=X doc=X code=X coherence=X maturity=X
- Stars: X | Forks: X | Contributors: X | Releases: X
- Language: X | License: X
- Last push: YYYY-MM-DD
```

Se o repositório já existir no arquivo, **atualize** a entrada existente em vez de duplicar.

## Regras

- Seja objetivo e preciso. Evite genéricos como "boa documentação" sem evidenciar.
- Cite arquivos e caminhos reais encontrados no clone.
- Se o repo não puder ser clonado (privado, removido), use apenas os metadados da API.
- Sempre inclua os scores numéricos nas Notes para rastreabilidade.
- Remova o clone temporário após gravar a avaliação: `rm -rf /tmp/radar-<repo-name>`
