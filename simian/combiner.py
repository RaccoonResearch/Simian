import logging
import json
import math
import os
import random
import argparse
from typing import Any, Dict, List, Optional
from mathutils import Vector

from .transform import determine_relationships, adjust_positions

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    Read a JSON file and return the data as a dictionary.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Dict[str, Any]: Data from the JSON file.
    """
    with open(file_path, "r") as file:
        return json.load(file)


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments using argparse.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Generate random camera combinations.")
    parser.add_argument(
        "--count", type=int, default=10, help="Number of combinations to generate"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Seed for the random number generator"
    )
    parser.add_argument(
        "--max_number_of_objects",
        type=int,
        default=5,
        help="Maximum number of objects to randomly select",
    )
    parser.add_argument(
        "--camera_file_path",
        type=str,
        default="data/camera_data.json",
        help="Path to the JSON file containing camera data",
    )
    parser.add_argument(
        "--object_data_path",
        type=str,
        default="data/object_data.json",
        help="Path to the JSON file containing object data",
    )
    parser.add_argument(
        "--texture_data_path",
        type=str,
        default="datasets/texture_data.json",
        help="Path to the JSON file containing texture data",
    )
    parser.add_argument(
        "--datasets_path",
        type=str,
        default="data/datasets.json",
        help="Path to the file which lists all the datasets to use",
    )
    parser.add_argument(
        "--cap3d_captions_path",
        type=str,
        default="datasets/cap3d_captions.json",
        help="Path to the JSON file containing captions data",
    )
    parser.add_argument(
        "--simdata_path",
        type=str,
        default="datasets",
        help="Path to the simdata directory",
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="combinations.json",
        help="Path to the output file",
    )
    parser.add_argument(
        "--stage_data_path",
        type=str,
        default="data/stage_data.json",
        help="Path to the JSON file containing stage data",
    )
    parser.add_argument(
        "--movement",
        type=str,
        default="all",
        help="Apply movement to all, none, or random objects."
    )
    parser.add_argument(
        "--ontop",
        type=str,
        default="all",
        help="Allow objects to be on top of each other."
    )
    parser.add_argument(
        "--camera_follow",
        type=str,
        default="all",
        help="Camera will follow specified object as it moves (for individual objects)."
    )
    return parser.parse_args()


def generate_stage_captions(combination: Dict[str, Any]) -> List[str]:
    """
    Generate captions for the stage based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.

    Returns:
        List[str]: List of stage captions.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))

    stage_data_path = os.path.join(current_dir, "../data/stage_data.json")
    stage_data = read_json_file(stage_data_path)

    background_prefix = random.choice(stage_data["background_names"])
    floor_prefix = random.choice(stage_data["material_names"])
    background_name = combination["background"]["name"]
    floor_material_name = combination["stage"]["material"]["name"]

    # remove all numbers and trim
    floor_material_name = "".join(
        [i for i in floor_material_name if not i.isdigit()]
    ).strip()
    background_name = (
        "".join([i for i in background_name if not i.isdigit()])
        .strip()
        .replace("#", "")
        .replace("_", " ")
        .replace("(", "")
        .replace(")", "")
    )
    caption_parts = [
        f"The {background_prefix} is {background_name}.",
        f"The {floor_prefix} is {floor_material_name}.",
    ]
    return caption_parts


def generate_orientation_caption(
    camera_data: Dict[str, Any], combination: Dict[str, Any]
) -> str:
    """
    Generate a caption for the camera orientation based on the combination data.

    Args:
        camera_data (Dict[str, Any]): Camera data.
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: Orientation caption.
    """
    pitch_labels = camera_data["orientation"]["labels"]["pitch"]
    yaw_labels = camera_data["orientation"]["labels"]["yaw"]

    closest_pitch_label = min(
        pitch_labels.keys(),
        key=lambda x: abs(int(x) - int(combination["orientation"]["pitch"])),
    )
    closest_yaw_label = min(
        yaw_labels.keys(),
        key=lambda x: abs(int(x) - int(combination["orientation"]["yaw"])),
    )

    # Replace the placeholders in the camera text with the closest matching labels
    orientation_text = random.choice(camera_data["orientation"]["descriptions"])
    orientation_text = (
        orientation_text.replace(
            "<pitch>", random.choice(pitch_labels[closest_pitch_label])
        )
        .replace("<degrees>", str(combination["orientation"]["pitch"]))
        .replace("<yaw>", random.choice(yaw_labels[closest_yaw_label]))
        .replace("<degrees>", str(combination["orientation"]["yaw"]))
    )

    return orientation_text


