"""Procedural PBR material library (pure shader nodes, no external image files).

Every material is built by :func:`make_pbr`, which produces a Principled BSDF graph with
* a colour chain (base -> wear/dirt mask -> variation),
* a roughness chain (noise driven),
* a bump chain (pattern specific micro detail),
and records ``metallic_const`` / ``socket links`` so :mod:`bake` can convert the graph to image
textures for glTF export.
"""
from __future__ import annotations
from typing import Dict, Optional, Sequence, Tuple
import bpy

Color = Tuple[float, float, float]


def _set(node, name: str, value) -> bool:
    """Set an input if it exists (Principled socket names differ between Blender versions)."""
    sock = node.inputs.get(name)
    if sock is None:
        return False
    sock.default_value = value
    return True


def _rgba(c: Sequence[float]):
    return (c[0], c[1], c[2], 1.0)


class _G:
    """Tiny node-graph helper."""

    def __init__(self, mat: bpy.types.Material):
        mat.use_nodes = True
        self.mat = mat
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = -1400
        self.y = 0

    def n(self, kind: str, label: Optional[str] = None, loc=None):
        node = self.nt.nodes.new(kind)
        if label:
            node.label = label
        node.location = loc or (self.x, self.y)
        self.y -= 220
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op: str, a=None, b=None, c=None, clamp=False):
        m = self.n('ShaderNodeMath')
        m.operation = op
        m.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def ramp(self, fac, stops: Sequence[Tuple[float, Sequence[float]]], interp='LINEAR'):
        r = self.n('ShaderNodeValToRGB')
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = _rgba(col) if len(col) == 3 else col
        if fac is not None:
            self.link(fac, r.inputs['Fac'])
        return r

    def noise(self, vec, scale, detail=6.0, rough=0.55, distortion=0.0):
        t = self.n('ShaderNodeTexNoise')
        try:
            t.noise_dimensions = '3D'
        except Exception:
            pass
        t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = detail
        t.inputs['Roughness'].default_value = rough
        if 'Distortion' in t.inputs:
            t.inputs['Distortion'].default_value = distortion
        self.link(vec, t.inputs['Vector'])
        return t.outputs['Fac']

    def voronoi(self, vec, scale, feature='F1', metric=None, out='Distance'):
        t = self.n('ShaderNodeTexVoronoi')
        t.feature = feature
        if metric:
            t.distance = metric
        t.inputs['Scale'].default_value = scale
        self.link(vec, t.inputs['Vector'])
        return t.outputs[out]


