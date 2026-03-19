from Products.Archetypes.public import DisplayList
from zope.component import getUtility
from zope.schema.interfaces import IVocabularyFactory

def getDestinationsVocabulary(self):
    factory = getUtility(
        IVocabularyFactory,
        name='hoch.lims.vocabularies.destinations'
    )
    vocab = factory(self)

    pairs = [(t.value, t.title) for t in vocab]
    return DisplayList(pairs)


def getProcessesVocabulary(self):
    """Return the processes for the linked product's process group."""
    batch = None
    
    # Method 1: getBatch() - works when AR is already linked to a batch
    if hasattr(self, 'getBatch'):
        batch = self.getBatch()
    
    # Method 2: getContainer() - works during ar_add when Container field is set
    if not batch and hasattr(self, 'getContainer'):
        try:
            batch = self.getContainer()
        except Exception:
            pass
    
    # Method 3: getBatchUID() and catalog lookup - works even in portal_factory
    if not batch and hasattr(self, 'getBatchUID'):
        try:
            batch_uid = self.getBatchUID()
            if batch_uid:
                req = getattr(self, 'REQUEST', None)
                if req:
                    parents = req.get('PARENTS', [])
                    if parents:
                        portal = parents[0]
                        try:
                            catalog = portal.uid_catalog
                            results = catalog(UID=batch_uid)
                            if results:
                                batch = results[0].getObject()
                        except Exception:
                            pass
        except Exception:
            pass

    # Method 4: Acquisition chain walk - fallback for edge cases
    if not batch or (hasattr(batch, 'meta_type') and batch.meta_type == 'AnalysisRequest'):
        parent = self
        for _ in range(10):
            parent = getattr(parent, 'aq_parent', None)
            if parent is None:
                break
            if hasattr(parent, 'meta_type') and parent.meta_type == 'Batch':
                batch = parent
                break

    if not batch:
        return DisplayList()

    # Get product from batch
    product = None
    
    # Method 1: getProduct() method
    if hasattr(batch, 'getProduct'):
        try:
            product = batch.getProduct()
        except Exception:
            pass
    
    # Method 2: Product attribute (may be a UID that needs resolution)
    if not product and hasattr(batch, 'Product'):
        try:
            product_ref = batch.Product
            
            # If it's a UID string, resolve it via the catalog
            if isinstance(product_ref, (str, unicode)):
                req = getattr(self, 'REQUEST', None)
                if req:
                    parents = req.get('PARENTS', [])
                    if parents:
                        portal = parents[0]
                        try:
                            catalog = portal.uid_catalog
                            results = catalog(UID=product_ref)
                            if results:
                                product = results[0].getObject()
                        except Exception:
                            pass
            else:
                # It's already a product object
                product = product_ref
        except Exception:
            pass
    
    # Method 3: getRawProduct()
    if not product and hasattr(batch, 'getRawProduct'):
        try:
            product = batch.getRawProduct()
        except Exception:
            pass

    if not product:
        return DisplayList()

    # Get process group from product
    process_group = None
    try:
        process_group = product.getProcessGroup()
    except Exception:
        pass

    if not process_group:
        return DisplayList()

    # Get processes from process group
    try:
        processes = process_group.getProcesses()
        pairs = [(p, p) for p in processes]
        return DisplayList(pairs)
    except Exception:
        return DisplayList()
