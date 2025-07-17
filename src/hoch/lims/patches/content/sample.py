from hoch.lims import check_installed

@check_installed(None)
def getProductionBatchNumber(self):  # noqa camelcase, but compliant with AT's
    """Returns the batch Number
    """
    return self.getField("ProductionBatchNumber").get(self)