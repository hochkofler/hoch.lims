# -*- coding: utf-8 -*-

from bika.lims import api
from hoch.lims import logger

BEHAVIORS = [
    ("SampleMatrix", [
        "hoch.lims.content.samplematrix.ISampleMatrixSchemaExtender",
    ]),
]

# Tuples of (folder_id, folder_name, type)
SETUP_FOLDERS = [
    ("products", "Products", "Products"),
]

def install(context):
    """Install handler
    """
    if context.readDataFile("hoch.lims.txt") is None:
        return
    logger.info("Install handler [BEGIN]")
    portal = context.getSite()  # noqa

    # Run Installers
    setup_behaviors(portal)
    add_setup_folders(portal)  # <-- Agrega la creación de carpetas

    logger.info("Install handler [DONE]")


def setup_behaviors(portal):
    """Assigns additional behaviors to existing content types
    """
    logger.info("*** Setup Behaviors ***")
    pt = api.get_tool("portal_types")
    for portal_type, behavior_ids in BEHAVIORS:
        fti = pt.get(portal_type)
        if not hasattr(fti, "behaviors"):
            # Skip, type is not registered yet probably (AT2DX migration)
            logger.warn("Behaviors is missing: {} [SKIP]".format(portal_type))
            continue
        fti_behaviors = fti.behaviors
        additional = filter(lambda b: b not in fti_behaviors, behavior_ids)
        if additional:
            fti_behaviors = list(fti_behaviors)
            fti_behaviors.extend(additional)
            fti.behaviors = tuple(fti_behaviors)

def add_setup_folders(portal):
    """Adds the initial folders in setup"""
    logger.info("Adding setup folders ...")
    setup = api.get_setup()
    pt = api.get_tool("portal_types")
    ti = pt.getTypeInfo(setup)
    ti.filter_content_types = False
    for folder_id, folder_name, portal_type in SETUP_FOLDERS:
        if setup.get(folder_id) is None:
            logger.info("Adding folder: {}".format(folder_id))
            setup.invokeFactory(portal_type, folder_id, title=folder_name)
    ti.filter_content_types = True
    logger.info("Adding setup folders [DONE]")