"""Tablas de datos de los nodos (categorias, paneles, orden de propiedades, etiquetas de Math, alturas extra).

Solo datos y la funcion category(): sin Qt ni estado. Los colores y el estilo que cambian con
el tema (BG, HEAD, FIELD, RAD...) siguen en main.py, porque themes.py los reasigna alli.
"""

IMGSEL_H = 28.5      # alto del bloque: IMG_TOP + 20 de botones + 5.5 de aire antes del primer menu

SH_IN = {"AmbientOcclusion", "Attribute", "Bevel", "CameraData", "Fresnel", "LayerWeight",
         "LightPath", "ObjectInfo", "ParticleInfo", "PointInfo", "RGB", "TexCoord", "UVMap",
         "Value", "VertexColor", "VolumeInfo", "Wireframe", "Tangent", "NewGeometry",
         "HairInfo", "CurvesInfo", "UVAlongStroke"}
SH_COLOR = {"BrightContrast", "Gamma", "HueSaturation", "Invert", "LightFalloff", "MixRGB",
            "RGBCurve"}
SH_VEC = {"Bump", "Displacement", "Mapping", "Normal", "NormalMap", "VectorCurve",
          "VectorDisplacement", "VectorRotate", "VectorTransform", "VectorMath"}
SH_CONV = {"Blackbody", "Clamp", "ValToRGB", "CombineColor", "CombineRGB", "CombineXYZ", "Math",
           "MapRange", "RGBToBW", "SeparateColor", "SeparateRGB", "SeparateXYZ", "ShaderToRGB",
           "VectorMath", "Wavelength", "FloatCurve", "Mix"}
CO_IN = {"RLayers", "Image", "MovieClip", "Mask", "RGB", "Value", "Time", "TexCoord",
         "BokehImage", "TrackPos", "SceneTime"}
CO_OUT = {"Composite", "Viewer", "SplitViewer", "OutputFile"}
CO_COLOR = {"AlphaOver", "BrightContrast", "ColorBalance", "ColorCorrection", "Curve", "Gamma",
            "HueCorrect", "HueSat", "Invert", "MixRGB", "Mix", "Posterize", "Tonemap", "Zcombine",
            "Exposure", "ConvertColorSpace", "ConvertToDisplay", "ColorToAlpha"}
CO_FILTER = {"Blur", "Bilateralblur", "BokehBlur", "Defocus", "Denoise", "Despeckle", "Dilate",
             "Filter", "Glare", "Inpaint", "Kuwahara", "Pixelate", "SunBeams", "VecBlur",
             "DBlur", "AntiAliasing", "Convolve"}
CO_MATTE = {"BoxMask", "ChannelMatte", "ChromaMatte", "ColorMatte", "ColorSpill", "DiffMatte",
            "DistanceMatte", "DoubleEdgeMask", "EllipseMask", "KeyingScreen", "Keying",
            "LumaMatte", "Cryptomatte", "CryptomatteV2"}
CO_DIST = {"Crop", "Displace", "Flip", "LensDist", "MapUV", "MovieDistortion",
           "PlaneTrackDeform", "Rotate", "Scale", "Stabilize2D", "Transform", "Translate",
           "CornerPin"}
CO_VEC = {"Normal", "Normalize", "MapValue", "CurveVec"}
# nodos compartidos (Function/Geometry) que Blender 5.x tambien ofrece en el compositor y son de entrada
CO_SHARED_IN = {"FunctionNodeInputBool", "FunctionNodeInputInt", "FunctionNodeInputIntVector",
                "FunctionNodeInputMenu", "FunctionNodeInputRotation", "FunctionNodeInputString",
                "FunctionNodeInputVector", "FunctionNodeInputSpecialCharacters", "GeometryNodeInputFont",
                "GeometryNodeInputObject", "GeometryNodeInputActiveCamera", "GeometryNodeCameraInfo",
                "GeometryNodeObjectInfo"}


