from senaite.core.schema import UIDReferenceField
from senaite.core.schema import DatetimeField as SenaiteDatetimeField
from senaite.core.z3cform.widgets.datetimewidget import DatetimeWidget as SenaiteDatetimeWidget

class UIDReferenceFieldDx(UIDReferenceField):
    """Extends the UIDReferenceField to be used in Dexterity content types.
    """

class DatetimeField(SenaiteDatetimeField):
    """Extends the DatetimeField to be used in Dexterity content types.
    """

class DatetimeWidget(SenaiteDatetimeWidget):
    """Widget for displaying datetime fields in Dexterity forms.
    """