import logging
import math

import bpy
from mathutils import Vector

import numpy as np
from scipy.spatial.transform import Rotation as R

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def rotate_points(points, angles):
    """Rotate points by given angles in degrees for (x, y, z) rotations."""
    rotation = R.from_euler("xyz", angles, degrees=True)
    return np.array([rotation.apply(point) for point in points])


def compute_camera_distance(points, fov_deg):
    """Calculate the camera distance required to frame the bounding sphere of the points."""
    # Calculate the center of the bounding sphere (use the centroid for simplicity)
    centroid = np.mean(points, axis=0)
    # Calculate the radius as the max distance from the centroid to any point
    radius = np.max(np.linalg.norm(points - centroid, axis=1))
    # Calculate the camera distance using the radius and the field of view
    fov_rad = math.radians(fov_deg)
    distance = radius / math.tan(fov_rad / 2)
    return distance, centroid, radius


def perspective_project(points, camera_distance, fov_deg, aspect_ratio=1.0):
    """Project points onto a 2D plane using a perspective projection considering the aspect ratio."""
    screen_points = []
    fov_rad = math.radians(fov_deg)
    f = 1.0 / math.tan(fov_rad / 2)
    for point in points:
        # Translate point to camera's frame of reference (camera along the positive x-axis)
        p_cam = np.array([camera_distance - point[0], point[1], point[2]])
        # Apply perspective projection if the point is in front of the camera
        if p_cam[0] > 0:
            x = (p_cam[1] * f) / (p_cam[0] * aspect_ratio)  # Adjust x by aspect ratio
            y = p_cam[2] * f / p_cam[0]
            # Normalize to range [0, 1] for OpenGL screen space
            screen_x = (x + 1) / 2
            screen_y = (y + 1) / 2
            screen_points.append((screen_x, screen_y))
    return np.array(screen_points)


def create_camera_rig() -> bpy.types.Object:
    """
    Creates a camera rig consisting of multiple objects in Blender.

    Returns:
        dict: A dictionary containing the created objects:
            - camera_animation_root: The root object of the camera animation hierarchy.
            - camera_orientation_pivot_yaw: The yaw pivot object for camera orientation.
            - camera_orientation_pivot_pitch: The pitch pivot object for camera orientation.
            - camera_framing_pivot: The pivot object for camera framing.
            - camera_animation_pivot: The pivot object for camera animation.
            - camera_object: The camera object.
            - camera: The camera data.
    """
    camera_animation_root = bpy.data.objects.new("CameraAnimationRoot", None)
    bpy.context.scene.collection.objects.link(camera_animation_root)

    camera_orientation_pivot_yaw = bpy.data.objects.new(
        "CameraOrientationPivotYaw", None
    )
    camera_orientation_pivot_yaw.parent = camera_animation_root
    bpy.context.scene.collection.objects.link(camera_orientation_pivot_yaw)

    camera_orientation_pivot_pitch = bpy.data.objects.new(
        "CameraOrientationPivotPitch", None
    )
    camera_orientation_pivot_pitch.parent = camera_orientation_pivot_yaw
    bpy.context.scene.collection.objects.link(camera_orientation_pivot_pitch)

    camera_framing_pivot = bpy.data.objects.new("CameraFramingPivot", None)
    camera_framing_pivot.parent = camera_orientation_pivot_pitch
    bpy.context.scene.collection.objects.link(camera_framing_pivot)

    camera_animation_pivot = bpy.data.objects.new("CameraAnimationPivot", None)
    camera_animation_pivot.parent = camera_framing_pivot
    bpy.context.scene.collection.objects.link(camera_animation_pivot)

    camera = bpy.data.cameras.new("Camera")
    camera_object = bpy.data.objects.new("Camera", camera)

    # Rotate the Camera 90º
    camera_object.delta_rotation_euler = [1.5708, 0, 1.5708]
    camera_object.data.lens_unit = "FOV"

    camera_object.parent = camera_animation_pivot
    bpy.context.scene.collection.objects.link(camera_object)

    bpy.context.scene.camera = camera_object

     # Add camera follow object
    camera_follow = bpy.data.objects.new("CameraFollow", None)
    camera_follow.parent = camera_animation_root
    bpy.context.scene.collection.objects.link(camera_follow)

    return {
        "camera_animation_root": camera_animation_root,
        "camera_orientation_pivot_yaw": camera_orientation_pivot_yaw,
        "camera_orientation_pivot_pitch": camera_orientation_pivot_pitch,
        "camera_framing_pivot": camera_framing_pivot,
        "camera_animation_pivot": camera_animation_pivot,
        "camera_object": camera_object,
        "camera": camera,
        "camera_follow": camera_follow,
    }


