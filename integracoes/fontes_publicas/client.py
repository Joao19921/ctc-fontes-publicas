"""Read-only public procurement clients for PNCP and Compras.gov.br."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PNCP_BASE = os.getenv("PNCP_CONSULTA_BASE_URL", "https://pncp.gov.br/api/consulta").rstrip("/")
COMPRAS_BASE = os.getenv("COMPRAS_GOV_BASE_URL", "https://dadosabertos.compras.gov.br").rstrip("/")
TIMEOUT = float(os.getenv("PUBLIC_SOURCES_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("PUBLIC_SOURCES_MAX_RETRIES", "3"))
USER_AGENT = "CTC-Tech-PreDisputa/1.0 (+public-data-consultation)"


class SourceError(RuntimeError):
    """Upstream public API error."""


def _request(url: str, *, binary: bool = False) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(
            url, headers={"Accept": "*/*" if binary else "application/json",
                          "User-Agent": USER_AGENT}, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = exc.headers.get("Retry-After", "")
                time.sleep(float(wait) if wait.isdigit() else min(2 ** attempt, 8))
                last_error = exc
                continue
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise SourceError(f"HTTP {exc.code} em {url}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(2 ** attempt, 8))
    raise SourceError(f"Falha de conexão em {url}: {last_error}")


def _json(url: str) -> dict[str, Any] | list[Any]:
    raw, _ = _request(url)
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceError(f"Resposta não é JSON válido: {url}") from exc
    if not isinstance(value, (dict, list)):
        raise SourceError(f"Estrutura JSON inesperada: {url}")
    return value


def _url(base: str, path: str, params: dict[str, Any]) -> str:
    return f"{base}{path}?{urllib.parse.urlencode({k:v for k,v in params.items() if v is not None and v != ''})}"


def pncp_search_publications(data_inicial: str, data_final: str, *, modalidade: int,
                             uf: str | None = None, cnpj: str | None = None,
                             pagina: int = 1, tamanho_pagina: int = 50) -> dict[str, Any] | list[Any]:
    if not re.fullmatch(r"\d{8}", data_inicial) or not re.fullmatch(r"\d{8}", data_final):
        raise ValueError("Datas PNCP devem usar AAAAMMDD.")
    if pagina < 1 or not 1 <= tamanho_pagina <= 500:
        raise ValueError("pagina deve ser >=1 e tamanho_pagina entre 1 e 500.")
    params = {"dataInicial": data_inicial, "dataFinal": data_final,
              "codigoModalidadeContratacao": modalidade, "uf": uf, "cnpj": cnpj,
              "pagina": pagina, "tamanhoPagina": tamanho_pagina}
    return _json(_url(PNCP_BASE, "/v1/contratacoes/publicacao", params))


def pncp_open_proposals(data_final: str, *, modalidade: int | None = None,
                        uf: str | None = None, pagina: int = 1,
                        tamanho_pagina: int = 50) -> dict[str, Any] | list[Any]:
    if not re.fullmatch(r"\d{8}", data_final):
        raise ValueError("data_final deve usar AAAAMMDD.")
    params = {"dataFinal": data_final, "codigoModalidadeContratacao": modalidade,
              "uf": uf, "pagina": pagina, "tamanhoPagina": tamanho_pagina}
    return _json(_url(PNCP_BASE, "/v1/contratacoes/proposta", params))


def parse_pncp_control(control: str) -> tuple[str, int, int]:
    match = re.fullmatch(r"([A-Z0-9]{14})-1-(\d{6})/(\d{4})", control.strip(), re.I)
    if not match:
        raise ValueError("Controle PNCP inválido. Esperado CNPJ-1-SSSSSS/AAAA.")
    cnpj, seq, year = match.groups()
    return cnpj.upper(), int(year), int(seq)


def pncp_purchase_detail(control: str) -> dict[str, Any] | list[Any]:
    cnpj, year, seq = parse_pncp_control(control)
    return _json(f"{PNCP_BASE}/v1/orgaos/{cnpj}/compras/{year}/{seq}")


def pncp_purchase_documents(control: str) -> dict[str, Any] | list[Any]:
    cnpj, year, seq = parse_pncp_control(control)
    return _json(f"{PNCP_BASE}/v1/orgaos/{cnpj}/compras/{year}/{seq}/arquivos")


def pncp_download_document(control: str, sequencial_documento: int, output_dir: str) -> Path:
    cnpj, year, seq = parse_pncp_control(control)
    if sequencial_documento < 1:
        raise ValueError("sequencial_documento deve ser >= 1.")
    url = f"{PNCP_BASE}/v1/orgaos/{cnpj}/compras/{year}/{seq}/arquivos/{sequencial_documento}"
    raw, mime = _request(url, binary=True)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ext = ".pdf" if "pdf" in mime.lower() or raw.startswith(b"%PDF") else ".bin"
    target = out / f"PNCP_{cnpj}_{year}_{seq}_doc_{sequencial_documento}{ext}"
    target.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(
        f"{digest}  {target.name}\n", encoding="utf-8")
    return target


def compras_gov_search_publications(data_inicial: str, data_final: str, *,
                                    modalidade: int = 5, pagina: int = 1,
                                    tamanho_pagina: int = 100) -> dict[str, Any] | list[Any]:
    params = {"dataPublicacaoPncpInicial": data_inicial,
              "dataPublicacaoPncpFinal": data_final, "codigoModalidade": modalidade,
              "pagina": pagina, "tamanhoPagina": tamanho_pagina}
    return _json(_url(COMPRAS_BASE,
        "/modulo-contratacoes/1_consultarContratacoes_PNCP_14133", params))


def _records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    for key in ("data", "resultado", "items"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def _all_pages(fetch, *args, source: str, **filters: Any) -> dict[str, Any]:
    first = fetch(*args, pagina=1, **filters)
    records = _records(first)
    total = int(first.get("totalPaginas", 1)) if isinstance(first, dict) else 1
    pages = [first]
    for page in range(2, max(total, 1) + 1):
        result = fetch(*args, pagina=page, **filters)
        pages.append(result)
        records.extend(_records(result))
        time.sleep(0.5)
    return {"fonte": source, "coletado_em": datetime.now(timezone.utc).isoformat(),
            "total_paginas_informado": total, "paginas_recebidas": len(pages),
            "total_registros_recebidos": len(records), "registros": records,
            "respostas_por_pagina": pages}


def pncp_search_all_pages(data_inicial: str, data_final: str, **filters: Any) -> dict[str, Any]:
    return _all_pages(pncp_search_publications, data_inicial, data_final,
                      source="PNCP API Consulta", **filters)


def compras_gov_search_all_pages(data_inicial: str, data_final: str, **filters: Any) -> dict[str, Any]:
    return _all_pages(compras_gov_search_publications, data_inicial, data_final,
                      source="Compras.gov.br Dados Abertos", **filters)
