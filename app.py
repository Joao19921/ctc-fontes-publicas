"""Authenticated, read-only HTTP facade for public procurement APIs."""
from __future__ import annotations

import hmac
import os
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from integracoes.fontes_publicas.client import (
    SourceError,
    pncp_open_proposals,
    pncp_purchase_detail,
    pncp_purchase_documents,
    pncp_search_all_pages,
    compras_gov_search_all_pages,
)

app = FastAPI(
    title="CTC Tech — Fontes Públicas",
    version="1.0.0",
    description="API somente leitura para consultas públicas PNCP e Compras.gov.br.",
    docs_url="/docs",
    redoc_url=None,
)

def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("CTC_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API não configurada: CTC_API_TOKEN ausente.")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Bearer token inválido ou ausente.")

def valid_yyyymmdd(value: str) -> str:
    try:
        date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")
        if len(value) != 8:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Data deve estar no formato AAAAMMDD.") from exc
    return value

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ctc-fontes-publicas-api"}

@app.get("/v1/pncp/publicacoes", dependencies=[Depends(require_token)])
def pncp_publicacoes(
    data_inicial: str = Query(..., description="AAAAMMDD"),
    data_final: str = Query(..., description="AAAAMMDD"),
    modalidade: int = Query(..., ge=1),
    uf: str | None = Query(default=None, min_length=2, max_length=2),
    cnpj: str | None = Query(default=None, min_length=14, max_length=14),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    return pncp_search_all_pages(
        valid_yyyymmdd(data_inicial), valid_yyyymmdd(data_final),
        modalidade=modalidade, uf=uf, cnpj=cnpj,
        pagina=pagina, tamanho_pagina=tamanho_pagina,
    )

@app.get("/v1/pncp/propostas", dependencies=[Depends(require_token)])
def pncp_propostas(
    data_final: str = Query(..., description="AAAAMMDD"),
    modalidade: int | None = Query(default=None, ge=1),
    uf: str | None = Query(default=None, min_length=2, max_length=2),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    from integracoes.fontes_publicas.client import pncp_open_proposals
    return pncp_open_proposals(
        valid_yyyymmdd(data_final), modalidade=modalidade, uf=uf,
        pagina=pagina, tamanho_pagina=tamanho_pagina,
    )

@app.get("/v1/pncp/contratacoes/{controle}", dependencies=[Depends(require_token)])
def pncp_detalhe(controle: str) -> dict[str, Any]:
    return {"controle_pncp": controle, "detalhe": pncp_purchase_detail(controle),
            "documentos": pncp_purchase_documents(controle)}

@app.get("/v1/comprasgov/publicacoes", dependencies=[Depends(require_token)])
def comprasgov_publicacoes(
    data_inicial: str = Query(..., description="AAAA-MM-DD"),
    data_final: str = Query(..., description="AAAA-MM-DD"),
    modalidade: int = Query(default=5, ge=1),
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    try:
        date.fromisoformat(data_inicial)
        date.fromisoformat(data_final)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Datas devem estar no formato AAAA-MM-DD.") from exc
    return compras_gov_search_all_pages(
        data_inicial, data_final, modalidade=modalidade,
        pagina=pagina, tamanho_pagina=tamanho_pagina,
    )

@app.exception_handler(SourceError)
async def source_error_handler(_request, exc: SourceError):
    return JSONResponse(status_code=502, content={"detail": str(exc), "source_error": True})