def update_camera_follow(combination: dict) -> None:
    """
    Update the camera position to follow the specified object.

    Args:
        combination (dict): A dictionary containing camera follow information.
    """
    follow_data = combination.get("camera_follow", {})
    if follow_data:
        for obj_name, follow in follow_data.items():
            if follow.get("follow"):
                obj = bpy.data.objects.get(obj_name)
                if obj:
                    camera_follow = bpy.data.objects.get("CameraFollow")
                    if camera_follow:
                        constraint = camera_follow.constraints.new(type='CHILD_OF')
                        constraint.target = obj
                        logger.info(f"Camera will follow {obj_name}")
                        return
                else:
                    logger.warning(f"Object {obj_name} not found for camera follow")
    else:
        logger.info("No camera follow data found in combination")


def set_camera_settings(combination: dict) -> None:
    """
    Applies camera settings from a combination to the Blender scene.

    This function updates various camera settings including orientation, pivot adjustments, and
    framing based on the provided combination dictionary.

    Args:
        combination (dict): A dictionary containing camera settings including 'fov', 'animation',
                            and orientation details.
    Returns:
        None
    """
    camera = bpy.context.scene.objects["Camera"]
    camera_data = camera.data

    postprocessing = combination.get("postprocessing", {})

    # Apply bloom settings
    bloom_settings = postprocessing.get("bloom", {})
    threshold = bloom_settings.get("threshold", 0.8)
    intensity = bloom_settings.get("intensity", 0.5)
    radius = bloom_settings.get("radius", 5.0)
    bpy.context.scene.eevee.use_bloom = True
    bpy.context.scene.eevee.bloom_threshold = threshold
    bpy.context.scene.eevee.bloom_intensity = intensity
    bpy.context.scene.eevee.bloom_radius = radius

    # Apply SSAO settings
    ssao_settings = postprocessing.get("ssao", {})
    distance = ssao_settings.get("distance", 0.2)
    factor = ssao_settings.get("factor", 0.5)
    bpy.context.scene.eevee.use_gtao = True
    bpy.context.scene.eevee.gtao_distance = distance
    bpy.context.scene.eevee.gtao_factor = factor

    # Apply SSRR settings
    ssrr_settings = postprocessing.get("ssrr", {})
    max_roughness = ssrr_settings.get("max_roughness", 0.5)
    thickness = ssrr_settings.get("thickness", 0.1)
    bpy.context.scene.eevee.use_ssr = True
    bpy.context.scene.eevee.use_ssr_refraction = True
    bpy.context.scene.eevee.ssr_max_roughness = max_roughness
    bpy.context.scene.eevee.ssr_thickness = thickness

    # Apply motion blur settings
    motionblur_settings = postprocessing.get("motionblur", {})
    shutter_speed = motionblur_settings.get("shutter_speed", 0.5)
    bpy.context.scene.eevee.use_motion_blur = True
    bpy.context.scene.eevee.motion_blur_shutter = shutter_speed

    # Get the initial lens value from the combination
    initial_lens = combination["framing"]["fov"]

    # Get the first keyframe's angle_offset value, if available
    animation = combination["animation"]
    keyframes = animation["keyframes"]
    if (
        keyframes
        and "Camera" in keyframes[0]
        and "angle_offset" in keyframes[0]["Camera"]
    ):
        angle_offset = keyframes[0]["Camera"]["angle_offset"]
        camera_data.angle = math.radians(initial_lens + angle_offset)
    else:
        camera_data.angle = math.radians(initial_lens)

    orientation_data = combination["orientation"]
    orientation = {"pitch": orientation_data["pitch"], "yaw": orientation_data["yaw"]}

    # Rotate CameraOrientationPivotYaw by the Y
    camera_orientation_pivot_yaw = bpy.data.objects.get("CameraOrientationPivotYaw")
    camera_orientation_pivot_yaw.rotation_euler[2] = orientation["yaw"] * math.pi / 180

    # Rotate CameraOrientationPivotPitch by the X
    camera_orientation_pivot_pitch = bpy.data.objects.get("CameraOrientationPivotPitch")
    camera_orientation_pivot_pitch.rotation_euler[1] = (
        orientation["pitch"] * -math.pi / 180
    )

    # set the camera framerate to 30
    bpy.context.scene.render.fps = 30


