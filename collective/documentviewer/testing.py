from plone.app.testing import TEST_USER_ID
from Products.CMFCore.utils import getToolByName
from plone.app.testing import setRoles
from plone.app.testing import applyProfile
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from zope.configuration import xmlconfig
from plone.testing import z2


class DocumentViewer(PloneSandboxLayer):
    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # load ZCML
        import plone.app.contenttypes
        self.loadZCML(package=plone.app.contenttypes)
        import collective.documentviewer
        xmlconfig.file(
            'configure.zcml', collective.documentviewer,
            context=configurationContext)
        z2.installProduct(app, 'collective.documentviewer')

    def setUpPloneSite(self, portal):
        # install into the Plone site
        applyProfile(portal, 'plone.app.contenttypes:default')
        applyProfile(portal, 'collective.documentviewer:default')
        setRoles(portal, TEST_USER_ID, ('Member', 'Manager'))
        workflowTool = getToolByName(portal, 'portal_workflow')
        workflowTool.setDefaultChain('simple_publication_workflow')
        workflowTool.setChainForPortalTypes(
            ('File',), 'simple_publication_workflow')


DocumentViewer_FIXTURE = DocumentViewer()
DocumentViewer_INTEGRATION_TESTING = IntegrationTesting(
    bases=(DocumentViewer_FIXTURE,), name="DocumentViewer:Integration")
DocumentViewer_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DocumentViewer_FIXTURE,), name="DocumentViewer:Functional")