def make_pbr(name: str, base: Color, metallic: float = 0.0, roughness: float = 0.5, *,
             wear: Optional[Color] = None, wear_amount: float = 0.0, wear_metallic: Optional[float] = None,
             wear_rough: Optional[float] = None, dirt: float = 0.25, pattern: Optional[str] = None,
             scale: float = 12.0, bump: float = 0.15, rough_var: float = 0.15, coord: str = 'OBJECT',
             sss: float = 0.0, sss_color: Optional[Color] = None, emission: Optional[Color] = None,
             emission_strength: float = 0.0, coat: float = 0.0, tint_var: float = 0.12,
             pattern_colors: Optional[Sequence[Color]] = None, anisotropic: float = 0.0,
             alpha: float = 1.0, ior: Optional[float] = None, transmission: float = 0.0) -> bpy.types.Material:
    """Create (or fetch) a node-based PBR material.

    pattern: None | 'weave' | 'leather' | 'diamond' | 'camo' | 'skin' | 'knurl' | 'hair' | 'rubber' | 'wood' | 'scratch'
    coord:   'OBJECT' (rigid props) or 'UV' (deforming characters).
    """
    existing = bpy.data.materials.get(name)
    if existing is not None:
        return existing
    mat = bpy.data.materials.new(name)
    g = _G(mat)
    out = g.n('ShaderNodeOutputMaterial', loc=(900, 0))
    bsdf = g.n('ShaderNodeBsdfPrincipled', loc=(600, 0))
    g.link(bsdf.outputs['BSDF'], out.inputs['Surface'])

    # coordinates
    tc = g.n('ShaderNodeTexCoord')
    src = tc.outputs['Object'] if coord == 'OBJECT' else tc.outputs['UV']
    mp = g.n('ShaderNodeMapping')
    g.link(src, mp.inputs['Vector'])
    vec = mp.outputs['Vector']
    if coord == 'UV':
        mp.inputs['Scale'].default_value = (1.0, 1.0, 1.0)

    s = scale if coord == 'OBJECT' else scale * 0.35   # UV space is ~0..1, object space is metres

    # ------------------------------------------------------------ wear / dirt mask
    n1 = g.noise(vec, s * 0.6, 7.0, 0.6, 0.3)
    n2 = g.noise(vec, s * 3.0, 4.0, 0.5)
    mask_a = g.ramp(n1, [(0.50 - 0.15 * wear_amount, (0, 0, 0)), (0.62, (1, 1, 1))]).outputs['Color']
    vor = g.voronoi(vec, s * 1.5, 'DISTANCE_TO_EDGE', out='Distance')
    edge_mask = g.ramp(vor, [(0.0, (1, 1, 1)), (0.06, (0, 0, 0))]).outputs['Color']
    wear_mask = g.math('MULTIPLY', g.math('MAXIMUM', mask_a, edge_mask), wear_amount * 1.0, clamp=True)
    wear_mask = g.math('MULTIPLY', wear_mask, g.ramp(n2, [(0.35, (0, 0, 0)), (0.6, (1, 1, 1))]).outputs['Color'],
                       clamp=True) if wear_amount > 0 else wear_mask

    # ------------------------------------------------------------ pattern producers
    pattern_col = None
    height = n2
    if pattern == 'weave':
        brick = g.n('ShaderNodeTexBrick')
        brick.inputs['Scale'].default_value = s * 9.0
        brick.inputs['Mortar Size'].default_value = 0.04
        brick.inputs['Brick Width'].default_value = 1.0
        brick.inputs['Row Height'].default_value = 1.0
        brick.inputs['Color1'].default_value = _rgba([c * 1.15 for c in base])
        brick.inputs['Color2'].default_value = _rgba([c * 0.85 for c in base])
        g.link(vec, brick.inputs['Vector'])
        pattern_col = brick.outputs['Color']
        height = g.math('ADD', brick.outputs['Fac'], g.math('MULTIPLY', n2, 0.6))
    elif pattern == 'leather':
        v = g.voronoi(vec, s * 12.0 if coord == 'OBJECT' else s * 6.0, 'F1', out='Distance')
        height = g.math('ADD', g.math('MULTIPLY', v, 1.0), g.math('MULTIPLY', n2, 0.5))
    elif pattern == 'rubber':
        v = g.voronoi(vec, s * 14.0 if coord == 'OBJECT' else s * 7.0, 'F1', out='Distance')
        height = g.math('ADD', v, g.math('MULTIPLY', n2, 0.4))
    elif pattern == 'diamond':
        rot = g.n('ShaderNodeMapping')
        rot.vector_type = 'POINT'
        rot.inputs['Rotation'].default_value = (0.0, 0.0, 0.7853982)
        g.link(vec, rot.inputs['Vector'])
        chk = g.n('ShaderNodeTexChecker')
        chk.inputs['Scale'].default_value = s * 1.6
        g.link(rot.outputs['Vector'], chk.inputs['Vector'])
        height = g.math('ADD', chk.outputs['Fac'], g.math('MULTIPLY', n2, 0.35))
    elif pattern == 'knurl':
        rot = g.n('ShaderNodeMapping')
        rot.vector_type = 'POINT'
        rot.inputs['Rotation'].default_value = (0.0, 0.0, 0.7853982)
        g.link(vec, rot.inputs['Vector'])
        chk = g.n('ShaderNodeTexChecker')
        chk.inputs['Scale'].default_value = s * 2.4
        g.link(rot.outputs['Vector'], chk.inputs['Vector'])
        height = g.math('ADD', chk.outputs['Fac'], g.math('MULTIPLY', n2, 0.25))
    elif pattern == 'camo' and pattern_colors:
        # pixelated (digital) camo: quantise coordinates then threshold noise
        sep = g.n('ShaderNodeSeparateXYZ')
        g.link(vec, sep.inputs['Vector'])
        q = 14.0
        comps = []
        for k in ('X', 'Y', 'Z'):
            sc = g.math('MULTIPLY', sep.outputs[k], q)
            fl = g.math('FLOOR', sc)
            comps.append(g.math('DIVIDE', fl, q))
        com = g.n('ShaderNodeCombineXYZ')
        for i, c in enumerate(comps):
            g.link(c, com.inputs[i])
        cn = g.noise(com.outputs['Vector'], s * 0.5, 3.0, 0.6)
        cols = list(pattern_colors)
        stops = [(i / max(1, len(cols) - 1) * 0.8 + 0.1, c) for i, c in enumerate(cols)]
        rp = g.ramp(cn, stops, interp='CONSTANT')
        pattern_col = rp.outputs['Color']
        height = g.math('ADD', n2, 0.0)
    elif pattern == 'skin':
        v = g.voronoi(vec, s * 14.0, 'F1', out='Distance')
        height = g.math('ADD', g.math('MULTIPLY', v, 0.7), g.math('MULTIPLY', n2, 0.3))
    elif pattern == 'hair':
        stretch = g.n('ShaderNodeMapping')
        g.link(vec, stretch.inputs['Vector'])
        stretch.inputs['Scale'].default_value = (60.0, 60.0, 4.0) if coord == 'OBJECT' else (30.0, 2.0, 1.0)
        height = g.noise(stretch.outputs['Vector'], 18.0, 3.0, 0.7)
    elif pattern == 'wood':
        wv = g.n('ShaderNodeTexWave')
        wv.wave_type = 'BANDS'
        wv.inputs['Scale'].default_value = s * 0.8
        wv.inputs['Distortion'].default_value = 6.0
        wv.inputs['Detail'].default_value = 3.0
        g.link(vec, wv.inputs['Vector'])
        height = g.math('ADD', wv.outputs['Fac'], g.math('MULTIPLY', n2, 0.3))
    elif pattern == 'scratch':
        st = g.n('ShaderNodeMapping')
        g.link(vec, st.inputs['Vector'])
        st.inputs['Scale'].default_value = (1.0, 40.0, 1.0)
        sc = g.noise(st.outputs['Vector'], s * 2.0, 2.0, 0.8)
        height = g.math('ADD', g.math('MULTIPLY', sc, 0.8), n2)

    # ------------------------------------------------------------ colour chain
    base_node = g.n('ShaderNodeRGB', 'base')
    base_node.outputs[0].default_value = _rgba(base)
    col = pattern_col if pattern_col is not None else base_node.outputs[0]
    if wear is not None and wear_amount > 0:
        wn = g.n('ShaderNodeRGB', 'wear')
        wn.outputs[0].default_value = _rgba(wear)
        mx = g.n('ShaderNodeMixRGB')
        mx.blend_type = 'MIX'
        g.link(wear_mask, mx.inputs['Fac'])
        g.link(col, mx.inputs['Color1'])
        g.link(wn.outputs[0], mx.inputs['Color2'])
        col = mx.outputs['Color']
    # dirt / tonal variation
    dn = g.noise(vec, s * 0.35, 5.0, 0.6)
    var = g.ramp(dn, [(0.3, (1 - tint_var,) * 3), (0.7, (1 + tint_var * 0.4,) * 3)]).outputs['Color']
    mv = g.n('ShaderNodeMixRGB')
    mv.blend_type = 'MULTIPLY'
    mv.inputs['Fac'].default_value = 1.0
    g.link(col, mv.inputs['Color1'])
    g.link(var, mv.inputs['Color2'])
    col = mv.outputs['Color']
    if dirt > 0:
        dd = g.noise(vec, s * 0.9, 8.0, 0.65, 0.5)
        dm = g.ramp(dd, [(0.5, (0, 0, 0)), (0.75, (dirt, dirt, dirt))]).outputs['Color']
        dmx = g.n('ShaderNodeMixRGB')
        dmx.blend_type = 'MULTIPLY'
        dmx.inputs['Fac'].default_value = 1.0
        inv = g.n('ShaderNodeInvert')
        g.link(dm, inv.inputs['Color'])
        g.link(col, dmx.inputs['Color1'])
        g.link(inv.outputs['Color'], dmx.inputs['Color2'])
        col = dmx.outputs['Color']
    g.link(col, bsdf.inputs['Base Color'])
    mat["bc_socket_node"] = col.node.name
    mat["bc_socket_name"] = col.name

    # ------------------------------------------------------------ roughness chain
    rn = g.noise(vec, s * 1.2, 5.0, 0.5)
    rr = g.n('ShaderNodeMapRange')
    rr.inputs['To Min'].default_value = max(0.0, roughness - rough_var)
    rr.inputs['To Max'].default_value = min(1.0, roughness + rough_var)
    g.link(rn, rr.inputs['Value'])
    rough = rr.outputs['Result']
    if wear_rough is not None and wear_amount > 0:
        rm = g.n('ShaderNodeMix')
        rm.data_type = 'FLOAT'
        g.link(wear_mask, rm.inputs['Factor'])
        g.link(rough, rm.inputs[2])
        rm.inputs[3].default_value = wear_rough
        rough = rm.outputs[0]
    g.link(rough, bsdf.inputs['Roughness'])
    mat["rough_socket_node"] = rough.node.name
    mat["rough_socket_name"] = rough.name

    # ------------------------------------------------------------ metallic
    if wear_metallic is not None and wear_amount > 0:
        mm = g.n('ShaderNodeMix')
        mm.data_type = 'FLOAT'
        mm.inputs[2].default_value = metallic
        mm.inputs[3].default_value = wear_metallic
        g.link(wear_mask, mm.inputs['Factor'])
        g.link(mm.outputs[0], bsdf.inputs['Metallic'])
        mat["metallic_const"] = float(0.5 * (metallic + wear_metallic) if wear_amount > 0.5 else metallic)
    else:
        _set(bsdf, 'Metallic', metallic)
        mat["metallic_const"] = float(metallic)

    # ------------------------------------------------------------ bump
    bn = g.n('ShaderNodeBump')
    bn.inputs['Strength'].default_value = min(1.0, bump)
    bn.inputs['Distance'].default_value = 0.01 if coord == 'OBJECT' else 0.004
    g.link(height, bn.inputs['Height'])
    g.link(bn.outputs['Normal'], bsdf.inputs['Normal'])

    # ------------------------------------------------------------ misc inputs
    if sss > 0:
        _set(bsdf, 'Subsurface Weight', sss)
        _set(bsdf, 'Subsurface Radius', (1.0, 0.35, 0.22))
        if sss_color:
            _set(bsdf, 'Subsurface Scale', 0.02)
    if coat > 0:
        _set(bsdf, 'Coat Weight', coat)
        _set(bsdf, 'Coat Roughness', 0.15)
    if emission is not None:
        _set(bsdf, 'Emission Color', _rgba(emission))
        _set(bsdf, 'Emission Strength', emission_strength)
    if anisotropic > 0:
        _set(bsdf, 'Anisotropic', anisotropic)
    if alpha < 1.0:
        _set(bsdf, 'Alpha', alpha)
        mat.blend_method = 'BLEND' if hasattr(mat, 'blend_method') else None
    if ior is not None:
        _set(bsdf, 'IOR', ior)
    if transmission > 0:
        _set(bsdf, 'Transmission Weight', transmission)
    mat.diffuse_color = _rgba(base)
    mat.metallic = float(metallic)
    mat.roughness = float(roughness)
    return mat


