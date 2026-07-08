# Assessment Registry Dashboard - Kobo + GitHub Pages v4

Esta versión corrige el mapeo de campos internos devueltos por la API de Kobo.

## Cambio principal de v4

La API devuelve nombres internos del XLSForm, por ejemplo:

- `ASSESSMENT_ID/assessment_title`
- `REPORTER/enum_org`
- `ASSESSMENT_ID/cluster_sector`
- `ASSESSMENT_ID/assessment_status`
- `GEO_COVERAGE/admin1_coverage`
- `DATES_ORGS/start_date`
- `REPORT/report`

La versión anterior buscaba etiquetas del CSV exportado, por eso los registros aparecían vacíos.

## Cómo actualizar el repositorio

1. Sustituye en GitHub estos archivos por los de este paquete:
   - `scripts/fetch_kobo.py`
   - `.github/workflows/update-kobo-data.yml`
   - `data/registry.js`
   - `data/registry.json`
   - `index.html`, `css/style.css`, `js/dashboard.js` si quieres mantener todo sincronizado.
2. Haz commit en `main`.
3. Ve a **Actions > Update Kobo registry data > Run workflow**.
4. Abre `data/registry.js` publicado en GitHub Pages y verifica que `titulo`, `organizacion`, `estado_evaluacion`, `sectores` y `admin1` ya estén llenos.

## GitHub secret requerido

`KOBO_API_TOKEN`

## Endpoint

`https://kobo.unocha.org/api/v2/assets/aTX9v7VgZdAbYfKozHV4dN/data/?format=json`