def meters_to_feet_rounded(meters: float) -> int:
    """
    Convert meters to feet and round the result.

    Args:
        meters (float): Distance in meters.

    Returns:
        int: Distance in feet (rounded).
    """
    feet_per_meter = 3.28084
    return round(meters * feet_per_meter)


def generate_object_name_description_captions(
    combination: Dict[str, Any], object_data
) -> str:
    """
    Generate captions for object names and descriptions based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: Object name and description captions.
    """
    object_name_descriptions = []
    for obj in combination["objects"]:
        object_name = obj["name"]
        object_description = obj["description"]

        object_scale = obj["scale"]
        scale_factor = object_scale["factor"]
        scale_name = object_scale["name_synonym"]

        object_name_description_relationship = random.choice(
            object_data["name_description_relationship"]
        )

        # Replace placeholders with actual values
        object_name_description_relationship = (
            object_name_description_relationship.replace("<name>", object_name)
            .replace("<description>", object_description)
            .replace("<size>", scale_name, 1)
        )

        random_metric_m = random.choice(["meters", "m", ""])
        size_in_meters = f"{scale_factor}{random_metric_m}"
        object_name_description_relationship = (
            object_name_description_relationship.replace(
                "<size_in_meters>", size_in_meters, 1
            )
        )

        random_metric_f = random.choice(["feet", "ft", ""])
        size_in_feet = f"{meters_to_feet_rounded(scale_factor)}{random_metric_f}"
        object_name_description_relationship = (
            object_name_description_relationship.replace(
                "<size_in_feet>", size_in_feet, 1
            )
        )

        object_name_descriptions.append(object_name_description_relationship)

    # Randomize order of object descriptions
    random.shuffle(object_name_descriptions)
    # Join the object descriptions
    object_name_descriptions = " ".join(object_name_descriptions)
    return object_name_descriptions


def generate_relationship_captions(combination: Dict[str, Any]) -> List[str]:
    """
    Generate captions for object relationships based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.

    Returns:
        List[str]: List of relationship captions.
    """
    threshold_relationships = len(combination["objects"])

    adjusted_objects = adjust_positions(
        combination["objects"], combination["orientation"]["yaw"]
    )

    camera_yaw = combination["orientation"]["yaw"]

    relationships = determine_relationships(adjusted_objects, camera_yaw)

    # Write relationships into the JSON file with combination["objects"]["relationships"]
    for i, obj in enumerate(combination["objects"]):
        obj.setdefault("relationships", [])
        if i < len(relationships):
            obj["relationships"] = relationships[i]

    selected_relationships = relationships
    if threshold_relationships < len(relationships):
        selected_relationships = random.sample(relationships, threshold_relationships)

    return selected_relationships


def add_movement_to_objects(objects, movement=None, max_speed=0.5):
    if not movement:
        return objects
    for obj in objects:
        if movement == "all":
            direction = random.choice(["left", "right", "forward", "backward"])
            speed = random.uniform(0.1, max_speed)
            obj["movement"] = {"direction": direction, "speed": speed}
    return objects


def generate_fov_caption(combination: Dict[str, Any]) -> str:
    """
    Generate a caption for the field of view (FOV) based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: FOV caption.
    """
    fov_templates = {
        "degrees": [
            "The camera has a <fov> degree field of view.",
            "The camera has a <fov> degree FOV.",
            "The field of view is <fov> degrees.",
            "Set the fov of the camera to <fov> degrees.",
            "Set the FOV of the camera to <fov>°",
        ],
        "mm": [
            "The camera has a <mm> mm focal length.",
            "The focal length is <mm> mm.",
            "Set the focal length of the camera to <mm> mm.",
        ],
    }

    fov = combination["framing"]["fov"]

    # FOV is stored as degrees in the framing data
    fov_types = "degrees", "mm"

    # Select a random FOV type
    fov_type = random.choice(fov_types)

    # Select a random FOV template
    fov_template = random.choice(fov_templates[fov_type])

    # Replace the <fov> placeholder with the FOV value
    fov_template = fov_template.replace("<fov>", str(fov))

    # Convert FOV to focal length
    focal_length = int(35 / (2 * math.tan(math.radians(fov) / 2)))
    fov_caption = fov_template.replace("<mm>", str(focal_length))

    if fov_type == "degrees":
        fov_caption += f" ({focal_length:.2f} mm focal length)"

    return fov_caption