def category(idname, mode):
    if mode == "shader":
        n = idname.replace("ShaderNode", "")
        if n.startswith("Output"):
            return "output_node"
        if n.startswith("Tex") and n not in SH_IN:   # TexCoord empieza por "Tex" pero es un nodo de entrada
            return "texture_node"
        for s, c in ((SH_IN, "input_node"), (SH_COLOR, "color_node"), (SH_VEC, "vector_node"),
                     (SH_CONV, "converter_node")):
            if n in s:
                return c
        return "shader_node"
    if not idname.startswith("CompositorNode"):   # nodos compartidos que Blender tambien ofrece en el compositor
        if idname.startswith("ShaderNode"):
            c = category(idname, "shader")
            return "converter_node" if c == "shader_node" else c
        if idname in CO_SHARED_IN:
            return "input_node"
        if idname in ("NodeGroupInput", "NodeGroupOutput"):
            return "group_socket_node"
        if idname == "GeometryNodeWarning":
            return "output_node"
        return "converter_node"
    n = idname.replace("CompositorNode", "")
    for s, c in ((CO_OUT, "output_node"), (CO_IN, "input_node"), (CO_COLOR, "color_node"),
                 (CO_FILTER, "filter_node"), (CO_MATTE, "matte_node"), (CO_DIST, "distor_node"),
                 (CO_VEC, "vector_node")):
        if n in s:
            return c
    if "Matte" in n or "Mask" in n:
        return "matte_node"
    return "converter_node"


# Paneles plegables (Blender no los expone por API; se agrupan por el nombre de los sockets)
PANELS = {
    "ShaderNodeBsdfPrincipled": [
        ("Diffuse", ["Diffuse Roughness"]),
        ("Subsurface", ["Subsurface Weight", "Subsurface Radius", "Subsurface Scale",
                        "Subsurface IOR", "Subsurface Anisotropy"]),
        ("Specular", ["Specular IOR Level", "Specular Tint", "Anisotropic",
                      "Anisotropic Rotation", "Tangent"]),
        ("Transmission", ["Transmission Weight"]),
        ("Coat", ["Coat Weight", "Coat Roughness", "Coat IOR", "Coat Tint", "Coat Normal"]),
        ("Sheen", ["Sheen Weight", "Sheen Roughness", "Sheen Tint"]),
        ("Emission", ["Emission Color", "Emission Strength"]),
        ("Thin Film", ["Thin Film Thickness", "Thin Film IOR"]),
    ],
    "ShaderNodeBsdfGlass": [("Thin Film", ["Thin Film Thickness", "Thin Film IOR"])],
    "CompositorNodeGlare": [
        ("Highlights", ["Threshold", "Smoothness", "Clamp", "Maximum"]),
        ("Adjust", ["Strength", "Saturation", "Tint"]),
        ("Glare", ["Size", "Streaks", "Streaks Angle", "Iterations", "Fade", "Color Modulation",
                   "Diagonal", "Sun Position", "Jitter", "Kernel Data Type", "Kernel"]),
    ],
    "ShaderNodeBsdfMetallic": [("Thin Film", ["Thin Film Thickness", "Thin Film IOR"])],
    "ShaderNodeVolumeCoefficients": [
        ("Absorption", ["Absorption Coefficients"]),
        ("Scatter", ["Scatter Coefficients", "Anisotropy"]),
        ("Emission", ["Emission Coefficients"]),
    ],
}
# menus que en Blender viven dentro de un panel (propiedad -> panel)
PROP_PANEL = {"ShaderNodeBsdfPrincipled": {"distribution": "Specular",
                                             "subsurface_method": "Subsurface"}}

