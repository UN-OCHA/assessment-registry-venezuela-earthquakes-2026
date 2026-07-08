#!/usr/bin/env python3
"""Fetch Kobo records and build data/registry.json + data/registry.js.

This version maps the internal Kobo/XLSForm field names returned by the API, e.g.:
- ASSESSMENT_ID/assessment_title
- REPORTER/enum_org
- ASSESSMENT_ID/cluster_sector
- GEO_COVERAGE/admin1_coverage

Required env var:
  KOBO_API_TOKEN - Kobo API token stored as a GitHub Actions secret.
"""
import json, os, re, sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

KOBO_API_URL = os.getenv("KOBO_API_URL", "https://kobo.unocha.org/api/v2/assets/aTX9v7VgZdAbYfKozHV4dN/data/?format=json")
TOKEN = os.getenv("KOBO_API_TOKEN")

SECTOR_MAP = {
    "inter_cluster": "Inter-Clúster",
    "shelter_nfi": "Refugio y Artículos No Alimentarios (SNF)",
    "erl": "Recuperación Temprana (ERL)",
    "food_security": "Seguridad Alimentaria",
    "health": "Salud",
    "nutrition": "Nutrición",
    "protection": "Protección",
    "wash": "Agua, Saneamiento e Higiene (WASH)",
    "education": "Educación",
    "cccm": "Coordinación y Gestión de Campamentos (CCCM)",
    "other": "Otro",
}
STATUS_MAP = {"completed": "Completado", "ongoing": "En curso", "planned": "Planificado"}
FREQUENCY_MAP = {"single": "Evaluación única", "daily": "Diaria", "weekly": "Semanal", "monthly": "Mensual", "other": "Otra (especificar)"}
GEO_LEVEL_MAP = {"admin1": "Estado", "admin2": "Municipio", "admin3": "Parroquia", "camp": "Campamento", "whole_eq_area": "Toda el área afectada"}
ADMIN1_MAP = {
    "VE01": "Distrito Capital",
    "VE05": "Aragua",
    "VE08": "Carabobo",
    "VE11": "Falcón",
    "VE15": "Miranda",
    "VE22": "Yaracuy",
    "VE24": "La Guaira",
}

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
    return s[:10]

def split_tokens(value):
    return [x.strip() for x in clean(value).split() if x.strip()]

def map_list(value, mapping):
    return [mapping.get(token, token) for token in split_tokens(value)]

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

def attachment_for(row, question_xpath):
    for att in row.get("_attachments", []) or []:
        if att.get("question_xpath") == question_xpath and not att.get("is_deleted"):
            return att
    return None

def transform(rows):
    records = []
    submission_dates = []
    for i, row in enumerate(rows):
        sectors = map_list(row.get("ASSESSMENT_ID/cluster_sector"), SECTOR_MAP)
        admin1 = map_list(row.get("GEO_COVERAGE/admin1_coverage"), ADMIN1_MAP)
        admin2_codes = split_tokens(row.get("GEO_COVERAGE/admin2_detail"))
        admin2 = [{"estado": ADMIN1_MAP.get(code[:4], ""), "municipio": code} for code in admin2_codes]
        admin3_codes = split_tokens(row.get("GEO_COVERAGE/admin3_detail"))
        admin3 = admin3_codes
        submission_date = parse_date(row.get("_submission_time"))
        if submission_date:
            submission_dates.append(submission_date)

        report_attachment = attachment_for(row, "REPORT/report")
        data_attachment = attachment_for(row, "ASSESSMENT_DATA/data") or attachment_for(row, "REPORT/data")
        report_name = clean(row.get("REPORT/report")) or clean(report_attachment.get("media_file_basename") if report_attachment else "")
        data_name = clean(row.get("ASSESSMENT_DATA/data")) or clean(data_attachment.get("media_file_basename") if data_attachment else "")

        records.append({
            "id": clean(row.get("_uuid")) or clean(row.get("_id")) or f"row-{i+1}",
            "indice": clean(row.get("_index")) or str(i+1),
            "titulo": clean(row.get("ASSESSMENT_ID/assessment_title")),
            "organizacion": clean(row.get("REPORTER/enum_org")),
            "agencia_lider": clean(row.get("DATES_ORGS/lead_agency")) or clean(row.get("REPORTER/enum_org")),
            "organizaciones_participantes": clean(row.get("DATES_ORGS/participating_orgs")),
            "estado_evaluacion": STATUS_MAP.get(clean(row.get("ASSESSMENT_ID/assessment_status")), clean(row.get("ASSESSMENT_ID/assessment_status"))),
            "frecuencia": FREQUENCY_MAP.get(clean(row.get("ASSESSMENT_ID/assessment_frequency")), clean(row.get("ASSESSMENT_ID/assessment_frequency"))),
            "nivel_cobertura": GEO_LEVEL_MAP.get(clean(row.get("GEO_COVERAGE/geo_level")), clean(row.get("GEO_COVERAGE/geo_level"))),
            "fecha_evaluacion": parse_date(row.get("DATES_ORGS/start_date")),
            "fecha_fin_estimada": parse_date(row.get("DATES_ORGS/end_date")),
            "fecha_envio": submission_date,
            "sectores": sectors,
            "admin1": admin1,
            "admin2": admin2,
            "admin3": admin3,
            "detalle_cobertura": clean(row.get("GEO_COVERAGE/geo_details")),
            "tiene_datos": bool(data_name or (data_attachment and data_attachment.get("download_url"))),
            "url_datos": clean(data_attachment.get("download_url") if data_attachment else ""),
            "tiene_reporte": bool(report_name or (report_attachment and report_attachment.get("download_url"))),
            "url_reporte": clean(report_attachment.get("download_url") if report_attachment else ""),
            "nombre_reporte": report_name,
            "metodologia": clean(row.get("REPORT/methodology")) or clean(row.get("REPORT/other_methodology")),
            "notas": clean(row.get("REPORT/additional_notes")),
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
    # Verify that mapping produced useful data.
    non_empty_titles = sum(1 for r in payload["records"] if r.get("titulo"))
    print(f"Wrote {len(payload['records'])} records. Non-empty titles: {non_empty_titles}. Latest published: {payload['metadata']['ultimo_registro_publicado']}")
    if payload["records"] and non_empty_titles == 0:
        raise SystemExit("ERROR: Kobo records were fetched, but title mapping produced zero non-empty titles.")

if __name__ == "__main__":
    main()
