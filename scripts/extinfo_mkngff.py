import sys
import requests

from omero.cli import cli_login
from omero.gateway import BlitzGateway
from omero.model import ExternalInfoI
from omero.rtypes import rstring, rlong


def get_images(conn, container_id, is_screen=False):
    if is_screen:
        pass
    else:
        project = conn.getObject('Project', attributes={'id': container_id})
        for dataset in project.listChildren():
            for image in dataset.listChildren():
                yield dataset, image


def get_filepaths_info(img):
    path = img.getImportedImageFilePaths()["client_paths"][0]
    base, _ = path.rsplit("/", 1)
    return f"{base}/0"


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
    print("Set extinfo:")
    print(img.getDetails().externalInfo)


def check(path):
    response = requests.get(f"{path}/.zattrs")
    return response.status_code == 200


def main(argv=None):
    argv = argv or sys.argv[1:]
    if len(argv) != 1:
        raise SystemExit(f"Usage: {sys.argv[0]} <project_id>")

    project_id = int(argv[0])
    with cli_login() as c:
        conn = BlitzGateway(client_obj=c.get_client())
        for parent, img in get_images(conn, project_id):
            print(parent.name, img.name)
            path = get_filepaths_info(img)
            print(path)
            if check(path):
                print("OK")
                set_ext_info(conn, img, path)
            else:
                print("NOT OK")


if __name__ == "__main__":
    main()
