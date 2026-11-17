# Read-only: list Nubis fur/skin material node setups. Never saves.
import bpy
for o in bpy.data.objects:
    if o.type in ("MESH", "CURVES"):
        print("OBJ", o.name, o.type, [s.material.name if s.material else None for s in o.material_slots])
for m in bpy.data.materials:
    if not m.use_nodes: continue
    print("MAT", m.name, "users", m.users)
    for n in m.node_tree.nodes:
        extra = ""
        if n.type == "TEX_IMAGE" and n.image: extra = n.image.name
        if n.type == "ATTRIBUTE": extra = n.attribute_name
        print("   NODE", n.bl_idname, n.name, extra)
    for l in m.node_tree.links:
        print("   LINK", l.from_node.name, l.from_socket.identifier, "->", l.to_node.name, l.to_socket.identifier)
fur = bpy.data.objects.get("Nubis Fur")
if fur:
    for md in fur.modifiers:
        print("FURMOD", md.name, md.type, md.node_group.name if md.node_group else None)
