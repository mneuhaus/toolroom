# Classifying small-topology findings with declared regions

`splitter()` can classify raw small-edge, tiny-face, and unmerged-face findings with
the same named regions used by `kerbe()`. Pass the part's `TeilForm` as `erklaert` and
the `Machine` when a region uses a named local frame:

```python
form = load_form(project.spec / "form.yaml")
result = splitter(holder, erklaert=form.teil(holder.key), machine=machine)
```

Every raw finding remains in its original result list. Each finding also has
`erklaert`, `grund`, and `erklaert_bereich`; the result reports `erklaert` and
`unerklaert` counts. A declared region is a review explanation, not proof that the
geometry is mechanically necessary. Findings outside all declared regions remain
unexplained and keep the result from passing.

Classification tests the finding's recorded representative point: the edge midpoint
for a short or unmerged edge, and the face center for a tiny face. It does not claim
that the complete edge or face lies inside the region, and it is not a necessity or
safety proof.

If BRep or frame analysis fails, `splitter()` returns the shared technical-failure
state while retaining raw candidates already found. A missing BRep remains
`unentschieden`; an empty or invalid non-None BRep is a technical failure. None of
these cases is an empty success.