def generate_postprocessing_caption(combination: Dict[str, Any], camera_data) -> str:
    """
    Generate a caption for postprocessing based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: Postprocessing caption.
    """
    postprocessing = combination["postprocessing"]
    caption_parts = []

    postprocessing_options = camera_data["postprocessing"]

    for key in postprocessing:
        post_type = postprocessing[key]["type"]
        if key == "bloom":
            bloom_caption = random.choice(
                postprocessing_options["bloom"]["types"][post_type]["descriptions"]
            )
            caption_parts.append(bloom_caption)
        elif key == "ssao":
            ssao_caption = random.choice(
                postprocessing_options["ssao"]["types"][post_type]["descriptions"]
            )
            caption_parts.append(ssao_caption)
        elif key == "ssrr":
            ssrr_caption = random.choice(
                postprocessing_options["ssrr"]["types"][post_type]["descriptions"]
            )
            caption_parts.append(ssrr_caption)
        elif key == "motionblur":
            motionblur_caption = random.choice(
                postprocessing_options["motionblur"]["types"][post_type]["descriptions"]
            )
            caption_parts.append(motionblur_caption)

    # randomly determine how many values (1-4 inclusive) to pop
    num_to_pop = random.randint(1, len(caption_parts))
    for _ in range(num_to_pop):
        random_index_to_remove_from_end = random.randint(0, len(caption_parts) - 1)
        caption_parts.pop(random_index_to_remove_from_end)
    return " ".join(caption_parts)


def generate_framing_caption(
    camera_data: Dict[str, Any], combination: Dict[str, Any]
) -> str:
    """
    Generate a caption for framing based on the camera data and combination data.
    Copy codeArgs:
        camera_data (Dict[str, Any]): Camera data.
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: Framing caption.
    """
    framing = combination["framing"]
    framing_name = framing["name"]

    # Find the matching framing in camera_data
    matching_framing = next(
        (f for f in camera_data["framings"] if f["name"] == framing_name), None
    )

    if matching_framing:
        framing_description = random.choice(matching_framing["descriptions"])
        framing_description = framing_description.replace(
            "<fov>", str(framing["fov"])
        ).replace("<coverage_factor>", str(framing["coverage_factor"]))
        return framing_description
    else:
        return ""


def flatten_descriptions(descriptions: List[Any]) -> List[str]:
    """
    Flatten a list of descriptions, which may contain nested lists.
    Copy codeArgs:
        descriptions (List[Any]): A list of descriptions which may contain nested lists.

    Returns:
        List[str]: A flattened list of descriptions.
    """
    flat_list = []
    for item in descriptions:
        if isinstance(item, list):
            flat_list.extend(flatten_descriptions(item))
        else:
            flat_list.append(item)
    return flat_list


def speed_factor_to_percentage(speed_factor: float) -> str:
    """
    Convert speed factor to a percentage string.
    Copy codeArgs:
        speed_factor (float): Speed factor value.

    Returns:
        str: Speed factor as a percentage string.
    """
    rounded_speed_factor = round(speed_factor, 2)
    percentage = int(rounded_speed_factor * 100)
    return f"{percentage}%"