SKIP_PROPS = {"is_active_output", "use_custom_color"}
# Render Layers (medido en capturas de Blender): aire antes de la fila Scene, paso de cada fila y valor por defecto
PROPS_TOP = {"CompositorNodeRLayers": 3.7}
RL_PITCH = {"scene": 24.1, "layer": 20.0}
CPANEL_BOX = 20.0   # x (desde el margen) de la casilla de un subpanel con checkbox (Glare > Clamp)
PROP_DEFAULTS = {("CompositorNodeRLayers", "scene"): "Scene"}
PREVIEW_ICON = {"CompositorNodeRLayers", "CompositorNodeFilter"}   # nodos con el icono de vista previa (ojo cerrado) en la cabecera
PROP_PANEL["ShaderNodeVolumeCoefficients"] = {"phase": "Scatter"}
# nodos cuyos paneles vienen abiertos por defecto (como en el PDF)
OPEN_DEFAULT = {"ShaderNodeVolumeCoefficients", "CompositorNodeGlare"}
# nodos que dibujan sus propiedades (casillas/menus) ANTES de las salidas
PROPS_FIRST = {"ShaderNodeRaycast", "ShaderNodeVectorRotate"}
# la primera entrada comparte fila con la salida; valor = mostrar tambien el nombre de la salida
IO_MERGE = {"ShaderNodeGamma": True, "ShaderNodeVectorRotate": False, "CompositorNodeKuwahara": False,
            "CompositorNodeGlare": False, "CompositorNodeLensdist": False, "CompositorNodeFilter": False}
# sockets de tipo menu que Blender dibuja como desplegable: (nodo, socket) -> opciones (id = nombre)
MENU_ITEMS = {("CompositorNodeKuwahara", "Type"): [{"id": "Classic", "name": "Classic"},
                                                    {"id": "Anisotropic", "name": "Anisotropic"}]}
# Glare: Type, Quality y Kernel Data Type son menus en Blender (el JSON los trae como sockets MENU sin opciones)
MENU_ITEMS.update({
    ("CompositorNodeGlare", "Type"): [{"id": n, "name": n} for n in
                                      ("Bloom", "Ghosts", "Streaks", "Fog Glow", "Simple Star", "Sun Beams", "Kernel")],
    ("CompositorNodeGlare", "Quality"): [{"id": n, "name": n} for n in ("High", "Medium", "Low")],
    ("CompositorNodeGlare", "Kernel Data Type"): [{"id": n, "name": n} for n in ("Float", "Color")],
    # Lens Distortion: Type es un menu (opciones segun mi recuerdo de Blender 5.x, sin verificar)
    ("CompositorNodeLensdist", "Type"): [{"id": n, "name": n} for n in ("Radial", "Horizontal")],
    # Filter: nombres de Blender 4.x/5.x segun mi recuerdo, sin verificar
    ("CompositorNodeFilter", "Type"): [{"id": n, "name": n} for n in
                                       ("Soften", "Box Sharpen", "Diamond Sharpen", "Laplace", "Sobel",
                                        "Prewitt", "Kirsch", "Shadow")],
})
# panel plegable sin sockets al final del nodo
TRAILING_PANELS = {"ShaderNodeRaycast": "Attributes"}
# Mix: que menus/casillas se ven segun el tipo de dato (como en Blender 5.2)
MIX_ORDER = {"FLOAT": ["data_type", "clamp_factor"],
             "VECTOR": ["data_type", "factor_mode", "clamp_factor"],
             "RGBA": ["data_type", "blend_type", "clamp_result", "clamp_factor"],
             "ROTATION": ["data_type"]}
MIX_SFX = {"FLOAT": "Float", "VECTOR": "Vector", "RGBA": "Color", "ROTATION": "Rotation"}
# Math / Vector Math: cuantas entradas y que etiquetas segun la operacion
MATH_1 = {"SQRT", "INVERSE_SQRT", "ABSOLUTE", "EXPONENT", "SIGN", "ROUND", "FLOOR", "CEIL", "TRUNC",
          "FRACT", "SINE", "COSINE", "TANGENT", "ARCSINE", "ARCCOSINE", "ARCTANGENT", "SINH",
          "COSH", "TANH", "RADIANS", "DEGREES"}
MATH_3 = {"MULTIPLY_ADD", "COMPARE", "SMOOTH_MIN", "SMOOTH_MAX", "WRAP"}
MATH_LABELS = {"POWER": ["Base", "Exponent", "Value"], "LOGARITHM": ["Value", "Base", "Value"],
               "MULTIPLY_ADD": ["Value", "Multiplier", "Addend"],
               "COMPARE": ["Value", "Value", "Epsilon"],
               "SMOOTH_MIN": ["Value", "Value", "Distance"],
               "SMOOTH_MAX": ["Value", "Value", "Distance"],
               "WRAP": ["Value", "Max", "Min"], "SNAP": ["Value", "Increment", "Value"],
               "PINGPONG": ["Value", "Scale", "Value"]}
