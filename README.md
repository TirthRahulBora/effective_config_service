# Effective Configuration FastAPI service

Implements `GET /effective-config?set=key=value&set=...`.

Precedence: hardcoded defaults -> `config.<APP_ENV>.yaml` (defaults to `config.development.yaml`) -> `.env` -> `APP_*` OS environment variables -> query `set` overrides.

`NUM_WORKERS` maps to `workers`; `api_key` is always masked in output. CORS is enabled for browser requests.

## Deploy on Render
1. Create a public GitHub repository and upload all files from this folder, including the hidden `.env` file.
2. In Render, choose **New + -> Blueprint**, connect that repository, and apply the `render.yaml` blueprint.
3. Wait for the service to become Live.
4. Your URL is `https://YOUR-RENDER-SERVICE.onrender.com/effective-config`.
5. Test overrides, e.g. `https://YOUR-RENDER-SERVICE.onrender.com/effective-config?set=port=9000&set=debug=true`.

The example `render.yaml` supplies the assigned OS environment values. The `.env` file is included for the requested lower-precedence layer; keep in mind that real secrets should not be committed to public repositories.
