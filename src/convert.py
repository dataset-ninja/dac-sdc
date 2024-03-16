import os
import shutil
import xml.etree.ElementTree as ET

import supervisely as sly
from dataset_tools.convert import unpack_if_archive
from supervisely.io.fs import (
    file_exists,
    get_file_ext,
    get_file_name,
    get_file_name_with_ext,
    get_file_size,
)
from tqdm import tqdm

import src.settings as s


def convert_and_upload_supervisely_project(
    api: sly.Api, workspace_id: int, project_name: str
) -> sly.ProjectInfo:
    # Possible structure for bbox case. Feel free to modify as you needs.

    dataset_path = "/home/alex/DATASETS/TODO/data_training_V4/data_training"
    batch_size = 30
    ds_name = "train"
    image_ext = ".jpg"
    bboxes_ext = ".xml"

    def create_ann(image_path):
        labels = []

        ann_path = image_path.replace(image_ext, bboxes_ext)

        if file_exists(ann_path):
            tree = ET.parse(ann_path)
            root = tree.getroot()

            img_height = int(root.find(".//height").text)
            img_wight = int(root.find(".//width").text)

            all_objects = root.findall(".//object")

            for curr_object in all_objects:
                class_name = curr_object.find(".//name").text
                obj_class = name_to_class[class_name[:3]]
                coords_xml = curr_object.findall(".//bndbox")
                for curr_coord in coords_xml:
                    left = int(curr_coord.find(".//xmin").text)
                    top = int(curr_coord.find(".//ymin").text)
                    right = int(curr_coord.find(".//xmax").text)
                    bottom = int(curr_coord.find(".//ymax").text)

                    rect = sly.Rectangle(
                        left=int(left), top=int(top), right=int(right), bottom=int(bottom)
                    )
                    label = sly.Label(rect, obj_class)
                    labels.append(label)

        return sly.Annotation(img_size=(img_height, img_wight), labels=labels, img_tags=[seq])

    boat = sly.ObjClass("boat", sly.Rectangle)
    building = sly.ObjClass("building", sly.Rectangle)
    car = sly.ObjClass("car", sly.Rectangle)
    drone = sly.ObjClass("drone", sly.Rectangle)
    group = sly.ObjClass("group", sly.Rectangle)
    horseride = sly.ObjClass("horseride", sly.Rectangle)
    paraglider = sly.ObjClass("paraglider", sly.Rectangle)
    person = sly.ObjClass("person", sly.Rectangle)
    riding = sly.ObjClass("riding", sly.Rectangle)
    truck = sly.ObjClass("truck", sly.Rectangle)
    wakeboard = sly.ObjClass("wakeboard", sly.Rectangle)
    whale = sly.ObjClass("whale", sly.Rectangle)

    name_to_class = {
        "boa": boat,
        "bui": building,
        "car": car,
        "dro": drone,
        "gro": group,
        "hor": horseride,
        "par": paraglider,
        "per": person,
        "rid": riding,
        "tru": truck,
        "wak": wakeboard,
        "wha": whale,
    }

    seq_meta = sly.TagMeta("sequence", sly.TagValueType.ANY_STRING)

    project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
    meta = sly.ProjectMeta(obj_classes=list(name_to_class.values()), tag_metas=[seq_meta])
    api.project.update_meta(project.id, meta.to_json())

    dataset = api.dataset.create(project.id, ds_name, change_name_if_conflict=True)

    for folder in os.listdir(dataset_path):

        seq = sly.Tag(seq_meta, value=folder)

        curr_path = os.path.join(dataset_path, folder)

        images_names = [
            im_name for im_name in os.listdir(curr_path) if get_file_ext(im_name) == image_ext
        ]

        progress = sly.Progress("Create dataset {}".format(ds_name), len(images_names))

        for images_names_batch in sly.batched(images_names, batch_size=batch_size):
            img_pathes_batch = []
            im_names_batch = []
            for image_name in images_names_batch:
                im_names_batch.append(folder + "_" + image_name)
                img_pathes_batch.append(os.path.join(curr_path, image_name))

            img_infos = api.image.upload_paths(dataset.id, im_names_batch, img_pathes_batch)
            img_ids = [im_info.id for im_info in img_infos]

            anns = [create_ann(image_path) for image_path in img_pathes_batch]
            api.annotation.upload_anns(img_ids, anns)

            progress.iters_done_report(len(images_names_batch))

    return project
