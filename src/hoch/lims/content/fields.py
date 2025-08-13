from senaite.core.schema import UIDReferenceField
from senaite.core.schema import DatetimeField as SenaiteDatetimeField
from bika.lims.browser.fields import UIDReferenceField as ATUIDReferenceField
from archetypes.schemaextender.field import ExtensionField
from senaite.core.z3cform.widgets.datetimewidget import DatetimeWidget as SenaiteDatetimeWidget
from Products.Archetypes.public import DateTimeField
from Products.Archetypes.Field import IntegerField
from Products.Archetypes.public import StringField

class UIDReferenceFieldDx(UIDReferenceField):
    """Extends the UIDReferenceField to be used in Dexterity content types.
    """

class DatetimeField(SenaiteDatetimeField):
    """Extends the DatetimeField to be used in Dexterity content types.
    """

class DatetimeWidget(SenaiteDatetimeWidget):
    """Widget for displaying datetime fields in Dexterity forms.
    """

class UIDReferenceFieldAT(ExtensionField, ATUIDReferenceField):
    """Extends the UIDReferenceField to be used in Archetypes content types.
    """


class ExtDateTimeFieldAT(ExtensionField, DateTimeField):
    """Field extender of core's DateTimeField for AT
    """

class ExtIntegerFieldAT(ExtensionField, IntegerField):
    """ Field extender of IntegerField AT
    """
    
class ExtStringFieldAT(ExtensionField, StringField):
    """ Field extender of StringField AT
    """