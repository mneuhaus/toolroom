"""Export the sorter master assembly as a glTF through Onshape's translation API.

  /opt/homebrew/opt/python@3.11/libexec/bin/python translate_gltf.py out.gltf [medium|fine]

Goes through the local Onshape Bridge (open -a 'Onshape Bridge' first). The
direct /gltf endpoint ignores every tolerance parameter and returns one fixed
coarse mesh, so this uses the async translation route, which honours them.
"medium" (2.8M unique triangles, ~4 min) is enough for renders; "fine" is 15M.
"""

import json
import sys
import time
import urllib.request

BRIDGE = "http://127.0.0.1:8317"
DOC = "9137894c36f07dfc4dea695d"
WORKSPACE = "dde194facf5a22be951251c3"
ASSEMBLY = "fd945a12cae469abc61edab3"
LEVELS = {
    "medium": {"angularTolerance": 0.06, "distanceTolerance": 0.0004, "maximumChordLength": 0.012},
    "fine": {"angularTolerance": 0.02, "distanceTolerance": 0.0001, "maximumChordLength": 0.004},
}


def req(path, body=None, binary=False):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BRIDGE + path, data=data, method="POST" if body is not None else "GET",
        headers={"Content-Type": "application/json", "Accept": "application/vnd.onshape.v1+json, */*"})
    with urllib.request.urlopen(r, timeout=900) as resp:
        raw = resp.read()
        return raw if binary else json.loads(raw)


out = sys.argv[1]
level = LEVELS[sys.argv[2] if len(sys.argv) > 2 else "medium"]
body = {"formatName": "GLTF", "storeInDocument": False, "includeExportIds": False,
        "flattenAssemblies": False, "yAxisUp": False, "triggerAutoDownload": False,
        "grouping": True, **level}
job = req(f"/api/assemblies/d/{DOC}/w/{WORKSPACE}/e/{ASSEMBLY}/translations", body)
print("translation", job["id"], job.get("requestState"), flush=True)
while True:
    time.sleep(10)
    st = req(f"/api/translations/{job['id']}")
    print("state", st.get("requestState"), st.get("failureReason") or "", flush=True)
    if st.get("requestState") in ("DONE", "FAILED"):
        break
if st.get("requestState") != "DONE":
    sys.exit(1)
(data_id,) = st["resultExternalDataIds"]
raw = req(f"/api/documents/d/{DOC}/externaldata/{data_id}", binary=True)
open(out, "wb").write(raw)
print("saved", out, len(raw), "bytes")
