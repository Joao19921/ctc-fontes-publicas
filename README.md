# CTC Tech — Fontes Públicas

API autenticada e somente leitura para consultas públicas ao PNCP e à API de Dados Abertos do Compras.gov.br.

## O que está publicado

- Cliente Python para PNCP Consulta e Compras.gov.br (somente HTTP GET).
- Paginação, validação de controle PNCP e download documental PNCP com SHA-256.
- API HTTP com autenticação Bearer para consultas.
- Blueprint de implantação isolada no Render.

**Este repositório é público.** Por segurança, não contém as skills internas, parâmetros financeiros, DRE, CNPJs de estabelecimentos, planilhas ou documentos operacionais confidenciais da CTC. Esses materiais permanecem no ambiente privado do Projeto Licitações.

## Endpoints

Todos os endpoints, exceto `GET /health`, exigem `Authorization: Bearer <CTC_API_TOKEN>`.

| Método | Endpoint | Uso |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/v1/pncp/publicacoes` | Publicações PNCP; `data_inicial`, `data_final` (AAAAMMDD), `modalidade`; filtros opcionais `uf`, `cnpj`, `pagina`, `tamanho_pagina` |
| GET | `/v1/pncp/propostas` | Contratações com propostas abertas; `data_final` (AAAAMMDD) |
| GET | `/v1/pncp/contratacoes?controle=...` | Detalhe e lista de documentos pelo controle PNCP |
| GET | `/v1/comprasgov/publicacoes` | Dados Abertos Compras.gov.br; datas AAAA-MM-DD |

A documentação OpenAPI estará disponível em `/docs` após a implantação.

## Implantação no Render

1. No Render, selecione **New → Blueprint** e conecte este repositório.
2. Revise o plano gerado pelo `render.yaml`. Ele propõe um único Web Service Free em Ohio.
3. Aprove o plano no Render. O blueprint gera `CTC_API_TOKEN` automaticamente.
4. Copie o token gerado para o cofre de segredos do consumidor da API. Não o publique em issues, código ou logs.
5. Valide `/health` e faça uma consulta autenticada de teste.

O serviço Free pode entrar em suspensão por inatividade e apresentar cold start. Para operação contínua, avalie plano pago conforme a necessidade.

## Execução local

Python 3.10+:

```bash
pip install -r requirements.txt
export CTC_API_TOKEN='defina-um-segredo-local'
uvicorn app:app --reload
```

## Governança e limitações

- Consultas públicas são somente leitura. Não há envio de propostas, lances, esclarecimentos, impugnações ou alterações em portais.
- Metadados localizam documentos; não comprovam aderência, habilitação ou GO/NO GO.
- Pareceres exigem documento primário efetivamente obtido e lido, com item e página.
- A API não faz análise de edital nem substitui os gates humanos do Fluxo 3 e da pré-disputa.
- PNCP/Compras.gov.br podem sofrer indisponibilidade, mudanças de contrato, paginação ou defasagem.
- Outros portais não estão integrados nesta versão.
