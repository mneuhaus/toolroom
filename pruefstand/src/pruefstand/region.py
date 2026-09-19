"""Region: Quader, Zylinder, Punktwolke oder Ebenengitter in einem Frame."""
from __future__ import annotations

import numpy as np

from .frame import Frame


class Region:
    """Erzeugen über Region.box / Region.cylinder / Region.points / Region.plane_grid."""

    __slots__ = ('kind', 'frame', 'lo', 'hi', '_pts_local', 'meta',
                 'origin', 'axis', 'radius', 'length')

    def __init__(self, kind, frame, lo=None, hi=None, pts_local=None, meta=None,
                 origin=None, axis=None, radius=None, length=None):
        self.kind = kind
        self.frame = frame
        self.lo = None if lo is None else np.asarray(lo, dtype=float).reshape(3)
        self.hi = None if hi is None else np.asarray(hi, dtype=float).reshape(3)
        self._pts_local = None if pts_local is None else np.asarray(pts_local, dtype=float).reshape(-1, 3)
        self.meta = meta or {}
        self.origin = None if origin is None else np.asarray(origin, dtype=float).reshape(3)
        self.axis = None if axis is None else np.asarray(axis, dtype=float).reshape(3)
        self.radius = None if radius is None else float(radius)
        self.length = None if length is None else float(length)

    # -- Konstruktoren ---------------------------------------------------
    @classmethod
    def box(cls, frame: Frame, lo, hi) -> "Region":
        lo = np.asarray(lo, dtype=float)
        hi = np.asarray(hi, dtype=float)
        return cls('box', frame, lo=np.minimum(lo, hi), hi=np.maximum(lo, hi))

    @classmethod
    def cylinder(cls, frame: Frame, origin, axis, radius, length, inner_radius=0.0) -> "Region":
        """Zylindrisches Messfenster: Achse durch `origin` in Richtung `axis`, Länge ab `origin`.

        Ein Quader ist das falsche Fenster für alles, was um eine Achse gebaut ist --
        Schraubenkreis, Lagersitz, Hornsitz. An der R6d-Schale hat ein 30x30-Quader um
        den Schwenkpunkt Stirnwandmaterial der Altschale mitgemessen und 3,94 mm
        Abweichung gemeldet, wo die Schnittstelle in Wahrheit deckungsgleich ist.
        Negative `length` dreht die Richtung (das Fenster liegt dann vor `origin`).
        `inner_radius` macht daraus einen Ring -- gebraucht, sobald in der Mitte etwas
        steht, das mit der Schnittstelle nichts zu tun hat (Zentrierzapfen, Lagerbolzen):
        der Lochkreis ist dann messbar, ohne dass die Mitte das Ergebnis bestimmt.
        """
        axis = np.asarray(axis, dtype=float).reshape(3)
        n = float(np.linalg.norm(axis))
        if n < 1e-12:
            raise ValueError('Region.cylinder: Achse hat Länge 0')
        axis = axis / n
        length = float(length)
        origin = np.asarray(origin, dtype=float).reshape(3)
        if length < 0:
            origin = origin + axis * length
            length = -length
        if length <= 0 or float(radius) <= 0:
            raise ValueError('Region.cylinder: Radius und Länge müssen positiv sein')
        if not 0.0 <= float(inner_radius) < float(radius):
            raise ValueError('Region.cylinder: inner_radius muss zwischen 0 und radius liegen')
        return cls('cylinder', frame, origin=origin, axis=axis, radius=float(radius), length=length,
                   meta={'inner_radius': float(inner_radius)})

    def _cyl_coords(self, loc: np.ndarray):
        """(Achsenkoordinate, Abstand zur Achse) für lokale Punkte."""
        d = np.atleast_2d(loc) - self.origin
        t = d @ self.axis
        r = np.linalg.norm(d - np.outer(t, self.axis), axis=1)
        return t, r

    @classmethod
    def points(cls, frame: Frame, pts) -> "Region":
        return cls('points', frame, pts_local=pts)

    @classmethod
    def plane_grid(cls, frame: Frame, plane='xy', u=(0, 1, 1), v=(0, 1, 1), w=0.0) -> "Region":
        plane = plane.lower()
        uu = np.arange(u[0], u[1] + 1e-9, u[2])
        vv = np.arange(v[0], v[1] + 1e-9, v[2])
        gu, gv = np.meshgrid(uu, vv, indexing='ij')
        gu = gu.ravel()
        gv = gv.ravel()
        ww = np.full_like(gu, float(w))
        axes = {'xy': (gu, gv, ww), 'yz': (ww, gu, gv), 'xz': (gu, ww, gv),
                'yx': (gv, gu, ww), 'zy': (ww, gv, gu), 'zx': (gv, ww, gu)}
        if plane not in axes:
            raise ValueError(f'unbekannte Ebene {plane!r}')
        pts = np.column_stack(axes[plane])
        return cls('points', frame, pts_local=pts, meta={'plane': plane})

    # -- Nutzung ---------------------------------------------------------
    def solid(self):
        """build123d Solid der Region in Weltkoordinaten (Quader oder Zylinder)."""
        from build123d import Box, Cylinder, Location, Plane
        if self.kind == 'box':
            size = self.hi - self.lo
            centre = (self.hi + self.lo) / 2.0
            b = Box(*[float(x) for x in size]).locate(
                Location((float(centre[0]), float(centre[1]), float(centre[2]))))
        elif self.kind == 'cylinder':
            centre = self.origin + self.axis * (self.length / 2.0)
            lage = Plane(origin=tuple(float(x) for x in centre),
                         z_dir=tuple(float(x) for x in self.axis))
            b = lage * Cylinder(self.radius, self.length)
            innen = self.meta.get('inner_radius', 0.0)
            if innen > 0:
                b = b - lage * Cylinder(innen, self.length)
        else:
            raise TypeError('solid() gibt es nur für Region.box / Region.cylinder')
        # Starre Lage über eine Ebene, nicht `transform_geometry`: das ersetzt exakte
        # Flächen durch Näherungen -- ein Ø12-Zylinder verlor dabei gemessen 0,86 %
        # Volumen. Ein Frame ist Drehung plus Verschiebung, also reicht die Lage.
        m = self.frame.matrix()
        welt = Plane(origin=tuple(float(x) for x in m[:3, 3]),
                     x_dir=tuple(float(x) for x in m[:3, 0]),
                     z_dir=tuple(float(x) for x in m[:3, 2]))
        return welt * b

    def contains(self, pts_world) -> np.ndarray:
        p = np.atleast_2d(np.asarray(pts_world, dtype=float))
        loc = np.atleast_2d(self.frame.to_local(p))
        if self.kind == 'box':
            return np.all((loc >= self.lo) & (loc <= self.hi), axis=1)
        if self.kind == 'cylinder':
            t, r = self._cyl_coords(loc)
            return ((t >= 0) & (t <= self.length) & (r <= self.radius)
                    & (r >= self.meta.get('inner_radius', 0.0)))
        raise TypeError('contains() gibt es nur für Region.box / Region.cylinder')

    def sample_points(self) -> np.ndarray:
        if self._pts_local is None:
            raise TypeError('sample_points() gibt es nur für Region.points / plane_grid')
        return np.atleast_2d(self.frame.to_world(self._pts_local))

    def points_local(self) -> np.ndarray:
        if self._pts_local is None:
            raise TypeError('nur für Region.points / plane_grid')
        return self._pts_local

    def crop(self, mesh):
        """Mesh an der Region **abschneiden** (Clipping an sechs Halbräumen).

        Dreiecke, die die Boxwand kreuzen, werden geteilt statt verworfen -- sonst
        fallen große Dreiecke (Maschinen-STLs bis 25 mm Kantenlänge) komplett aus der
        Messung und die Primitive melden stillschweigend "nichts gefunden".
        Die Schnittflächen bleiben offen (cap=False); das Ergebnis ist nicht
        wasserdicht und darf es auch nicht müssen.
        """
        if self.kind == 'cylinder':
            return self._crop_cylinder(mesh)
        if self.kind != 'box':
            raise TypeError('crop() gibt es nur für Region.box / Region.cylinder')
        if mesh is None or len(mesh.faces) == 0:
            return mesh
        part = self._local_arrays(mesh)
        for axis in range(3):
            for sign, bound in ((1.0, self.lo[axis]), (-1.0, self.hi[axis])):
                part = self._slice(part, axis, sign, bound)
                if part is None:
                    # Leeres Fenster: es gibt nichts anzuschneiden. Der Merker wird
                    # trotzdem gesetzt, damit „nicht angeschnitten" und „gar nicht
                    # zugeschnitten" (Schlüssel fehlt) unterscheidbar bleiben.
                    self._rand_merken(False)
                    return self._empty()
        self._rand_merken(self._box_rand_trifft(part))
        return self._world_mesh(part)

    #: Ein Punkt gilt als „auf der Fensterwand", wenn er nicht weiter als das entfernt
    #: ist. 1e-6 mm, weil das Clipping die Schnittpunkte exakt auf die Ebene rechnet --
    #: alles Größere wäre schon eine gemessene Lücke.
    WAND_TOL_MM = 1e-6

    def _rand_merken(self, trifft: bool) -> None:
        """`rand_schneidet_material` sammeln (ODER über alle Zuschnitte dieser Region).

        Ein Primitiv beschneidet beide Seiten mit derselben Region; berührt auch nur
        eine davon die Fensterwand, ist der Hinweis fällig. Deshalb wird der Merker
        nicht je Zuschnitt zurückgesetzt, sondern aufgesammelt.
        """
        self.meta['rand_schneidet_material'] = bool(
            self.meta.get('rand_schneidet_material', False) or trifft)

    def _box_rand_trifft(self, part) -> bool:
        """Liegt nach dem Zuschnitt noch ein benutzter Punkt auf einer der sechs Wände?

        Material, das die Wand kreuzt, bekommt beim Clipping neue Ecken exakt auf der
        Ebene; ohne Kreuzung entsteht dort nichts. Der Test ist damit exakt und kostet
        nichts -- kein Suchen nach „fast auf der Wand".
        """
        verts, faces = part
        if len(faces) == 0:
            return False
        benutzt = verts[np.unique(faces)]
        nah = np.abs(benutzt - self.lo) <= self.WAND_TOL_MM
        nah |= np.abs(benutzt - self.hi) <= self.WAND_TOL_MM
        return bool(nah.any())

    def _crop_cylinder(self, mesh):
        """Mesh am Zylinder abschneiden: Deckel exakt, Mantel über Unterteilung.

        Die beiden Stirnflächen sind Ebenen, die schneidet `_slice` exakt. Für den
        Mantel gibt es keinen Halbraum-Schnitt; stattdessen werden die Dreiecke auf
        `radius/8` heruntergeteilt und dann die behalten, deren Ecken **alle** im
        Radius liegen. Der Fensterrand ist damit um höchstens eine Dreieckskante
        unscharf -- das steht als `rand_unschaerfe_mm` in `meta`, damit es im Bericht
        auftaucht statt still zu wirken.
        """
        if mesh is None or len(mesh.faces) == 0:
            return mesh
        from trimesh.remesh import subdivide_to_size
        verts, faces = self._local_arrays(mesh)
        for sign, punkt in ((1.0, 0.0), (-1.0, self.length)):
            out = self._slice_ebene(verts, faces, self.axis * sign,
                                    self.origin + self.axis * punkt)
            if out is None:
                self._rand_merken(False)
                return self._empty()
            verts, faces = out
        self._rand_merken(self._zylinder_rand_trifft(verts, faces))
        kante = max(self.radius / 8.0, 1e-3)
        verts, faces = subdivide_to_size(verts, faces, max_edge=kante)
        self.meta['rand_unschaerfe_mm'] = kante
        _, r = self._cyl_coords(verts)
        innen = self.meta.get('inner_radius', 0.0)
        drin = (r <= self.radius) & (r >= innen)
        faces = faces[np.all(drin[faces], axis=1)]
        if len(faces) == 0:
            return self._empty()
        # Nur noch benutzte Ecken behalten -- sonst schleppt das Ergebnis die
        # weggeschnittenen Punkte mit und jede bounds()-Auswertung misst zu groß.
        benutzt = np.unique(faces)
        neu = np.full(len(verts), -1, dtype=np.int64)
        neu[benutzt] = np.arange(len(benutzt))
        return self._world_mesh((np.asarray(verts[benutzt], dtype=float), neu[faces]))

    def _zylinder_rand_trifft(self, verts, faces) -> bool:
        """Kreuzt Material die **Mantel**wand des Zylinderfensters?

        Ein Dreieck, dessen Ecken beidseits des Radius liegen, wird von der Mantelfläche
        durchschnitten. Der Test läuft vor der Unterteilung und ist deshalb unabhängig
        von `rand_unschaerfe_mm`. Diese Unschärfe taugt hier nämlich nicht als Maßstab:
        sie ist `radius/8`, beim Fenster r 4,5 also 0,5625 mm. Der freie Zapfen endet
        bei 3,95 mm, ganze 0,55 mm vor der Wand -- über die Unschärfe gemessen wäre er
        fälschlich als „schneidet" gemeldet worden. Der Kreuzungstest trennt beide Fälle
        (Bund Ø10,5: der Stirnring kreuzt -> True; Zapfen Ø7,9: nichts kreuzt -> False).

        Die beiden **Deckel** zählen bewusst nicht mit. Ein Zylinderfenster wird über
        einem Rundteil gesetzt, um dessen Radius zu messen; die Länge schneidet dabei
        fast immer durch Material, ohne dass das Ergebnis darunter leidet. Der Befund
        geht trotzdem nicht verloren -- er steht als `rand_deckel_schneidet_material`
        in `meta`.
        """
        if len(faces) == 0:
            return False
        t, r = self._cyl_coords(verts)
        benutzt = np.unique(faces)
        auf_deckel = (np.abs(t[benutzt]) <= self.WAND_TOL_MM) | (
            np.abs(t[benutzt] - self.length) <= self.WAND_TOL_MM)
        self.meta['rand_deckel_schneidet_material'] = bool(
            self.meta.get('rand_deckel_schneidet_material', False) or auf_deckel.any())
        rf = r[faces]
        lo, hi = rf.min(axis=1), rf.max(axis=1)
        innen = self.meta.get('inner_radius', 0.0)
        kreuzt = (lo < self.radius) & (hi > self.radius)
        if innen > 0:
            kreuzt |= (lo < innen) & (hi > innen)
        return bool(kreuzt.any())

    def crop_complement(self, mesh):
        """Umkehrung von crop: alles, was **außerhalb** der Box liegt."""
        if self.kind != 'box':
            raise TypeError('crop_complement() gibt es nur für Region.box')
        if mesh is None or len(mesh.faces) == 0:
            return mesh
        rest = self._local_arrays(mesh)
        pieces = []
        for axis in range(3):
            for sign, bound in ((1.0, self.lo[axis]), (-1.0, self.hi[axis])):
                if rest is None:
                    break
                outside = self._slice(rest, axis, -sign, bound)
                if outside is not None:
                    pieces.append(outside)
                rest = self._slice(rest, axis, sign, bound)
            if rest is None:
                break
        if not pieces:
            return self._empty()
        offset = 0
        verts = []
        faces = []
        for v, f in pieces:
            verts.append(v)
            faces.append(f + offset)
            offset += len(v)
        return self._world_mesh((np.vstack(verts), np.vstack(faces)))

    # -- Clipping-Helfer -------------------------------------------------
    @staticmethod
    def _slice_ebene(verts, faces, normal, origin):
        """Halbraum normal*(x - origin) >= 0 behalten, ohne Deckel."""
        from trimesh.intersections import slice_faces_plane
        out = slice_faces_plane(np.asarray(verts, dtype=float), np.asarray(faces, dtype=np.int64),
                                np.asarray(normal, dtype=float), np.asarray(origin, dtype=float))
        v, f = out[0], out[1]
        if f is None or len(f) == 0:
            return None
        return np.asarray(v, dtype=float), np.asarray(f, dtype=np.int64)

    @staticmethod
    def _slice(part, axis, sign, bound):
        """Halbraum sign*(x[axis] - bound) >= 0 behalten, ohne Deckel.

        Arbeitet auf (vertices, faces); `slice_faces_plane` ist der Kern von
        `slice_mesh_plane` ohne dessen shapely-Abhängigkeit (die wir nur für den
        Deckel bräuchten).
        """
        from trimesh.intersections import slice_faces_plane
        verts, faces = part
        normal = np.zeros(3)
        normal[axis] = sign
        origin = np.zeros(3)
        origin[axis] = bound
        out = slice_faces_plane(verts, faces, normal, origin)
        v, f = out[0], out[1]
        if f is None or len(f) == 0:
            return None
        return np.asarray(v, dtype=float), np.asarray(f, dtype=np.int64)

    def _local_arrays(self, mesh):
        return (np.asarray(self.frame.to_local(np.asarray(mesh.vertices, dtype=float)), dtype=float),
                np.asarray(mesh.faces, dtype=np.int64))

    def _world_mesh(self, part):
        import trimesh
        verts, faces = part
        return trimesh.Trimesh(vertices=self.frame.to_world(verts), faces=faces, process=False)

    @staticmethod
    def _empty():
        import trimesh
        return trimesh.Trimesh(vertices=np.zeros((0, 3)), faces=np.zeros((0, 3), dtype=np.int64), process=False)

    def __repr__(self):
        if self.kind == 'box':
            return f'Region.box(lo={np.round(self.lo, 2).tolist()}, hi={np.round(self.hi, 2).tolist()})'
        if self.kind == 'cylinder':
            return (f'Region.cylinder(origin={np.round(self.origin, 2).tolist()}, '
                    f'axis={np.round(self.axis, 3).tolist()}, r={self.radius:g}, l={self.length:g}'
                    + (f', innen={self.meta["inner_radius"]:g})' if self.meta.get('inner_radius') else ')'))
        return f'Region.points(n={len(self._pts_local)})'