def generate_animation_captions(combination: Dict[str, Any], camera_data) -> List[str]:
    """
    Generate captions for camera animations based on the combination data and speed factor.
    Copy codeArgs:
        combination (Dict[str, Any]): Combination data.

    Returns:
        List[str]: List of animation captions.
    """
    speed_factor = round(combination["animation"]["speed_factor"], 2)
    speed_factor_str = (
        speed_factor_to_percentage(speed_factor)
        if random.choice([True, False])
        else f"{speed_factor}x"
    )

    animation_speeds = camera_data["animation_speed"]

    animation_type = "none"
    for speed_range in animation_speeds["types"].values():
        if speed_range["min"] <= speed_factor <= speed_range["max"]:
            animation_type = next(
                (
                    t
                    for t, details in animation_speeds["types"].items()
                    if details == speed_range
                ),
                "none",
            )
            descriptions = speed_range["descriptions"]
            break

    if animation_type != "none":
        flat_descriptions = flatten_descriptions(descriptions)
        animation_caption = random.choice(flat_descriptions)
        animation_caption = animation_caption.replace(
            "<animation_speed_value>", speed_factor_str
        )
        return [animation_caption]

    return []


def generate_movement_captions(combination: Dict[str, Any], object_data) -> List[str]:
    """
    Generate captions for object movement based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.
        object_data (Dict[str, Any]): Object data including movement templates and speed descriptions.

    Returns:
        List[str]: List of movement captions.
    """

    if 'movement_description_relationship' not in object_data:
        return []

    object_movement_data = object_data['movement_description_relationship']
    object_movement_speed_words = object_data['movement_speed_description']

    movement_captions = []
    for obj in combination['objects']:
        if 'movement' in obj:
            speed = obj['movement']['speed']
            if speed <= 0.25:
                speed_words = object_movement_speed_words['0.25']
            else:
                speed_words = object_movement_speed_words['0.5']

            speed_description = random.choice(speed_words)

            template = random.choice(object_movement_data)
            movement_description = template.replace('<object>', obj['name'])
            movement_description = movement_description.replace('<movement>', obj['movement']['direction'])
            movement_description = movement_description.replace('<speed>', f'{speed:.2f}')

            if '<speed_description>' in movement_description:
                movement_description = movement_description.replace('<speed_description>', speed_description)

            movement_captions.append(movement_description)

    return movement_captions


def generate_ontop_captions(combination: Dict[str, Any], ontop_data, object_data) -> List[str]:
    """
    Generate captions for objects being on top of each other based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.
        ontop_data (str): Flag indicating whether to allow objects on top of each other.
        object_data (Dict[str, Any]): Object data containing ontop description relationships.

    Returns:
        List[str]: List of ontop captions.
    """
    if not ontop_data or 'ontop_description_relationship' not in object_data:
        return []

    ontop_captions = []
    placement_stacks = {}

    object_ontop_captions = object_data['ontop_description_relationship']

    # Maintain the original order of objects
    for obj in combination["objects"]:
        placement = obj["placement"]
        if placement not in placement_stacks:
            placement_stacks[placement] = []
        placement_stacks[placement].append(obj)

    # Generate captions for objects at the same placement
    for placement, objects in placement_stacks.items():
        if len(objects) > 1:
            for i in range(len(objects) - 1):
                below_obj = objects[i]
                above_obj = objects[i + 1]
                
                caption_template = random.choice(object_ontop_captions)
                
                # Always describe from bottom to top to maintain consistency
                caption = caption_template.replace("<object1>", above_obj['name']).replace("<object2>", below_obj['name'])
                
                ontop_captions.append(caption)

    return ontop_captions


def generate_camerafollow_captions(combination: Dict[str, Any], camera_data) -> List[str]:
    """
    Generate captions for camera following objects based on the combination data.

    Args:
        combination (Dict[str, Any]): Combination data.
        camera_data (Dict[str, Any]): Camera data containing camera follow options. 

    Returns:
        List[str]: List of camera follow captions.
    """
    camera_follow_options = camera_data['camera_follow']
    camera_follow_captions = []
    for obj in combination['objects']:
        if 'camera_follow' in obj:
            caption = random.choice(camera_follow_options)
            caption = caption.replace('<object>', obj['name'])
            camera_follow_captions.append(caption)        
    return camera_follow_captions