VM_1 = {"NORMALIZE", "LENGTH", "ABSOLUTE", "SIGN", "ROUND", "FLOOR", "CEIL", "FRACTION", "SINE",
        "COSINE", "TANGENT"}
VM_3 = {"MULTIPLY_ADD", "FACEFORWARD", "WRAP"}
VM_VAL = {"LENGTH", "DISTANCE", "DOT_PRODUCT"}
VM_LABELS = {"MULTIPLY_ADD": ["Vector", "Multiplier", "Addend"],
             "FACEFORWARD": ["Vector", "Incident", "Reference"],
             "WRAP": ["Vector", "Max", "Min"], "SNAP": ["Vector", "Increment", "Vector"],
             "REFLECT": ["Vector", "Normal", "Vector"], "REFRACT": ["Vector", "Normal", "Vector"]}

# propiedades dibujadas en el cuerpo del nodo (orden y ajustes tal como en Blender 5.2)
PROP_ORDER = {
    "ShaderNodeAmbientOcclusion": ["samples", "inside", "only_local"],
    "ShaderNodeBevel": ["samples"],
    "ShaderNodeTexMagic": ["turbulence_depth"],
    "ShaderNodeTexBrick": ["offset", "offset_frequency", "squash", "squash_frequency"],
    "ShaderNodeTexSky": ["sky_type", "_warn", "sun_disc", "sun_size", "sun_intensity",
                         "sun_elevation", "sun_rotation", "altitude", "air_density",
                         "aerosol_density", "ozone_density"],
    "ShaderNodeAttribute": ["attribute_type", "attribute_name"],
    "ShaderNodeUVMap": ["from_instancer", "uv_map"],
    "ShaderNodeVertexColor": ["layer_name"],
    "ShaderNodeNormalMap": ["space", "convention", "base", "uv_map"],
    "ShaderNodeTexIES": ["mode", "ies"],
    "ShaderNodeTexCoord": ["object", "from_instancer"],
    "ShaderNodeTangent": ["direction_type", "axis"],
    "ShaderNodeVectorTransform": ["vector_type", "convert_from", "convert_to"],
    "ShaderNodeTexEnvironment": ["interpolation", "projection"],
    "ShaderNodeOutputAOV": ["aov_name"],
    "ShaderNodeMapping": ["vector_type"],
    "ShaderNodeMapRange": ["data_type", "interpolation_type", "clamp"],
    "ShaderNodeVectorRotate": ["rotation_type", "invert"],
    "ShaderNodeTexImage": ["interpolation", "projection", "projection_blend", "extension"],
    "ShaderNodeTexEnvironment": ["interpolation", "projection"],
    "ShaderNodeTexVoronoi": ["voronoi_dimensions", "feature", "distance", "normalize"],
    "CompositorNodeDefocus": ["_lbl", "bokeh", "angle", "f_stop", "blur_max", "scene",
                              "use_zbuffer", "z_scale"],
    "CompositorNodeCryptomatte": ["_lbl", "_pick", "matte_id"],
    "CompositorNodeOutputFile": ["directory", "save_as_render", "use_file_extension"],
    "CompositorNodeRLayers": ["scene", "layer"],
}
PROP_EXTRA = {
    "ShaderNodeAmbientOcclusion": {"samples": {"name": "Samples"}},
    "ShaderNodeBevel": {"samples": {"name": "Samples"}},
    "ShaderNodeTexMagic": {"turbulence_depth": {"name": "Depth"}},
    "ShaderNodeTexBrick": {"offset": {"name": "Offset", "fac": True, "lo": 0.0, "hi": 1.0},
                           "offset_frequency": {"name": "Frequency"},
                           "squash": {"name": "Squash"},
                           "squash_frequency": {"name": "Frequency"}},
    "ShaderNodeTexSky": {"_warn": {"name": "Sun disc not available"},
                         "sun_size": {"name": "Sun Size", "unit": "deg"},
                         "sun_intensity": {"name": "Sun Intensity"},
                         "sun_elevation": {"name": "Sun Elevation", "unit": "deg"},
                         "sun_rotation": {"name": "Sun Rotation", "unit": "deg"},
                         "altitude": {"name": "Altitude", "unit": "m"},
                         "air_density": {"name": "Air"},
                         "aerosol_density": {"name": "Aerosols"},
                         "ozone_density": {"name": "Ozone"}},
    "ShaderNodeAttribute": {"attribute_name": {"name": "Name", "ph": "Name"}},
    "ShaderNodeUVMap": {"uv_map": {"name": "UV Map", "icon": "uvmap"}},
    "ShaderNodeVertexColor": {"layer_name": {"name": "Color", "icon": "uv"}},
    "ShaderNodeNormalMap": {"uv_map": {"name": "UV Map", "icon": "uvmap"}},
    "ShaderNodeTexIES": {"mode": {"seg": True}, "ies": {"name": "Text", "ph": "Text", "icon": "uv"}},
    "ShaderNodeTexCoord": {"object": {"name": "Object", "ph": "Object", "icon": "obj"}},
    "ShaderNodeTangent": {"axis": {"seg": True}},
    "ShaderNodeVectorTransform": {"vector_type": {"seg": True}},
    "ShaderNodeOutputAOV": {"aov_name": {"name": "", "ph": "", "icon": "circle"}},
    "ShaderNodeMapping": {"vector_type": {"inline": True}},
    "ShaderNodeVectorRotate": {"rotation_type": {"inline": True}},
    "ShaderNodeTexImage": {"projection_blend": {"name": "Blend", "fac": True, "lo": 0.0, "hi": 1.0}},
    "CompositorNodeDefocus": {"_lbl": {"type": "LABEL", "name": "Bokeh Type:"},
                              "angle": {"name": "Angle", "unit": "deg"},
                              "f_stop": {"name": "F-Stop"},
                              "blur_max": {"name": "Max Blur"},
                              "scene": {"name": "Scene", "ph": "Scene", "icon": "uv"},
                              "z_scale": {"name": "Z-Scale"}},
    "CompositorNodeCryptomatte": {"_lbl": {"type": "LABEL", "name": "Matte Objects:"},
                                  "_pick": {"type": "PICK"},
                                  "matte_id": {"name": "Matte ID", "ph": ""}},
    "CompositorNodeOutputFile": {"directory": {"name": "Directory", "ph": "Directory"}},
    "CompositorNodeRLayers": {"scene": {"name": "Scene", "ph": "Scene", "rl": "scene"},
                              "layer": {"name": "Layer", "rl": "layer",
                                        "items": [{"id": "ViewLayer", "name": "ViewLayer"}]}},
}

