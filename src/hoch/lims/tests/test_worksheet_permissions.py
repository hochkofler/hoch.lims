# -*- coding: utf-8 -*-

import unittest2 as unittest

from hoch.lims.patches import worksheet_permissions
from senaite.core.subscribers import senaite_setup as core_setup


class DummyPermissionContext(object):

    def __init__(self, roles=("LabManager", "Manager")):
        self.selected_roles = {}
        self.managed_permissions = {}
        self.reindexed = 0
        self.set_roles(roles)

    def set_roles(self, roles):
        for permission in worksheet_permissions.WORKSHEET_PERMISSIONS:
            self.selected_roles[permission] = tuple(roles)

    def rolesOfPermission(self, permission):
        return [
            {"name": role, "selected": role in self.selected_roles[permission]}
            for role in (
                "Analyst", "LabClerk", "LabManager", "Manager", "Owner")
        ]

    def manage_permission(self, permission, roles, acquire):
        roles = tuple(roles)
        self.managed_permissions[permission] = (roles, acquire)
        self.selected_roles[permission] = roles

    def snapshot(self):
        return (
            dict(self.selected_roles),
            dict(self.managed_permissions),
        )


class DummyWorksheetFolder(DummyPermissionContext):

    def reindexObject(self):
        self.reindexed += 1


class DummyPortal(DummyPermissionContext):

    def __init__(self, folder):
        super(DummyPortal, self).__init__()
        self.worksheets = folder


class TestWorksheetPermissionSynchronization(unittest.TestCase):

    def setUp(self):
        self.folder = DummyWorksheetFolder()
        self.portal = DummyPortal(self.folder)

    def test_adds_labclerk_to_portal_and_worksheet_permissions(self):
        worksheet_permissions.synchronize_worksheet_permissions(self.portal)

        for context in (self.portal, self.folder):
            for permission in worksheet_permissions.WORKSHEET_PERMISSIONS:
                self.assertIn(permission, context.managed_permissions)
                self.assertEqual(
                    (("LabClerk", "LabManager", "Manager"), 1),
                    context.managed_permissions[permission])

    def test_preserves_roles_selected_by_core_in_both_contexts(self):
        self.portal.set_roles(("LabManager", "Manager", "Owner"))
        self.folder.set_roles(("Analyst", "LabManager", "Manager"))

        worksheet_permissions.synchronize_worksheet_permissions(self.portal)

        for permission in worksheet_permissions.WORKSHEET_PERMISSIONS:
            self.assertIn(permission, self.portal.managed_permissions)
            self.assertEqual(
                (("LabClerk", "LabManager", "Manager", "Owner"), 1),
                self.portal.managed_permissions[permission])
        for permission in worksheet_permissions.WORKSHEET_PERMISSIONS:
            self.assertEqual(
                (("Analyst", "LabClerk", "LabManager", "Manager"), 1),
                self.folder.managed_permissions[permission])

    def test_is_idempotent(self):
        worksheet_permissions.synchronize_worksheet_permissions(self.portal)
        first = (self.portal.snapshot(), self.folder.snapshot())

        worksheet_permissions.synchronize_worksheet_permissions(self.portal)

        self.assertEqual(
            first, (self.portal.snapshot(), self.folder.snapshot()))


class TestWorksheetPermissionPatch(unittest.TestCase):

    def setUp(self):
        current = core_setup.update_worksheets_permissions
        self.original_core = getattr(
            current, "_hoch_lims_original", current)
        self.original_synchronize = (
            worksheet_permissions.synchronize_worksheet_permissions)
        self.events = []
        self.core_call_count = 0

        def core_update(setup):
            self.core_call_count += 1
            self.events.append("core")

        def synchronize():
            self.events.append("hoch")

        core_setup.update_worksheets_permissions = core_update
        worksheet_permissions.synchronize_worksheet_permissions = synchronize

    def tearDown(self):
        core_setup.update_worksheets_permissions = self.original_core
        worksheet_permissions.synchronize_worksheet_permissions = (
            self.original_synchronize)

    def test_runs_core_then_synchronizes_hoch_permissions(self):
        worksheet_permissions.apply_worksheet_permissions_patch()

        core_setup.update_worksheets_permissions(object())

        self.assertEqual(["core", "hoch"], self.events)

    def test_patch_initialization_is_idempotent(self):
        worksheet_permissions.apply_worksheet_permissions_patch()
        worksheet_permissions.apply_worksheet_permissions_patch()

        core_setup.update_worksheets_permissions(object())

        self.assertEqual(1, self.core_call_count)
        self.assertEqual(["core", "hoch"], self.events)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestWorksheetPermissionSynchronization))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(
        TestWorksheetPermissionPatch))
    return suite