def set_camera_animation(combination: dict, animation_length: int) -> None:
    """
    Applies the specified animation to the camera based on the keyframes from the camera_data.json file.
    The total animation frames are fixed to ensure consistent speed.

    Args:
        combination (dict): The combination dictionary containing animation data.
        animation_length (int): Total number of frames for the entire animation.

    Returns:
        None
    """
    animation = combination["animation"]
    speed_factor = animation.get("speed_factor", 1)
    keyframes = animation["keyframes"]
    frame_interval = animation_length

    for i, keyframe in enumerate(keyframes):
        for obj_name, transforms in keyframe.items():
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                raise ValueError(f"Object {obj_name} not found in the scene")
            frame = int(i * frame_interval)
            for transform_name, value in transforms.items():
                if transform_name == "position":
                    obj.location = [coord * speed_factor for coord in value]
                    obj.keyframe_insert(data_path="location", frame=frame)
                elif transform_name == "rotation":
                    obj.rotation_euler = [
                        math.radians(angle * speed_factor) for angle in value
                    ]
                    obj.keyframe_insert(data_path="rotation_euler", frame=frame)
                elif transform_name == "scale":
                    obj.scale = [coord * speed_factor for coord in value]
                    obj.keyframe_insert(data_path="scale", frame=frame)
                elif transform_name == "angle_offset" and obj_name == "Camera":
                    camera_data = bpy.data.objects["Camera"].data
                    camera_data.angle = math.radians(
                        combination["framing"]["fov"] + value
                    )
                    camera_data.keyframe_insert(data_path="lens", frame=frame)

    bpy.context.scene.frame_set(0)


def position_camera(combination: dict, focus_object: bpy.types.Object) -> None:
    """
    Positions the camera based on the coverage factor and lens values.

    Args:
        combination (dict): The combination dictionary containing coverage factor and lens values.

    Returns:
        None
    """
    camera = bpy.context.scene.objects["Camera"]

    # Get the bounding box of the focus object in world space
    bpy.context.view_layer.update()
    
    bbox = [
        focus_object.matrix_world @ Vector(corner) for corner in focus_object.bound_box
    ]
    bbox_points = np.array([corner.to_tuple() for corner in bbox])

    # Rotate points as per the desired view angle if any
    # Assuming we want to compute this based on some predefined rotation angles
    rotation_angles = (45, 45, 45)  # Example rotation angles
    rotated_points = rotate_points(bbox_points, rotation_angles)

    # scale rotated_points by combination["framing"]["coverage_factor"]
    rotated_points *= combination["framing"]["coverage_factor"]

    # Calculate the camera distance to frame the rotated bounding box correctly
    fov_deg = combination["framing"][
        "fov"
    ]  # Get the FOV from combination or default to 45
    aspect_ratio = (
        bpy.context.scene.render.resolution_x / bpy.context.scene.render.resolution_y
    )

    camera_distance, centroid, radius = compute_camera_distance(
        rotated_points, fov_deg / aspect_ratio
    )

    # Set the camera properties
    camera.data.angle = math.radians(fov_deg)  # Set camera FOV
    if aspect_ratio >= 1:
        camera.data.sensor_fit = "HORIZONTAL"
    else:
        camera.data.sensor_fit = "VERTICAL"

    bbox = [
        focus_object.matrix_world @ Vector(corner) for corner in focus_object.bound_box
    ]
    bbox_min = min(bbox, key=lambda v: v.z)
    bbox_max = max(bbox, key=lambda v: v.z)

    # Calculate the height of the bounding box
    bbox_height = bbox_max.z - bbox_min.z

    # Position the camera based on the computed distance
    camera.location = Vector((camera_distance, 0, 0))  # Adjust this as needed


    # Set the position of the CameraAnimationRoot object to slightly above the focus object center, quasi-rule of thirds
    # bbox_height / 2 is the center of the bounding box, bbox_height / 1.66 is more aesthetically pleasing
    bpy.data.objects["CameraAnimationRoot"].location = focus_object.location + Vector(
        (0, 0, bbox_height/2)
    )

