from Testing.makerequest import makerequest
from zope.globalrequest import setRequest
from bika.lims import api

app = makerequest(app)
setRequest(app.REQUEST)

try:
    portal = app.unrestrictedTraverse('test05')
except:
    try:
        portal = app.unrestrictedTraverse('plone')
    except:
        portal = app.unrestrictedTraverse('lims')

portal.setupCurrentSkin(app.REQUEST)

# Test creating process
container = portal.Processes
print("Container ID before create:", container.getId())

try:
    obj = api.create(container, "Process", title="Test Process Script")
    print("Created obj:", obj)
    print("Obj ID after create:", obj.getId() if hasattr(obj, 'getId') else "no getId")
    print("Is obj the container?", obj == container)
except Exception as e:
    import traceback
    traceback.print_exc()

