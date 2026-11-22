"""Write the first N commands of a SolidCraft script to another file (for bisecting a failing or heavy step)."""
import json
import sys

src, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cmds = json.load(open(src))["commands"]
json.dump({"commands": cmds[:n]}, open(out, "w"), indent=1)
print(f"{n} of {len(cmds)}: last = {cmds[n - 1]['command']} {cmds[n - 1]['params'].get('name', '')}")
