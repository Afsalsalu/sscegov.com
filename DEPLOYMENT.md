# SSCEGOV deployment checklist

The main application is Django under `django/`, served by Gunicorn as
`ssc.wsgi:application`. Production deploys must use the repository checkout;
the old `projectname.wsgi` Gunicorn target is invalid for this project.

## One-time server setup

Install the service unit and enable it:

```bash
cd "$HOME/sscegov.com"
sudo install -m 0644 deploy/sscegov-gunicorn.service /etc/systemd/system/sscegov-gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable sscegov-gunicorn.service
```

The unit expects the application checkout at `$HOME/sscegov.com`, the virtual
environment at `django/venv`, and environment values in `django/.env`.

## Every deployment

Run from the server checkout:

```bash
cd "$HOME/sscegov.com"
DEPLOY_BRANCH=main APP_SERVICE=sscegov-gunicorn.service bash scripts/deploy_django.sh
```

The script pulls fast-forward-only, then runs:

- `python manage.py check`
- `python manage.py migrate --noinput` and `migrate --check`
- `python manage.py collectstatic --noinput`
- source/template/static-file presence checks
- verification of `USE_I18N`, the 23-language catalog, and the required Kerala state row
- Gunicorn restart and active-service check

The selector is composed from `web/language.py`,
`templates/web/includes/language_switcher.html`, and
`static/web/css/language-switcher.css`. No extra language package is required.
`LocaleMiddleware` and `UserLanguageMiddleware` must remain enabled in
`ssc/settings.py`, with `LANGUAGES = SUPPORTED_LANGUAGES`, `USE_I18N = True`,
and `LOCALE_PATHS` configured.

## Post-deploy verification

1. Confirm the deployed commit: `git -C "$HOME/sscegov.com" rev-parse HEAD`.
2. Confirm migrations: `cd django && python manage.py showmigrations web`.
3. Confirm source/static parity: compare
   `static/web/css/language-switcher.css` and
   `assets/web/css/language-switcher.css`.
4. Check runtime logs: `sudo journalctl -u sscegov-gunicorn.service -n 200 --no-pager`.
5. Open a logged-in Head Office or franchise dashboard in a browser. Check the
   language selector is visible, its POST returns to the same safe page, the
   selected language persists, and the browser console/network panel has no
   template, CSS, JavaScript, or 404 errors.

If the selector is absent after a successful deploy, first verify that the
served HTML contains `data-language-switcher` and that the CSS request for
`web/css/language-switcher.css` returns 200; this distinguishes stale templates
from stale static files.
