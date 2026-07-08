#!/usr/bin/env python3
"""Fetch Kobo records and build data/registry.json + data/registry.js.

Required env var:
  KOBO_API_TOKEN - Kobo API token stored as a GitHub Actions secret.

Optional env vars:
  KOBO_API_URL - Kobo API endpoint. Defaults to the Venezuela 2026 assessment registry endpoint.
"""
import json, os, re, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

KOBO_API_URL = os.getenv("KOBO_API_URL", "https://kobo.unocha.org/api/v2/assets/aTX9v7VgZdAbYfKozHV4dN/data/?format=json")
TOKEN = os.getenv("KOBO_API_TOKEN")

if not TOKEN:
    print("ERROR: KOBO_API_TOKEN is not set. Add it as a GitHub Actions secret.", file=sys.stderr)
    sys.exit(1)

def clean(value):
    if value is None:
        return ""
    s = str(value).replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", s)

def parse_date(value):
    s = clean(value)
    if not s:
        return ""
    # Handles YYYY-MM-DD and datetime strings; keeps date only.
    return s[:10]

def truthy(value):
    return str(value).strip().lower() in {"1", "1.0", "true", "sí", "si", "yes"}

def get_records_from_response(payload):
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return payload["results"]
    if isinstance(payload, dict) and isinstance(payload.get("records"), list):
        return payload["records"]
    if isinstance(payload, list):
        return payload
    raise ValueError("Unsupported Kobo response structure")

def fetch_all(url):
    all_rows = []
    while url:
        req = Request(url, headers={"Authorization": f"Token {TOKEN}", "Accept": "application/json"})
        try:
            with urlopen(req, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            print(f"HTTP error from Kobo: {e.code} {e.reason}", file=sys.stderr)
            raise
        except URLError as e:
            print(f"Network error fetching Kobo: {e}", file=sys.stderr)
            raise
        rows = get_records_from_response(payload)
        all_rows.extend(rows)
        url = payload.get("next") if isinstance(payload, dict) else None
    return all_rows

def key_starts(row, prefix):
    return [k for k in row.keys() if k.startswith(prefix)]

def transform(rows):
    records = []
    submission_dates = []
    sector_prefix = "Clúster / Sector/"
    admin1_prefix = "Cobertura Admin 1 (Estado)/"
    admin2_prefix = "Cobertura Admin 2 (Municipio)/"
    admin3_prefix = "Cobertura Admin 3 (Parroquia) Opcional/"

    for i, row in enumerate(rows):
        sectors = [k.replace(sector_prefix, "").strip() for k in key_starts(row, sector_prefix) if truthy(row.get(k))]
        admin1 = [k.replace(admin1_prefix, "").strip() for k in key_starts(row, admin1_prefix) if truthy(row.get(k))]
        admin2 = []
        for k in key_starts(row, admin2_prefix):
            if truthy(row.get(k)):
                val = k.replace(admin2_prefix, "").strip()
                parts = [p.strip() for p in val.split(" - ", 1)]
                admin2.append({"estado": parts[0] if len(parts) > 1 else "", "municipio": parts[-1]})
        admin3 = [k.replace(admin3_prefix, "").strip() for k in key_starts(row, admin3_prefix) if truthy(row.get(k))]
        submission_date = parse_date(row.get("_submission_time"))
        if submission_date:
            submission_dates.append(submission_date)

        records.append({
            "id": clean(row.get("_uuid")) or clean(row.get("_id")) or f"row-{i+1}",
            "indice": clean(row.get("_index")) or str(i+1),
            "titulo": clean(row.get("Título de la evaluación")),
            "organizacion": clean(row.get("Organización")),
            "agencia_lider": clean(row.get("Agencia líder")) or clean(row.get("Organización")),
            "organizaciones_participantes": clean(row.get("Organizaciones participantes")),
            "estado_evaluacion": clean(row.get("Estado de la evaluación")),
            "frecuencia": clean(row.get("Frecuencia de la evaluación")),
            "nivel_cobertura": clean(row.get("Nivel geográfico de cobertura")),
            "fecha_evaluacion": parse_date(row.get("Fecha de la evaluación")),
            "fecha_fin_estimada": parse_date(row.get("Fecha de finalización estimada") or row.get("Fecha de finalización / prevista")),
            "fecha_envio": submission_date,
            "sectores": sectors,
            "admin1": admin1,
            "admin2": admin2,
            "admin3": admin3,
            "detalle_cobertura": clean(row.get("Detalles adicionales de cobertura")),
            "tiene_datos": bool(clean(row.get("Datos de la evaluación")) or clean(row.get("Datos de la evaluación_URL"))),
            "url_datos": clean(row.get("Datos de la evaluación_URL")),
            "tiene_reporte": bool(clean(row.get("Reporte de la evaluación")) or clean(row.get("Reporte de la evaluación_URL"))),
            "url_reporte": clean(row.get("Reporte de la evaluación_URL")),
            "nombre_reporte": clean(row.get("Reporte de la evaluación")),
            "metodologia": clean(row.get("Metodología de la evaluación")) or clean(row.get("Si seleccionó Otro, especifique la metodología")),
            "notas": clean(row.get("Notas adicionales")),
        })

    return {
        "metadata": {
            "titulo": "Registro de Evaluaciones - Terremotos en Venezuela 2026",
            "subtitulo": "Assessment Registry | Respuesta Humanitaria",
            "fuente": "Registro de evaluaciones en Kobo.",
            "endpoint": KOBO_API_URL,
            "ultimo_registro_publicado": max(submission_dates) if submission_dates else "",
            "generado": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "registros": len(records),
        },
        "records": records,
    }

def main():
    rows = fetch_all(KOBO_API_URL)
    payload = transform(rows)
    os.makedirs("data", exist_ok=True)
    with open("data/registry.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open("data/registry.js", "w", encoding="utf-8") as f:
        f.write("window.REGISTRY_PAYLOAD = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"Wrote {len(payload['records'])} records. Latest published: {payload['metadata']['ultimo_registro_publicado']}")

if __name__ == "__main__":
    main()