def generate_caption(combination: Dict[str, Any], object_data, camera_data, ontop_data) -> str:
    """
    Generate a complete caption based on the combination data.
    Copy codeArgs:
        combination (Dict[str, Any]): Combination data.

    Returns:
        str: Complete caption.
    """
    caption_parts = []

    # Add object name and description captions to the caption
    object_name_descriptions = generate_object_name_description_captions(
        combination, object_data
    )
    caption_parts.append(object_name_descriptions)

    scene_relationship_description = generate_relationship_captions(combination)
    scene_relationship_description_str = " ".join(scene_relationship_description)
    caption_parts.append(scene_relationship_description_str)

    # Add the camera orientation to the caption
    orientation_text = generate_orientation_caption(camera_data, combination)
    caption_parts.append(orientation_text)

    fov_caption = generate_fov_caption(combination)
    caption_parts.append(fov_caption)

    framing_caption = generate_framing_caption(camera_data, combination)
    caption_parts.append(framing_caption)

    postprocessing_caption = generate_postprocessing_caption(combination, camera_data)
    caption_parts.append(postprocessing_caption)

    # Add the stage caption
    stage_captions = generate_stage_captions(combination)
    caption_parts.extend(stage_captions)

    animation_captions = generate_animation_captions(combination, camera_data)
    caption_parts.extend(animation_captions)

     # Add information about object movement
    movement_captions = generate_movement_captions(combination, object_data)
    caption_parts.extend(movement_captions)

    ontop_captions = generate_ontop_captions(combination, ontop_data, object_data)
    caption_parts.extend(ontop_captions)

    camerafollow_captions = generate_camerafollow_captions(combination, camera_data)
    caption_parts.extend(camerafollow_captions)

    caption = " ".join(caption_parts)  # Join the caption parts into a single string
    caption = caption.strip()  # Remove leading and trailing whitespace

    return caption