# ======================================================================================
# Library
# ======================================================================================
def build_library(skin_male: Color, skin_female: Color, hair_male: Color, hair_female: Color) -> Dict[str, bpy.types.Material]:
    L: Dict[str, bpy.types.Material] = {}
    # ---------------- weapons (rigid props: object coordinates)
    L['polymer'] = make_pbr("M_Polymer_Black", (0.018, 0.018, 0.020), 0.0, 0.55, wear=(0.07, 0.07, 0.075),
                            wear_amount=0.55, wear_rough=0.35, pattern='rubber', scale=40, bump=0.12, dirt=0.3)
    L['gunmetal'] = make_pbr("M_Gunmetal", (0.06, 0.062, 0.066), 1.0, 0.38, wear=(0.45, 0.45, 0.46),
                             wear_amount=0.6, wear_rough=0.25, pattern='scratch', scale=30, bump=0.08, dirt=0.35)
    L['steel_bare'] = make_pbr("M_Steel_Bare", (0.55, 0.55, 0.56), 1.0, 0.32, wear=(0.8, 0.8, 0.8), wear_amount=0.4,
                               wear_rough=0.22, pattern='scratch', scale=30, bump=0.06, dirt=0.18)
    L['cerakote_tan'] = make_pbr("M_Cerakote_Tan", (0.27, 0.19, 0.075), 0.45, 0.42, wear=(0.18, 0.18, 0.18),
                                 wear_amount=0.55, wear_metallic=1.0, wear_rough=0.3, pattern='scratch', scale=26,
                                 bump=0.07, dirt=0.3)
    L['brass'] = make_pbr("M_Brass_Aged", (0.55, 0.37, 0.10), 1.0, 0.33, wear=(0.2, 0.12, 0.04), wear_amount=0.45,
                          wear_rough=0.5, pattern='scratch', scale=30, bump=0.05, dirt=0.4)
    L['blade'] = make_pbr("M_Blade_Steel", (0.62, 0.63, 0.64), 1.0, 0.24, wear=(0.35, 0.35, 0.36), wear_amount=0.35,
                          wear_rough=0.4, pattern='scratch', scale=34, bump=0.06, rough_var=0.12, dirt=0.15)
    L['wood_dark'] = make_pbr("M_Wood_Ebony", (0.035, 0.022, 0.014), 0.0, 0.5, wear=(0.12, 0.07, 0.04), wear_amount=0.35,
                              wear_rough=0.35, pattern='wood', scale=24, bump=0.12, coat=0.25, dirt=0.2)
    L['grip_diamond'] = make_pbr("M_Grip_Diamond", (0.03, 0.02, 0.015), 0.0, 0.5, wear=(0.14, 0.09, 0.05),
                                 wear_amount=0.5, wear_rough=0.3, pattern='diamond', scale=40, bump=0.5, coat=0.2, dirt=0.15)
    L['leather_black'] = make_pbr("M_Leather_Black", (0.016, 0.016, 0.018), 0.0, 0.58, wear=(0.08, 0.075, 0.07),
                                  wear_amount=0.5, wear_rough=0.4, pattern='leather', scale=36, bump=0.3, dirt=0.3)
    L['glass_lens'] = make_pbr("M_Sight_Glass", (0.02, 0.03, 0.04), 0.0, 0.05, scale=10, bump=0.0, dirt=0.0,
                               emission=(1.0, 0.05, 0.03), emission_strength=0.4, coat=0.8, tint_var=0.0)
    L['reticle'] = make_pbr("M_Reticle_Red", (1.0, 0.03, 0.02), 0.0, 0.3, scale=10, bump=0.0, dirt=0.0,
                            emission=(1.0, 0.03, 0.02), emission_strength=12.0, tint_var=0.0)
    L['camo_pouch'] = make_pbr("M_Camo_Digital", (0.1, 0.15, 0.06), 0.0, 0.85, pattern='camo', scale=14, bump=0.2,
                               pattern_colors=[(0.05, 0.08, 0.03), (0.16, 0.20, 0.08), (0.08, 0.06, 0.035), (0.22, 0.27, 0.12)],
                               dirt=0.35, coord='OBJECT', wear=(0.15, 0.14, 0.1), wear_amount=0.2)
    L['webbing_olive'] = make_pbr("M_Webbing_Olive", (0.07, 0.10, 0.04), 0.0, 0.9, pattern='weave', scale=30,
                                  bump=0.3, dirt=0.35)
    L['badge_red'] = make_pbr("M_Badge_Red", (0.55, 0.03, 0.03), 0.3, 0.45, scale=10, bump=0.0, dirt=0.1)
    # ---------------- clothing (UV coordinates)
    L['jacket'] = make_pbr("M_Jacket_Black", (0.010, 0.0095, 0.0095), 0.0, 0.72, wear=(0.05, 0.043, 0.038),
                           wear_amount=0.4, wear_rough=0.45, pattern='weave', scale=26, bump=0.35, dirt=0.4, coord='UV')
    L['shirt'] = make_pbr("M_Shirt_Black", (0.012, 0.012, 0.014), 0.0, 0.85, pattern='weave', scale=34, bump=0.2,
                          dirt=0.3, coord='UV')
    L['pants'] = make_pbr("M_Pants_Black", (0.011, 0.0105, 0.0105), 0.0, 0.8, wear=(0.05, 0.045, 0.04), wear_amount=0.4,
                          wear_rough=0.5, pattern='weave', scale=26, bump=0.3, dirt=0.45, coord='UV')
    L['webbing'] = make_pbr("M_Webbing_Black", (0.009, 0.009, 0.010), 0.0, 0.88, pattern='weave', scale=40, bump=0.4,
                            dirt=0.3, coord='UV')
    L['gear_nylon'] = make_pbr("M_Gear_Nylon", (0.010, 0.010, 0.011), 0.0, 0.8, wear=(0.05, 0.047, 0.043), wear_amount=0.4,
                               wear_rough=0.5, pattern='weave', scale=36, bump=0.3, dirt=0.4, coord='UV')
    L['boot_leather'] = make_pbr("M_Boot_Leather", (0.015, 0.014, 0.014), 0.0, 0.5, wear=(0.09, 0.07, 0.06), wear_amount=0.6,
                                 wear_rough=0.35, pattern='leather', scale=30, bump=0.25, dirt=0.45, coord='UV', coat=0.15)
    L['rubber_sole'] = make_pbr("M_Rubber_Sole", (0.012, 0.012, 0.012), 0.0, 0.8, pattern='rubber', scale=34, bump=0.5,
                                dirt=0.5, coord='UV')
    L['glove'] = make_pbr("M_Glove_Leather", (0.02, 0.019, 0.018), 0.0, 0.6, wear=(0.09, 0.08, 0.07), wear_amount=0.5,
                          wear_rough=0.4, pattern='leather', scale=36, bump=0.3, dirt=0.4, coord='UV')
    L['metal_hw'] = make_pbr("M_Hardware_Metal", (0.05, 0.05, 0.055), 1.0, 0.4, wear=(0.4, 0.4, 0.42), wear_amount=0.55,
                             wear_rough=0.28, pattern='scratch', scale=30, bump=0.05, dirt=0.3, coord='UV')
    L['patch'] = make_pbr("M_Velcro_Patch", (0.02, 0.02, 0.02), 0.0, 0.95, pattern='weave', scale=60, bump=0.5,
                          dirt=0.2, coord='UV')
    L['watch'] = make_pbr("M_Watch_Strap", (0.02, 0.02, 0.022), 0.0, 0.5, pattern='rubber', scale=36, bump=0.2, coord='UV')
    # ---------------- skin / hair / eyes
    L['skin_male'] = make_pbr("M_Skin_Male", skin_male, 0.0, 0.52, pattern='skin', scale=50, bump=0.18, rough_var=0.1,
                              sss=0.18, sss_color=skin_male, dirt=0.05, tint_var=0.1, coord='UV')
    L['skin_female'] = make_pbr("M_Skin_Female", skin_female, 0.0, 0.5, pattern='skin', scale=50, bump=0.12, rough_var=0.1,
                                sss=0.2, sss_color=skin_female, dirt=0.04, tint_var=0.08, coord='UV')
    L['lips_male'] = make_pbr("M_Lips_Male", tuple(c * 0.78 for c in (skin_male[0] * 1.2, skin_male[1] * 0.85, skin_male[2] * 0.9)),
                              0.0, 0.4, sss=0.2, bump=0.05, dirt=0.0, scale=30, coord='UV')
    L['lips_female'] = make_pbr("M_Lips_Female", (0.42, 0.16, 0.13), 0.0, 0.38, sss=0.2, bump=0.05, dirt=0.0, scale=30, coord='UV')
    L['hair_male'] = make_pbr("M_Hair_Male", hair_male, 0.0, 0.42, pattern='hair', scale=30, bump=0.35, dirt=0.0,
                              tint_var=0.5, rough_var=0.12, coord='UV', anisotropic=0.5)
    L['hair_female'] = make_pbr("M_Hair_Female", hair_female, 0.0, 0.38, pattern='hair', scale=30, bump=0.35, dirt=0.0,
                                tint_var=0.5, rough_var=0.12, coord='UV', anisotropic=0.5)
    L['beard'] = make_pbr("M_Beard", (0.015, 0.012, 0.011), 0.0, 0.55, pattern='hair', scale=50, bump=0.5, dirt=0.0,
                          tint_var=0.4, coord='UV')
    L['sclera'] = make_pbr("M_Eye_Sclera", (0.78, 0.74, 0.70), 0.0, 0.18, scale=10, bump=0.0, dirt=0.15, coat=0.6,
                           coord='OBJECT', tint_var=0.1)
    L['iris'] = make_pbr("M_Eye_Iris", (0.075, 0.035, 0.018), 0.0, 0.2, scale=60, bump=0.1, dirt=0.0, coat=0.6,
                         coord='OBJECT', tint_var=0.5)
    L['pupil'] = make_pbr("M_Eye_Pupil", (0.0, 0.0, 0.0), 0.0, 0.1, scale=10, bump=0.0, dirt=0.0, coat=0.8,
                          coord='OBJECT', tint_var=0.0)
    L['mouth'] = make_pbr("M_Mouth", (0.25, 0.06, 0.06), 0.0, 0.4, scale=10, bump=0.0, dirt=0.0, coord='UV')
    L['teeth'] = make_pbr("M_Teeth", (0.75, 0.7, 0.62), 0.0, 0.3, scale=10, bump=0.0, dirt=0.1, coord='UV')
    L['hair_tie'] = make_pbr("M_Hair_Tie", (0.02, 0.02, 0.022), 0.0, 0.6, scale=20, bump=0.2, dirt=0.1, coord='UV')
    return L


def all_materials() -> Sequence[bpy.types.Material]:
    return list(bpy.data.materials)
