# -*- coding: utf-8 -*-

import sys

# Monkey patch the batch workflow module into bika.lims.workflow
# This allows SENAITE's guard_handler and AfterTransitionEventHandler
# to find our guards and events modules
import hoch.lims.workflow.batch as batch_workflow_module
import hoch.lims.workflow.batch.guards as batch_guards_module
import hoch.lims.workflow.batch.events as batch_events_module

# Add to bika.lims.workflow namespace
import bika.lims.workflow
sys.modules['bika.lims.workflow.batch'] = batch_workflow_module
sys.modules['bika.lims.workflow.batch.guards'] = batch_guards_module
sys.modules['bika.lims.workflow.batch.events'] = batch_events_module
bika.lims.workflow.batch = batch_workflow_module
