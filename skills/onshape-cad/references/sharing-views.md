# Deliver CAD views the user can actually open

If inline images or local attachment links do not render for the user, change
the delivery mechanism instead of repeatedly sending another equivalent path.
Use native CAD views for evidence, with captions naming the view, revision and
changed parts. Generated illustrations may explain a mechanism but are not proof
of the actual CAD geometry.

A standalone HTML gallery with embedded PNGs and ordinary anchor links worked
for Sparky. Static CSS can enlarge an image without JavaScript. Inspect the images
locally before delivery and provide the actual accessible URL. Preserve the native
CAD link and a short assembly sequence alongside the images.

## Postplan observations (September 2026)

Use publishing only within the user's requested/previously authorized sharing
scope. Do not upload private CAD to an external service solely because an inline
image failed. A local self-contained artifact can still be prepared for review.

The session used `POST https://postplan.dev/api/uploads` with a JSON object:

```json
{"html":"...","filename":"gallery.html","description":"...","draftId":"only when updating that known draft"}
```

The response contained `publicUrl` and `draftId`. Anonymous uploads rejected
inline JavaScript. A static gallery under the observed 512 KiB HTML limit worked;
measure UTF-8 bytes including base64 assets. Treat these as observed service
behavior and recheck responses if it changes. This recipe is not a reason to
remove required interaction from a different task.

Store each revision's publication state separately in `var/state/`; do not let a
copied publisher script reuse the preceding revision's draft-ID file. After an
upload, fetch the returned public URL and check that it serves the intended
artifact (the self-contained Sparky HTML was compared byte-for-byte). Do not
claim a URL works based only on the upload response.

Reference implementation: `~/Workspace/cad/spar-key-z-axis/scripts/make-r7-gallery.mjs`.
Local generation needs no network. `--publish` updates the revision's known draft.