# widgets dibujados como bloque justo despues de las salidas: idname -> (tipo, alto extra)
BLOCKS = {"ShaderNodeRGB": ("wheel", 98), "ShaderNodeRGBCurve": ("curve_rgb", 188),
          "ShaderNodeFloatCurve": ("curve", 188), "ShaderNodeVectorCurve": ("curve_xyz", 184),
          "ShaderNodeValToRGB": ("ramp", 110), "ShaderNodeTexImage": ("imgsel", IMGSEL_H),
          "ShaderNodeGroup": ("groupsel", 22), "ShaderNodeNormal": ("spheres", 127),
          "ShaderNodeTexEnvironment": ("imgsel", IMGSEL_H)}
# alto extra (real de Blender 5.2 menos el de la app) de nodos con widgets aun sin dibujar
EXTRA_H = {"ShaderNodeVolumeCoefficients": 21.3,
           "ShaderNodeGamma": -2.2,
           "ShaderNodeVectorRotate": 0.8,
           "ShaderNodeRaycast": 0.8,
           "ShaderNodeOutputAOV": -2.2,
           "ShaderNodeTexCoord": 7.8,
           "ShaderNodeTexSky": 25.3,
           "ShaderNodeAttribute": 3.3,
           "ShaderNodeAmbientOcclusion": 5.8,
           "ShaderNodeNormalMap": -3.2,
           "ShaderNodeTexIES": 0.8,
           "ShaderNodeUVMap": 4.8,
           "ShaderNodeVertexColor": 3.8,
           "ShaderNodeTangent": -2.7,
           "ShaderNodeTexMagic": 2.8,
           "ShaderNodeBevel": 2.3,
           "ShaderNodeBsdfGlass": -5.2,
           "ShaderNodeBsdfMetallic": -5.7,
           "ShaderNodeBsdfPrincipled": -1.1,
           "ShaderNodeMath": -1.5,
           "ShaderNodeTexEnvironment": 0.0,
           "ShaderNodeTexImage": 0.0,
           "ShaderNodeVectorCurve": 5.3,
           "ShaderNodeVectorTransform": -5.2,
           "ShaderNodeBsdfDiffuse": 2.3,
           "ShaderNodeBsdfTranslucent": 2.3,
           "ShaderNodeClamp": -3.2,
           "ShaderNodeCombineColor": -3.2,
           "ShaderNodeDisplacement": -2.2,
           "ShaderNodeEeveeSpecular": 3.3,
           "ShaderNodeMapping": 0.8,
           "ShaderNodeOutputMaterial": -2.7,
           "ShaderNodeRadialTiling": 2.3,
           "ShaderNodeSeparateColor": -2.2,
           "ShaderNodeSeparateXYZ": 1.3,
           "ShaderNodeSubsurfaceScattering": 0.8,
           "ShaderNodeTexVoronoi": -2.7,
           "ShaderNodeTexWave": -4.7,
           "ShaderNodeVectorDisplacement": -2.2,
           "ShaderNodeVectorMath": 0.8,
           "ShaderNodeAddShader": 1.3,
           "ShaderNodeBsdfTransparent": 1.3,
           "ShaderNodeBump": 1.8,
           "ShaderNodeEmission": 1.3,
           "ShaderNodeMapRange": -1.2,
           "ShaderNodeMixShader": 1.3,
           "ShaderNodeNormal": -1.2,
           "ShaderNodeRGB": 1.8,
           "ShaderNodeTexBrick": 9.8,
           "ShaderNodeTexGradient": -1.7,
           "ShaderNodeTexNoise": -1.7,
           "ShaderNodeValToRGB": -1.2,
           "ShaderNodeVolumeAbsorption": 1.3,
           "ShaderNodeVolumePrincipled": 1.3,
           "ShaderNodeVolumeScatter": -1.2,
           "CompositorNodeDefocus": 8.3,
           "CompositorNodeCryptomatte": -0.7,
           "CompositorNodeOutputFile": -2.2,
           "CompositorNodeRLayers": 3.0,
           "FunctionNodeInputBool": -27.2,
           "FunctionNodeInputVector": 36.3,
           "GeometryNodeMenuSwitch": -27.2,
           "GeometryNodeRepeatInput": 16.3,
           "GeometryNodeRepeatOutput": 15.8,
           "NodeClosureInput": 17.8,
           "NodeClosureOutput": -2.2,
           "NodeCombineBundle": -7.2,
           "NodeEvaluateClosure": 41.3,
           "NodeJoinBundle": -26.7,
           "NodeSeparateBundle": -1.7}


# Glare: sockets activos segun el Type (verificado en Blender 5.2.0 LTS). "Maximum" vive dentro del
# subpanel plegado de Clamp, asi que de momento no se dibuja.
_GLARE_COMMON = {"Quality", "Threshold", "Smoothness", "Clamp", "Strength", "Saturation", "Tint"}
GLARE_SOCKS = {
    "bloom": _GLARE_COMMON | {"Size"},
    "fog glow": _GLARE_COMMON | {"Size"},
    "streaks": _GLARE_COMMON | {"Streaks", "Streaks Angle", "Iterations", "Fade", "Color Modulation"},
    "simple star": _GLARE_COMMON | {"Iterations", "Fade", "Diagonal"},
    "ghosts": _GLARE_COMMON | {"Iterations", "Color Modulation"},
    "sun beams": _GLARE_COMMON | {"Size", "Sun Position", "Jitter"},
    "kernel": _GLARE_COMMON | {"Kernel Data Type", "Kernel"},
}
