import bpy
import bmesh
import os
import requests

def download_texture(url, material_name, texture_name):
    """
    Downloads the texture from the given URL and saves it in the materials/<material_name> folder.
    Returns the local file path of the downloaded texture.
    """
    materials_dir = os.path.join("materials", material_name)
    os.makedirs(materials_dir, exist_ok=True)
    
    local_path = os.path.join(materials_dir, f"{texture_name}.jpg")
    
    if not os.path.exists(local_path):
        response = requests.get(url)
        with open(local_path, "wb") as file:
            file.write(response.content)
    
    return local_path


def create_stage(stage_size=(100, 100), stage_height=0.01):
    """
    Creates a simple stage object in the scene.
    """
    # Create a new plane object
    bpy.ops.mesh.primitive_plane_add(size=1)
    stage = bpy.context.active_object
    
    # Scale the stage to the desired size
    stage.scale = (stage_size[0], stage_size[1], 1)
    
    # Set the stage location to be at the bottom of the scene
    stage.location = (0, 0, stage_height)
    
    # Rename the stage object
    stage.name = "Stage"
    
    # Rescale the UVs based on the inverse of the scale multiplied by 2
    scale_x = stage_size[0]
    scale_y = stage_size[1] 
    
    # Enter edit mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Get the bmesh representation of the stage
    bm = bmesh.from_edit_mesh(stage.data)
    
    # Get the UV layer
    uv_layer = bm.loops.layers.uv.verify()
    
    # Iterate over the faces and rescale the UVs
    for face in bm.faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            uv.x *= scale_x
            uv.y *= scale_y
    
    # Update the mesh and return to object mode
    bmesh.update_edit_mesh(stage.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    return stage


def apply_stage_material(stage, combination):
    """
    Applies the stage material to the given stage object based on the combination settings.
    """
    # Get the stage material settings from the combination
    stage_material = combination.get('stage_material', {})
    material_name = stage_material.get('name', 'DefaultMaterial')

    # Create a new material for the stage
    material = bpy.data.materials.new(name="StageMaterial")

    # Assign the material to the stage object
    stage.data.materials.append(material)

    # Set the material properties based on the combination settings
    material.use_nodes = True
    nodes = material.node_tree.nodes

    # Clear existing nodes
    for node in nodes:
        nodes.remove(node)

    # Create shader nodes
    output = nodes.new(type='ShaderNodeOutputMaterial')
    principled = nodes.new(type='ShaderNodeBsdfPrincipled')

    # Create texture coordinate and mapping nodes
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    mapping = nodes.new(type='ShaderNodeMapping')

    # Connect texture coordinate to mapping
    links = material.node_tree.links
    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

    # Load and connect diffuse texture
    if 'Diffuse' in stage_material['maps']:
        diffuse_url = stage_material['maps']['Diffuse']
        diffuse_path = download_texture(diffuse_url, material_name, "Diffuse")
        diffuse_tex = nodes.new(type='ShaderNodeTexImage')
        diffuse_tex.image = bpy.data.images.load(diffuse_path)
        links.new(mapping.outputs['Vector'], diffuse_tex.inputs['Vector'])
        links.new(diffuse_tex.outputs['Color'], principled.inputs['Base Color'])

    # Load and connect normal texture
    if 'nor_gl' in stage_material['maps']:
        normal_url = stage_material['maps']['nor_gl']
        normal_path = download_texture(normal_url, material_name, "Normal")
        normal_tex = nodes.new(type='ShaderNodeTexImage')
        normal_tex.image = bpy.data.images.load(normal_path)
        normal_map = nodes.new(type='ShaderNodeNormalMap')
        links.new(mapping.outputs['Vector'], normal_tex.inputs['Vector'])
        links.new(normal_tex.outputs['Color'], normal_map.inputs['Color'])
        links.new(normal_map.outputs['Normal'], principled.inputs['Normal'])

    # Load and connect rough_ao texture
    if 'rough_ao' in stage_material['maps']:
        rough_ao_url = stage_material['maps']['rough_ao']
        rough_ao_path = download_texture(rough_ao_url, material_name, "RoughAO")
        rough_ao_tex = nodes.new(type='ShaderNodeTexImage')
        rough_ao_tex.image = bpy.data.images.load(rough_ao_path)
        links.new(mapping.outputs['Vector'], rough_ao_tex.inputs['Vector'])
        links.new(rough_ao_tex.outputs['Color'], principled.inputs['Roughness'])

    # Load and connect AO texture
    if 'AO' in stage_material['maps']:
        ao_url = stage_material['maps']['AO']
        ao_path = download_texture(ao_url, material_name, "AO")
        ao_tex = nodes.new(type='ShaderNodeTexImage')
        ao_tex.image = bpy.data.images.load(ao_path)
        links.new(mapping.outputs['Vector'], ao_tex.inputs['Vector'])
        links.new(ao_tex.outputs['Color'], principled.inputs['Base Color'])

    # Load and connect displacement texture
    if 'Displacement' in stage_material['maps']:
        disp_url = stage_material['maps']['Displacement']
        disp_path = download_texture(disp_url, material_name, "Displacement")
        disp_tex = nodes.new(type='ShaderNodeTexImage')
        disp_tex.image = bpy.data.images.load(disp_path)
        disp_node = nodes.new(type='ShaderNodeDisplacement')
        links.new(mapping.outputs['Vector'], disp_tex.inputs['Vector'])
        links.new(disp_tex.outputs['Color'], disp_node.inputs['Height'])
        links.new(disp_node.outputs['Displacement'], output.inputs['Displacement'])

    # Load and connect roughness texture
    if 'Rough' in stage_material['maps']:
        rough_url = stage_material['maps']['Rough']
        rough_path = download_texture(rough_url, material_name, "Rough")
        rough_tex = nodes.new(type='ShaderNodeTexImage')
        rough_tex.image = bpy.data.images.load(rough_path)
        links.new(mapping.outputs['Vector'], rough_tex.inputs['Vector'])
        links.new(rough_tex.outputs['Color'], principled.inputs['Roughness'])

    # Connect the nodes
    links.new(principled.outputs['BSDF'], output.inputs['Surface'])