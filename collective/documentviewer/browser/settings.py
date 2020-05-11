from logging import getLogger

from collective.documentviewer.interfaces import IDocumentViewerSettings
from collective.documentviewer import _
from plone.app.z3cform.layout import wrap_form
from Products.CMFPlone import PloneMessageFactory
from z3c.form import button, field, form
from zope.component import getMultiAdapter

logger = getLogger('collective.documentviewer')


class SettingsForm(form.EditForm):
    """
    The page that holds all the slider settings
    """
    fields = field.Fields(IDocumentViewerSettings)

    label = _(u'heading_documentviewer_settings_form',
              default=u"Document Viewer Settings")
    description = _(u'description_documentviewer_settings_form',
                    default=u"These settings override the global settings.")

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.applyChanges(data)

        url = getMultiAdapter((self.context, self.request),
                              name='absolute_url')() + '/view'
        self.request.response.redirect(url)

        self.context.plone_utils.addPortalMessage(PloneMessageFactory('Changes saved.'))


SettingsFormView = wrap_form(SettingsForm)
