# -*- coding: utf-8 -*-
"""Package containing catalog indexers for HochLims.

The submodules are imported here to ensure that their ``@indexer``
decorators are executed when the package is loaded by ZCML.  Without
explicit imports Python would not automatically load the modules and our
custom adapters would never be registered.
"""

# ensure our custom auditlog patch is imported as well
from . import auditlog  # noqa: F401
