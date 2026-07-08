# consumi.barulli.it

Static site, published via GitHub Pages, published at `consumi.barulli.it`.

- `index.html` — landing page linking to individual reports
- `gas/index.html` — gas consumption & cost report (Chart.js + Grid.js, data embedded inline, no build step)
- `CNAME` — tells GitHub Pages which custom domain to serve

To add a new report later (electricity, water, ...): create a new folder (e.g. `elettricita/index.html`) and add a card for it in the root `index.html`.

## Deploy (first time)

1. Create a new **public** repo on GitHub, e.g. `consumi` (public is required for GitHub Pages on free plans; private works only on Pro/Team/Enterprise).
2. From this folder:

   ```bash
   git init
   git add .
   git commit -m "Initial report: gas consumption"
   git branch -M main
   git remote add origin git@github.com:<your-username>/consumi.git
   git push -u origin main
   ```

3. On GitHub: repo → **Settings → Pages** → Source: "Deploy from a branch" → Branch: `main` / `/(root)`. Save.
4. Still in **Settings → Pages**, under "Custom domain" enter `consumi.barulli.it` and save (GitHub will re-check the `CNAME` file already in the repo — this step also triggers the DNS check banner).
5. At Hover (DNS for `barulli.it`), add a **CNAME record**:
   - Host/Name: `consumi`
   - Type: `CNAME`
   - Value/Target: `<your-username>.github.io`
   - TTL: default
6. Wait for DNS to propagate (usually minutes, sometimes up to a few hours), then back in GitHub Pages settings tick **"Enforce HTTPS"** once it becomes available (it's greyed out until GitHub verifies the domain).

## Update later

Edit the relevant `index.html`, then:

```bash
git add .
git commit -m "Update gas report"
git push
```

GitHub Pages redeploys automatically within a minute or two.
