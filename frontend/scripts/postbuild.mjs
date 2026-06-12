// SWA's deployment validator requires an index.html at the artifact root, but
// the app is built into dist/ttb/ (to live under the /ttb base path). Write a
// tiny root index that forwards to /ttb/ — the staticwebapp.config.json route
// redirect handles normal traffic; this satisfies the validator and acts as a
// fallback.
import { writeFileSync } from 'node:fs'

writeFileSync(
  new URL('../dist/index.html', import.meta.url),
  `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="refresh" content="0; url=/ttb/" />
    <title>TTB Label Verification</title>
  </head>
  <body>
    <p><a href="/ttb/">Continue to TTB Label Verification</a></p>
  </body>
</html>
`,
)
console.log('postbuild: wrote dist/index.html root redirect')
