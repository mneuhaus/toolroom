"""Token-Verbrauch der Claude-Code-Sessions der letzten N Stunden aus den Transkripten (~/.claude/projects).

    uv run python usage_report.py [hours=48] [top=15]

Gewichtung nach Preisverhaeltnis: Input 1, Cache-Write 1.25, Cache-Read 0.1, Output 5.
"""
import json, glob, os, sys, collections, datetime
H = int(sys.argv[1]) if len(sys.argv) > 1 else 48; TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 15
root = os.path.expanduser('~/.claude/projects'); cut = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=H); cut_s = cut.isoformat()
def cost(t): return t['input_tokens'] + t['cache_creation_input_tokens'] * 1.25 + t['cache_read_input_tokens'] * 0.1 + t['output_tokens'] * 5
rows = []; total = collections.Counter(); days = collections.defaultdict(collections.Counter); models = collections.Counter()
for f in glob.glob(f'{root}/*/*.jsonl') + glob.glob(f'{root}/*/*/subagents/*.jsonl'):
    if os.path.getmtime(f) < cut.timestamp(): continue
    proj = f[len(root) + 1:].split('/')[0]; sid = os.path.basename(f)[:8] + (' (sub)' if 'subagents' in f else '')
    tot = collections.Counter(); ctxs = []; first = last = None
    with open(f) as fh:
        for line in fh:
            try: d = json.loads(line)
            except Exception: continue
            if d.get('type') != 'assistant': continue
            ts = d.get('timestamp') or ''
            if ts < cut_s: continue
            u = (d.get('message') or {}).get('usage') or {}
            if not u: continue
            first = first or ts; last = ts
            for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'): tot[k] += u.get(k, 0) or 0
            ctxs.append(sum((u.get(k, 0) or 0) for k in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')))
            models[d['message'].get('model') or '?'] += 1
            for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens'): days[ts[:10]][k] += u.get(k, 0) or 0
    if ctxs: rows.append((proj, sid, len(ctxs), tot, first, last, max(ctxs), sum(ctxs) / len(ctxs)))
    for k, v in tot.items(): total[k] += v
rows.sort(key=lambda r: -cost(r[3]))
print(f"Letzte {H} h  |  {'Projekt':38} {'Session':14} {'Msgs':>5} {'Ø Ktx':>6} {'max':>5} {'CacheRead':>10} {'CacheW':>7} {'Out':>6} {'Gewicht':>8}  Zeitraum")
for proj, sid, n, t, first, last, mx, avg in rows[:TOP]:
    print(f"{'':13}|  {proj[-38:]:38} {sid:14} {n:5} {avg/1000:5.0f}k {mx/1000:4.0f}k {t['cache_read_input_tokens']/1e6:9.1f}M {t['cache_creation_input_tokens']/1e6:6.1f}M {t['output_tokens']/1e6:5.2f}M {cost(t)/1e6:7.1f}M  {first[5:16]}..{last[5:16]}")
print('\nSumme:', {k: f'{v/1e6:.1f}M' for k, v in total.items()}, 'gewichtet', f'{cost(total)/1e6:.1f}M')
print('Pro Tag (CacheRead / CacheWrite / Output):', ', '.join(f"{d}: {v['cache_read_input_tokens']/1e6:.0f}M / {v['cache_creation_input_tokens']/1e6:.0f}M / {v['output_tokens']/1e6:.1f}M" for d, v in sorted(days.items())))
print('Modelle:', dict(models))
