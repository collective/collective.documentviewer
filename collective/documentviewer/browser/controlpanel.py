from logging import getLogger

from collective.documentviewer.interfaces import IGlobalDocumentViewerSettings
from collective.documentviewer import _
from plone.app.z3cform.layout import wrap_form
from Products.CMFPlone import PloneMessageFactory
from z3c.form import button, field, form
from z3c.form.browser.checkbox import CheckBoxFieldWidget

logger = getLogger('collective.documentviewer')


class GlobalSettingsForm(form.EditForm):
    fields = field.Fields(IGlobalDocumentViewerSettings)
    fields['auto_layout_file_types'].widgetFactory = CheckBoxFieldWidget

    label = _(u'heading_documentviewer_global_settings_form',
              default=u"Global Document Viewer Settings")
    description = _(u'description_documentviewer_global_settings_form',
                    default=u"Configure the parameters for this Viewer.")

    @button.buttonAndHandler(_('Save'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        self.applyChanges(data)

        self.status = PloneMessageFactory('Changes saved.')


GlobalSettingsFormView = wrap_form(GlobalSettingsForm)