def generate_postprocessing(camera_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate postprocessing settings based on the camera data.
    Copy codeArgs:
        camera_data (Dict[str, Any]): Camera data.

    Returns:
        Dict[str, Any]: Postprocessing settings.
    """
    postprocessing = {}

    bloom_data = camera_data["postprocessing"]["bloom"]

    bloom_threshold = random.uniform(
        bloom_data["threshold_min"], bloom_data["threshold_max"]
    )
    bloom_intensity = random.uniform(
        bloom_data["intensity_min"], bloom_data["intensity_max"]
    )
    bloom_radius = random.uniform(bloom_data["radius_min"], bloom_data["radius_max"])

    bloom_type = "none"
    bloom_types = bloom_data["types"]
    for t in bloom_types.keys():
        if (
            bloom_intensity >= bloom_types[t]["intensity_min"]
            and bloom_intensity <= bloom_types[t]["intensity_max"]
        ):
            bloom_type = t
            break

    postprocessing["bloom"] = {
        "threshold": bloom_threshold,
        "intensity": bloom_intensity,
        "radius": bloom_radius,
        "type": bloom_type,
    }

    ssao_data = camera_data["postprocessing"]["ssao"]
    ssao_distance = random.uniform(ssao_data["distance_min"], ssao_data["distance_max"])
    ssao_factor = random.uniform(ssao_data["factor_min"], ssao_data["factor_max"])

    ssao_type = "none"
    for t in ssao_data["types"].keys():
        if (
            ssao_factor >= ssao_data["types"][t]["factor_min"]
            and ssao_factor <= ssao_data["types"][t]["factor_max"]
        ):
            ssao_type = t
            break

    postprocessing["ssao"] = {
        "distance": ssao_distance,
        "factor": ssao_factor,
        "type": ssao_type,
    }

    ssrr_data = camera_data["postprocessing"]["ssrr"]
    ssrr_max_roughness = random.uniform(
        ssrr_data["min_max_roughness"], ssrr_data["max_max_roughness"]
    )
    ssrr_thickness = random.uniform(
        ssrr_data["min_thickness"], ssrr_data["max_thickness"]
    )

    ssrr_type = "none"
    for t in ssrr_data["types"].keys():
        if (
            ssrr_max_roughness >= ssrr_data["types"][t]["max_roughness_min"]
            and ssrr_max_roughness <= ssrr_data["types"][t]["max_roughness_max"]
        ):
            ssrr_type = t
            break

    postprocessing["ssrr"] = {
        "max_roughness": ssrr_max_roughness,
        "thickness": ssrr_thickness,
        "type": ssrr_type,
    }

    motionblur_data = camera_data["postprocessing"]["motionblur"]
    motionblur_shutter_speed = random.uniform(
        motionblur_data["shutter_speed_min"], motionblur_data["shutter_speed_max"]
    )

    motionblur_type = "none"
    for t in motionblur_data["types"].keys():
        if (
            motionblur_shutter_speed >= motionblur_data["types"][t]["shutter_speed_min"]
            and motionblur_shutter_speed
            <= motionblur_data["types"][t]["shutter_speed_max"]
        ):
            motionblur_type = t
            break

    postprocessing["motionblur"] = {
        "shutter_speed": motionblur_shutter_speed,
        "type": motionblur_type,
    }
    return postprocessing


def generate_orientation(
    camera_data: Dict[str, Any],
    objects: List[Dict[str, Any]],
    background: Dict[str, Any],
) -> Dict[str, int]:
    """
    Generate camera orientation based on the camera data, objects, and background.
    Copy codeArgs:
        camera_data (Dict[str, Any]): Camera data.
        objects (List[Dict[str, Any]]): List of objects in the scene.
        background (Dict[str, Any]): Background information.

    Returns:
        Dict[str, int]: Camera orientation.
    """
    orientation_data = camera_data["orientation"]

    # Roll a number between orientation['yaw_min'] and orientation['yaw_max']
    yaw = random.randint(orientation_data["yaw_min"], orientation_data["yaw_max"])
    pitch = random.randint(orientation_data["pitch_min"], orientation_data["pitch_max"])

    # Check if the camera is going to be occluded by the objects
    # If so, re-roll the orientation until a non-occluded orientation is found
    while True:
        occluded = False
        for obj in objects[1:]:
            # Calculate the vector from the camera to the object
            # calculate the position of the camera on the unit circle from yaw
            camera_x = math.cos(math.radians(yaw))
            camera_y = math.sin(math.radians(yaw))

            camera_vector = [camera_x, camera_y, 0]

            # get the position of the object
            object_position = obj["transformed_position"]

            # normalize the object position, account for division by 0
            object_position = [
                a / max(1e-6, sum([b**2 for b in object_position])) ** 0.5
                for a in object_position
            ]

            # if the magnitude of the object position is 0, ignore it
            if sum([a**2 for a in object_position]) < 0.001:
                continue

            # dot product of the camera vector and the object position
            dot_product = sum([a * b for a, b in zip(camera_vector, object_position)])

            # calculate an angle padding on both sides of the object to use as a threshold
            angle = math.radians(15)
            # set the threshold to the dot product - cos of the angle
            threshold = math.cos(angle)

            if dot_product > threshold:
                occluded = True
                break

        if not occluded:
            break

        # Re-roll the orientation if occluded and try again
        yaw = random.randint(orientation_data["yaw_min"], orientation_data["yaw_max"])
        pitch = random.randint(
            orientation_data["pitch_min"], orientation_data["pitch_max"]
        )

    orientation = {
        "yaw": int(yaw),
        "pitch": int(pitch),
    }

    return orientation


def generate_framing(camera_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate camera framing based on the camera data.
    Copy codeArgs:
        camera_data (Dict[str, Any]): Camera data.

    Returns:
        Dict[str, Any]: Camera framing.
    """
    # Get the min_fov and max_fov across all framings
    fov_min = min([f["fov_min"] for f in camera_data["framings"]])
    fov_max = max([f["fov_max"] for f in camera_data["framings"]])

    # Randomly roll an FOV value between FOV_min and FOV_max
    fov = int(random.uniform(fov_min, fov_max))

    # Find the corresponding framing
    framing = None
    for f in camera_data["framings"]:
        if f["fov_min"] <= fov <= f["fov_max"]:
            framing = f
            break

    # Derive a coverage_factor between coverage_factor_min and coverage_factor_max
    coverage_factor = random.uniform(
        framing["coverage_factor_min"], framing["coverage_factor_max"]
    )

    framing = {
        "fov": fov,
        "coverage_factor": coverage_factor,
        "name": framing["name"],
    }
    return framing


def generate_animation(camera_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate camera animation based on the camera data.
    Copy codeArgs:
        camera_data (Dict[str, Any]): Camera data.

    Returns:
        Dict[str, Any]: Camera animation.
    """
    animation = random.choice(camera_data["animations"])
    animation = animation.copy()
    animation["speed_factor"] = random.uniform(0.5, 2.0)
    animation.pop("descriptions", None)
    return animation


def generate_background(
    background_dict, background_names, background_weights
) -> Dict[str, Any]:
    """
    Generate a random background.

    Returns:
        Dict[str, Any]: Generated background.
    """
    chosen_background = random.choices(background_names, weights=background_weights)[0]
    # Get the keys from the chosen background
    background_keys = list(background_dict[chosen_background].keys())
    background_id = random.choice(background_keys)
    bg = background_dict[chosen_background][background_id]

    background = {
        "name": bg["name"],
        "url": bg["url"],
        "id": background_id,
        "from": chosen_background,
    }

    return background


def generate_stage(texture_data) -> Dict[str, Any]:
    """
    Generate a random stage.

    Returns:
        Dict[str, Any]: Generated stage.
    """
    texture_names = list(texture_data.keys())
    texture_weights = [len(texture_data[name]["maps"]) for name in texture_names]
    chosen_texture = random.choices(texture_names, weights=texture_weights)[0]
    maps = texture_data[chosen_texture]["maps"]

    material = {
        "name": texture_data[chosen_texture]["name"],
        "maps": maps,
    }
    stage = {
        "material": material,
        "uv_scale": [random.uniform(0.8, 1.2), random.uniform(0.8, 1.2)],
        "uv_rotation": random.uniform(0, 360),
    }
    return stage


def add_camera_follow(objects, camera_follow):
    if camera_follow == "all":  
        # how many objects in array
        num_objects = len(objects)
        # randomly select an object to follow
        random_index = random.randint(0, num_objects - 1)
        objects[random_index]["camera_follow"] = {"follow": True}

    return objects


def generate_combinations(
    camera_data: Dict[str, Any],
    count: int,
    seed: Optional[int],
    dataset_names: List[str],
    dataset_weights: List[int],
    object_data: Dict[str, Any],
    dataset_dict: Dict[str, Any],
    captions_data: Dict[str, Any],
    background_dict: Dict[str, Any],
    background_names: List[str],
    background_weights: List[int],
    texture_data: Dict[str, Any],
    movement: str = "",  
    max_speed: float = 0.5,
    ontop_data: str = "",
    camera_follow: str = "",
) -> Dict[str, Any]:
    """
    Generate random combinations of camera settings, objects, background, and stage.

    Args:
        camera_data (Dict[str, Any]): Camera data.
        count (int): Number of combinations to generate.
        seed (Optional[int]): Seed for the random number generator.

    Returns:
        Dict[str, Any]: Generated combinations data.
    """
    if seed is None:
        seed = -1
    random.seed(seed)

    combinations = []

    # Generate combinations on the fly up to the specified count
    for i in range(count):
        objects = generate_objects(
            object_data, dataset_names, dataset_weights, dataset_dict, captions_data, ontop_data
        )
        background = generate_background(
            background_dict, background_names, background_weights
        )

        # Calculate the transformed positions of the objects
        adjusted_objects = adjust_positions(objects, random.randint(0, 360))
        for obj, adjusted_obj in zip(objects, adjusted_objects):
            obj["transformed_position"] = adjusted_obj["transformed_position"]

        orientation = generate_orientation(camera_data, objects, background)

        framing = generate_framing(camera_data)

        postprocessing = generate_postprocessing(camera_data)

        animation = generate_animation(camera_data)  # speed is between 0.5 and 2

        stage = generate_stage(texture_data)

        objects = add_movement_to_objects(objects, movement, max_speed)

        camera_follow = add_camera_follow(objects, camera_follow)

        combination = {
            "index": i,
            "objects": objects,
            "background": background,
            "orientation": orientation,
            "framing": framing,
            "animation": animation,
            "stage": stage,
            "postprocessing": postprocessing,
        }

        combination["caption"] = generate_caption(combination, object_data, camera_data, ontop_data)

        combinations.append(combination)

    data = {"seed": seed, "count": count, "combinations": combinations}

    return data

def generate_objects(
    object_data, dataset_names, dataset_weights, dataset_dict, captions_data, ontop_data
) -> List[Dict[str, Any]]:
    """
    Generate a list of random objects.

    Returns:
        List[Dict[str, Any]]: List of generated objects.
    """
    chosen_dataset = "cap3d"

    if chosen_dataset not in dataset_dict:
        raise KeyError(f"Dataset '{chosen_dataset}' not found in dataset_dict")

    # Randomly generate max_number_of_objects
    max_number_of_objects = parse_args().max_number_of_objects
    number_of_objects = random.randint(1, max_number_of_objects)

    object_scales = object_data["scales"]

    # Scale values
    scale_values = [scale["factor"] for scale in object_scales.values()]

    # Create simple triangular distribution based on scale_values
    len_scale_values = len(scale_values)
    mid_point = len_scale_values // 2
    if len_scale_values % 2 == 0:
        weights = [i + 1 for i in range(mid_point)] + [
            mid_point - i for i in range(mid_point)
        ]
    else:
        weights = (
            [i + 1 for i in range(mid_point)]
            + [mid_point + 1]
            + [mid_point - i for i in range(mid_point)]
        )

    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    objects = []
    positions_taken = set()
    for i in range(number_of_objects):
        object_uid = random.choice(dataset_dict[chosen_dataset])
        object_description = captions_data[object_uid]
        
        scale_choice = random.choices(
            list(object_scales.items()), weights=normalized_weights, k=1
        )[0]
        scale_key = scale_choice[0]
        scale_value = scale_choice[1]

        scale = {
            "factor": scale_value["factor"],
            "name": scale_key,
            "name_synonym": random.choice(scale_value["names"]),
        }

        if i == 0:
            placement = 4  # Ensure the first object is always placed at position 4
            positions_taken.add(placement)
        else:
            possible_positions = [
                pos for pos in range(0, 9) if pos not in positions_taken or ontop_data == "all"
            ]
            placement = random.choice(possible_positions)
            positions_taken.add(placement)

        object = {
            "name": object_description,  # Use the description directly
            "uid": object_uid,
            "description": object_description,  # Use the description directly
            "placement": placement,
            "from": chosen_dataset,
            "scale": scale,
        }

        objects.append(object)

    return objects

if __name__ == "__main__":
    args = parse_args()

    # Load only cap3d dataset
    cap3d_data_path = args.cap3d_captions_path
    logger.info(f"Loading {cap3d_data_path}")
    cap3d_data = read_json_file(cap3d_data_path)
    logger.info(f"Loaded {len(cap3d_data)} unique entries from cap3d")

    # Ensure the dataset_dict contains only cap3d data
    dataset_dict = {"cap3d": list(cap3d_data.keys())}

    object_data = read_json_file(args.object_data_path)
    captions_data = read_json_file(args.cap3d_captions_path)
    stage_data = read_json_file(args.stage_data_path)
    texture_data = read_json_file(args.texture_data_path)
    camera_data = read_json_file(args.camera_file_path)
    movement_data = args.movement
    ontop_data = args.ontop
    speed = 1.0
    camera_follow = args.camera_follow

    # Load backgrounds
    backgrounds = read_json_file(args.datasets_path)["backgrounds"]
    background_dict = {}
    for bg in backgrounds:
        bg_path = os.path.join(args.simdata_path, bg + ".json")
        logger.info(f"Loading {bg_path}")
        if os.path.exists(bg_path):
            background_data = read_json_file(bg_path)
            background_dict[bg] = background_data
            logger.info(f"Loaded {len(background_data)} entries from {bg}")
        else:
            logger.info(f"Dataset file {bg_path} not found")

    background_names = list(background_dict.keys())
    background_weights = [len(background_dict[name]) for name in background_names]

    # Generate combinations
    combinations = generate_combinations(
        camera_data,
        args.count,
        args.seed,
        ["cap3d"],  # Use only the cap3d dataset
        [1],  # Weight for the cap3d dataset
        object_data,
        dataset_dict,
        captions_data,
        background_dict,
        background_names,
        background_weights,
        texture_data,
        movement_data,
        speed,
        ontop_data,
        camera_follow
    )

    # Write to JSON file
    with open(args.output_path, "w") as f:
        json.dump(combinations, f, indent=4)

    logger.info(f"Combinations have been successfully written to {args.output_path}")
