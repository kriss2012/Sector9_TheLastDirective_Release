"""Scene helpers and the MeshBuilder (bmesh wrapper with material + skin-weight support)."""
from __future__ import annotations
import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler

V = Vector


class BuildError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- scene
def clear_scene() -> None:
    """Return Blender to an empty factory state (deterministic start)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def get_collection(name: str, parent: Optional[bpy.types.Collection] = None) -> bpy.types.Collection:
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    elif parent is not None and name not in [c.name for c in parent.children]:
        try:
            parent.children.link(col)
        except RuntimeError:
            pass
    return col


def link_only(obj: bpy.types.Object, col: bpy.types.Collection) -> None:
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)


def set_active(obj: bpy.types.Object) -> None:
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def new_empty(name: str, col: bpy.types.Collection, loc=(0, 0, 0), display='ARROWS', size=0.1):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = display
    e.empty_display_size = size
    e.location = loc
    col.objects.link(e)
    return e


def apply_modifiers(obj: bpy.types.Object) -> None:
    """Bake all modifiers into mesh data (works headless, no ops context needed)."""
    if not obj.modifiers:
        return
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    new_me = bpy.data.meshes.new_from_object(ev, depsgraph=dg)
    old = obj.data
    mats = list(old.materials)
    obj.modifiers.clear()
    obj.data = new_me
    for m in mats:
        new_me.materials.append(m)
    # keep vertex groups (names live on the object, indices stay valid because
    # modifiers used here never reorder original vertices ahead of groups)
    bpy.data.meshes.remove(old)


# ----------------------------------------------------------------------------- maths
def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 0.0 if x < a else 1.0
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def gauss(x: float, s: float) -> float:
    return math.exp(-(x * x) / (2 * s * s))


def lerp(a, b, t):
    return a + (b - a) * t


def seg_dist(p: Vector, a: Vector, b: Vector) -> float:
    ab = b - a
    l2 = ab.length_squared
    if l2 < 1e-12:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    return (p - (a + ab * t)).length


def frame_from_tangent(t: Vector, ref: Vector = V((1, 0, 0))) -> Tuple[Vector, Vector, Vector]:
    t = t.normalized()
    u = ref - t * ref.dot(t)
    if u.length < 1e-6:
        u = V((0, 1, 0)) - t * V((0, 1, 0)).dot(t)
    u.normalize()
    v = t.cross(u).normalized()
    return t, u, v


def ring_ellipse(center: Vector, u: Vector, v: Vector, rx: float, ry: float, n: int,
                 power: float = 2.0, offx: float = 0.0, offy: float = 0.0) -> List[Vector]:
    """Super-ellipse ring. angle 0 starts at +u axis."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a), math.sin(a)
        cx = math.copysign(abs(c) ** (2 / power), c)
        sy = math.copysign(abs(s) ** (2 / power), s)
        pts.append(center + u * (offx + rx * cx) + v * (offy + ry * sy))
    return pts


# ----------------------------------------------------------------------------- skin weights
class WeightSpec:
    """How verts created by a MeshBuilder call are bound to bones."""

    def __init__(self, bones: Sequence[str], mode: str = 'auto', power: float = 5.0,
                 max_infl: int = 4, bone_table=None, bias: Optional[Dict[str, float]] = None):
        self.bones = list(bones)
        self.mode = mode           # 'rigid' (single bone) or 'auto'
        self.power = power
        self.max_infl = max_infl
        self.table = bone_table
        self.bias = bias or {}

    @staticmethod
    def rigid(bone: str) -> "WeightSpec":
        return WeightSpec([bone], 'rigid')

    @staticmethod
    def auto(bones: Sequence[str], table, power: float = 5.0, bias=None) -> "WeightSpec":
        return WeightSpec(bones, 'auto', power, 4, table, bias)

    def weights_for(self, p: Vector) -> Dict[str, float]:
        if self.mode == 'rigid' or len(self.bones) == 1:
            return {self.bones[0]: 1.0}
        ds = []
        for b in self.bones:
            h, t = self.table[b]['head'], self.table[b]['tail']
            d = seg_dist(p, h, t)
            ds.append((b, d))
        raw = {}
        for b, d in ds:
            raw[b] = self.bias.get(b, 1.0) / ((d + 0.012) ** self.power)
        top = sorted(raw.items(), key=lambda kv: -kv[1])[: self.max_infl]
        tot = sum(w for _, w in top)
        out = {b: w / tot for b, w in top if w / tot > 0.02}
        tot = sum(out.values())
        return {b: w / tot for b, w in out.items()}


