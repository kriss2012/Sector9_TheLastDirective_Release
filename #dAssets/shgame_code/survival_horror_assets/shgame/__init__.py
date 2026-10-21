"""shgame - procedural survival-horror asset generator for Blender (bpy).

Modules
-------
config       build configuration + character/weapon dimension tables
utils        scene helpers, MeshBuilder (bmesh wrapper with skin-weight support), loft, UV
materials    procedural PBR material library (node based)
skeleton     bone table (shared by mesh weighting and armature creation)
weapons      pistol, machine-gun (carbine), kukri (+ karda/chakmak, sheath)
character    male / female body, head, hair, clothing, gear
rig          armature creation, vertex groups finalisation, sockets
animations   idle / walk / run / crouch / sit / aim / fire / reload actions
camera_rig   third-person camera rig
bake         procedural -> image-texture baking (for glTF)
export       .blend and .glb export
validate     post-build validation report
"""
__version__ = "1.0.0"
