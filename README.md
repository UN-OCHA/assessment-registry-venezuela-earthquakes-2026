# Assessment Registry Dashboard - Kobo + GitHub Pages

Dashboard HTML estático para GitHub Pages que actualiza sus datos desde Kobo mediante GitHub Actions.

## Importante: no pegues el token en el HTML

El dashboard **no** llama a Kobo directamente desde el navegador. El token se guarda como secreto de GitHub y solo lo usa GitHub Actions para generar `data/registry.json` y `data/registry.js`.

## Archivos principales

- `index.html` - dashboard.
- `css/style.css` - estilos OCHA.
- `js/dashboard.js` - lógica de filtros, tabla y gráficos Canvas.
- `data/registry.js` - datos que lee el dashboard.
- `data/registry.json` - datos en formato JSON.
- `scripts/fetch_kobo.py` - descarga datos desde Kobo y transforma el JSON.
- `.github/workflows/update-kobo-data.yml` - workflow programado para actualizar datos.

## Configuración en GitHub

1. Crea o usa un repositorio en la organización `UN-OCHA`.
2. Sube todos los archivos de este paquete a la raíz del repositorio.
3. En el repositorio, ve a **Settings > Secrets and variables > Actions > New repository secret**.
4. Crea el secreto:
   - Name: `KOBO_API_TOKEN`
   - Secret: tu token de Kobo
5. Ve a **Actions > Update Kobo registry data > Run workflow** para ejecutar la primera actualización manual.
6. Ve a **Settings > Pages**.
7. En **Build and deployment**, selecciona:
   - Source: `Deploy from a branch`
   - Branch: `main`
   - Folder: `/ (root)`
8. Guarda la configuración.

Cuando GitHub Pages termine de publicar, el dashboard estará disponible en una URL similar a:

`https://un-ocha.github.io/NOMBRE-DEL-REPOSITORIO/`

## Ajustar periodicidad

La actualización está configurada en `.github/workflows/update-kobo-data.yml` para correr cada 30 minutos:

```yaml
schedule:
  - cron: "*/30 * * * *"
```

Puedes cambiar esa frecuencia si lo deseas.

## Endpoint Kobo usado

`https://kobo.unocha.org/api/v2/assets/aTX9v7VgZdAbYfKozHV4dN/data/?format=json`

## Notas

- El dashboard no usa librerías externas ni CDN.
- Los gráficos se generan con Canvas API.
- La fecha “Último registro publicado” usa `_submission_time` y se muestra sin hora.
