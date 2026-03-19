import sys
import requests

from omero.cli import cli_login
from omero.gateway import BlitzGateway
from omero.model import ExternalInfoI
from omero.rtypes import rstring, rlong

DRY_RUN = True

plate_cache = dict()

def get_images(conn, container_id, is_screen=False):
    if is_screen:
        screen = conn.getObject('Screen', attributes={'id': container_id})
        for plate in screen.listChildren():
            for well in plate.listChildren():
                index = well.countWellSample()
                well_pos = well.getWellPos()
                well_pos = f"{well_pos[0]}/{well_pos[1:]}"
                for index in range(0, index):
                    pos = f"{well_pos}/{index}"
                    yield plate.getName(), pos, well.getImage(index)
    else:
        project = conn.getObject('Project', attributes={'id': container_id})
        for dataset in project.listChildren():
            for image in dataset.listChildren():
                yield dataset, "", image


def get_filepaths_info(img, parent):
    if parent and parent in plate_cache:
        return plate_cache[parent]
    path = img.getImportedImageFilePaths()["client_paths"][0]
    base, _ = path.rsplit("/", 1)
    if parent:
        plate_cache[parent] = base
    return base


def set_ext_info(conn, img, path):
    img = conn.getObject('Image', img.getId())
    extinfo = img.getExternalInfo()
    if extinfo is None:
        extinfo = ExternalInfoI()
    extinfo.entityId = rlong(3)
    extinfo.entityType = rstring("com.glencoesoftware.ngff:multiscales")
    extinfo.lsid = rstring(path)
    img.details.externalInfo = extinfo
    us = conn.getUpdateService()
    extinfo = us.saveAndReturnObject(extinfo)
    img = us.saveAndReturnObject(img._obj)


def check(path):
    response = requests.get(f"{path}/.zattrs")
    return response.status_code == 200


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        raise SystemExit(f"Usage: {sys.argv[0]} <Container>:<ID>  # e.g. Project:123")

    container, container_id = argv[0].split(":")
    container_id = int(container_id)
    is_screen = container.lower() == "screen"
    with cli_login() as c:
        conn = BlitzGateway(client_obj=c.get_client())
        for parent, pos, img in get_images(conn, container_id, is_screen=is_screen):
            path = get_filepaths_info(img, parent)
            if is_screen:
                path = f"{path}/{pos}"
            else:
                path = f"{path}/0"
            if check(path):
                if DRY_RUN:
                    print(f"Would set extinfo for image {img.getName()}({img.getId()}) to {path}")
                else:
                    set_ext_info(conn, img, path)
                    print(f"Set extinfo for image {img.getName()}({img.getId()}) to {path}")
            else:
                print(f"Could not resolve {path} for image {img.getName()}({img.getId()})")


if __name__ == "__main__":
    main()
