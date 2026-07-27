# Browser asset policy

The production contract is the self-hosted file:

```text
examples/golden/static/vendor/htmx-2.0.10.min.js
```

It is the official `htmx.org@2.0.10` minified distribution. The checked-in
file has:

```text
SHA-256  71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de
SHA-384  H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V
```

The SHA-384 value matches the integrity value published in the official htmx
installation documentation. The upstream Zero-Clause BSD license is stored
next to the asset as `htmx-LICENSE`.

## Update process

1. Read the target htmx release notes and migration guidance.
2. Download the exact versioned `dist/htmx.min.js` from the official
   `htmx.org` npm package.
3. Compare SHA-384 against the value published by htmx.
4. Rename the file with its exact version and update the script path.
5. Update both hashes in this document and the integrity regression test.
6. Run direct tests and the full Chromium smoke path.
7. Review the browser network log and ensure no CDN or other third-party
   request was introduced.

Do not update this asset through an unpinned URL or at application startup.