# ----------------------------------------------------------------------------- MeshBuilder
class MeshBuilder:
    """Accumulates geometry in one bmesh; faces get a material slot index, verts get skin weights.

    All positions are in object space (objects are created at the origin, rest pose).
    """

    def __init__(self, name: str):
        self.name = name
        self.bm = bmesh.new()
        self.mats: List[bpy.types.Material] = []
        self.dvl = self.bm.verts.layers.deform.verify()
        self.group_names: Dict[str, int] = {}

    # ---- bookkeeping
    def slot(self, mat: Optional[bpy.types.Material]) -> int:
        if mat is None:
            return 0
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _gidx(self, name: str) -> int:
        if name not in self.group_names:
            self.group_names[name] = len(self.group_names)
        return self.group_names[name]

    def _finish(self, verts, faces, mat, bind: Optional[WeightSpec]):
        idx = self.slot(mat)
        for f in faces:
            f.material_index = idx
            f.smooth = True
        if bind is not None:
            for v in verts:
                for b, w in bind.weights_for(v.co).items():
                    v[self.dvl][self._gidx(b)] = w

    # ---- primitives
    def add_box(self, center, size, rot: Optional[Euler] = None, mat=None, bind=None, bevel: float = 0.0,
                taper: Optional[Tuple[float, float]] = None) -> None:
        """size = full extents (x, y, z). taper = (top_x_scale, top_y_scale) for +Z face."""
        bm = self.bm
        ret = bmesh.ops.create_cube(bm, size=1.0)
        verts = ret['verts']
        sx, sy, sz = size
        R = rot.to_matrix() if rot is not None else Matrix.Identity(3)
        for v in verts:
            x, y, z = v.co.x * sx, v.co.y * sy, v.co.z * sz
            if taper and v.co.z > 0:
                x *= taper[0]
                y *= taper[1]
            v.co = R @ V((x, y, z)) + V(center)
        faces = list({f for v in verts for f in v.link_faces})
        if bevel > 0:
            edges = list({e for v in verts for e in v.link_edges})
            res = bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=2, affect='EDGES', profile=0.6)
            verts = [g for g in res['verts']] + [v for v in verts if v.is_valid]
            faces = list({f for v in verts for f in v.link_faces})
        self._finish(verts, faces, mat, bind)

    def add_cyl(self, p0, p1, r0, r1=None, segs: int = 12, mat=None, bind=None, caps: bool = True,
                ref=V((1, 0, 0)), squash: float = 1.0) -> None:
        """Tapered cylinder between two points. squash scales the 'v' axis radius."""
        p0, p1 = V(p0), V(p1)
        r1 = r0 if r1 is None else r1
        t, u, v = frame_from_tangent(p1 - p0, ref)
        rings = [ring_ellipse(p0, u, v, r0, r0 * squash, segs), ring_ellipse(p1, u, v, r1, r1 * squash, segs)]
        self.add_loft(rings, caps=caps, mat=mat, bind=bind)

    def add_sphere(self, center, radii, segs: int = 16, rings: int = 10, mat=None, bind=None,
                   rot: Optional[Euler] = None) -> None:
        bm = self.bm
        ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
        verts = ret['verts']
        R = rot.to_matrix() if rot is not None else Matrix.Identity(3)
        for v in verts:
            v.co = R @ V((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2])) + V(center)
        faces = list({f for v in verts for f in v.link_faces})
        self._finish(verts, faces, mat, bind)

    def add_loft(self, rings: List[List[Vector]], caps: bool = True, closed: bool = True, mat=None,
                 bind=None, flip: Optional[bool] = None, smooth: bool = True) -> None:
        """Skin a list of equal-length vertex rings. closed=False gives an open strip (cloth)."""
        bm = self.bm
        n = len(rings[0])
        if any(len(r) != n for r in rings):
            raise BuildError("loft rings must have equal vertex counts")
        vr = [[bm.verts.new(p) for p in ring] for ring in rings]
        faces = []
        span = n if closed else n - 1
        for i in range(len(vr) - 1):
            for j in range(span):
                a, b = vr[i][j], vr[i][(j + 1) % n]
                c, d = vr[i + 1][(j + 1) % n], vr[i + 1][j]
                try:
                    faces.append(bm.faces.new((a, b, c, d)))
                except ValueError:
                    pass
        if caps and closed:
            for ring in (vr[0], vr[-1]):
                cen = sum((v.co for v in ring), V()) / n
                cv = bm.verts.new(cen)
                for j in range(n):
                    try:
                        faces.append(bm.faces.new((ring[j], ring[(j + 1) % n], cv)))
                    except ValueError:
                        pass
                vr.append([cv])
        # orientation: make the first side quad face away from its ring centre
        if faces:
            if flip is None:
                f = faces[0]
                cen0 = sum((v.co for v in vr[0]), V()) / n
                cen1 = sum((v.co for v in vr[1]), V()) / n
                axis_c = (cen0 + cen1) / 2
                bm.normal_update()
                flip = f.normal.dot(f.calc_center_median() - axis_c) < 0
            if flip:
                bmesh.ops.reverse_faces(bm, faces=faces)
            for f in faces:
                f.smooth = smooth
        verts = [v for ring in vr for v in ring]
        self._finish(verts, faces, mat, bind)

    def add_tube_path(self, pts: Sequence[Vector], radii: Sequence[float], segs: int = 8, mat=None,
                      bind=None, squash: float = 1.0, ref=V((0, 0, 1)), caps: bool = True) -> None:
        """Tube along a polyline with per-point radius (parallel-transport frames)."""
        rings = []
        n = len(pts)
        u_prev = None
        for i, p in enumerate(pts):
            if i == 0:
                tan = pts[1] - pts[0]
            elif i == n - 1:
                tan = pts[-1] - pts[-2]
            else:
                tan = pts[i + 1] - pts[i - 1]
            tan = V(tan).normalized()
            if u_prev is None:
                _, u, v = frame_from_tangent(tan, ref)
            else:
                u = u_prev - tan * u_prev.dot(tan)
                if u.length < 1e-6:
                    _, u, v = frame_from_tangent(tan, ref)
                u = u.normalized()
                v = tan.cross(u).normalized()
            u_prev = u
            rings.append(ring_ellipse(V(p), u, v, radii[i], radii[i] * squash, segs))
        self.add_loft(rings, caps=caps, mat=mat, bind=bind)

    def add_mesh_data(self, verts: Sequence[Sequence[float]], faces: Sequence[Sequence[int]], mat=None,
                      bind=None, smooth: bool = True) -> List[bmesh.types.BMVert]:
        bv = [self.bm.verts.new(V(p)) for p in verts]
        fs = []
        for f in faces:
            try:
                fs.append(self.bm.faces.new([bv[i] for i in f]))
            except ValueError:
                pass
        self._finish(bv, fs, mat, bind)
        for f in fs:
            f.smooth = smooth
        return bv

    def nverts(self) -> int:
        return len(self.bm.verts)

    def verts_from(self, start: int):
        self.bm.verts.ensure_lookup_table()
        return [self.bm.verts[i] for i in range(start, len(self.bm.verts))]

    # ---- output
    def box_uv(self, scale: float = 1.0, name: str = "UVMap") -> None:
        """World-scale box projection (1 UV unit = 1/scale metres). Used as base unwrap."""
        bm = self.bm
        uvl = bm.loops.layers.uv.get(name) or bm.loops.layers.uv.new(name)
        bm.normal_update()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                if ax == 0:
                    uv = (c.y, c.z)
                elif ax == 1:
                    uv = (c.x, c.z)
                else:
                    uv = (c.x, c.y)
                l[uvl].uv = (uv[0] * scale, uv[1] * scale)

    def recalc_normals(self) -> None:
        bmesh.ops.recalc_face_normals(self.bm, faces=list(self.bm.faces))

    def weld(self, dist: float = 1e-5) -> None:
        bmesh.ops.remove_doubles(self.bm, verts=list(self.bm.verts), dist=dist)

    def to_object(self, col: bpy.types.Collection, loc=(0, 0, 0), smooth: bool = True,
                  auto_smooth_angle: Optional[float] = None) -> bpy.types.Object:
        me = bpy.data.meshes.new(self.name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        for m in self.mats:
            me.materials.append(m)
        me.update()
        ob = bpy.data.objects.new(self.name, me)
        col.objects.link(ob)
        ob.location = loc
        for name, idx in sorted(self.group_names.items(), key=lambda kv: kv[1]):
            ob.vertex_groups.new(name=name)
        # bmesh deform layer indices follow insertion order == vertex_groups order
        self.bm.free()
        return ob


def shade_smooth_by_angle(obj: bpy.types.Object, deg: float = 40.0) -> None:
    """Smooth shading with sharp edges above the angle (version tolerant)."""
    me = obj.data
    for p in me.polygons:
        p.use_smooth = True
    try:  # Blender >= 4.1: edge sharpness by angle without modifiers
        set_active(obj)
        bpy.ops.object.shade_auto_smooth(use_auto_smooth=True, angle=math.radians(deg))
    except Exception:
        try:
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(deg)
        except Exception:
            pass


def add_bevel(obj: bpy.types.Object, width: float = 0.0015, segments: int = 2, angle_deg: float = 35.0,
              apply: bool = True) -> None:
    m = obj.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = 'ANGLE'
    m.angle_limit = math.radians(angle_deg)
    if apply:
        apply_modifiers(obj)


def unwrap_smart(obj: bpy.types.Object, angle_deg: float = 66.0, margin: float = 0.003) -> bool:
    """Non-overlapping smart-project unwrap into the active UV map. Returns success."""
    try:
        set_active(obj)
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[utils] smart_project failed for {obj.name}: {exc}")
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except Exception:
            pass
        return False


def mesh_stats(obj: bpy.types.Object) -> Dict[str, int]:
    me = obj.data
    return dict(verts=len(me.vertices), faces=len(me.polygons), tris=sum(len(p.vertices) - 2 for p in me.polygons))


def rng(seed: int, salt: str = "") -> random.Random:
    return random.Random(f"{seed}:{salt}")
