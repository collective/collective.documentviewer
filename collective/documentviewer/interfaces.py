from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import Interface
from zope import schema
from collective.documentviewer.config import CONVERTABLE_TYPES


class ILayer(Interface):
    """
    layer class
    """

FILE_TYPES_VOCAB = []

for id, doc in CONVERTABLE_TYPES.items():
    FILE_TYPES_VOCAB.append(SimpleTerm(id, id, doc.name))


class IGlobalDocumentViewerSettings(Interface):
    large_size = schema.Int(
        title=u"Large Image Size",
        default=1000)
    normal_size = schema.Int(
        title=u"Normal Image Size",
        default=700)
    thumb_size = schema.Int(
        title=u"Thumb Image Size",
        default=180)
    storage_type = schema.Choice(
        title=u"Storage Type",
        default='Blob',
        vocabulary=SimpleVocabulary.fromValues([
            'Blob',
            'File']))
    storage_location = schema.TextLine(
        title=u"Storage location",
        description=u'Only for file storage not with zodb. '
                    u'Plone client must have write access to directory.',
        default=u"/opt/dvpdffiles")
    pdf_image_format = schema.Choice(
        title=u"Image Format",
        default=u"gif",
        vocabulary=SimpleVocabulary.fromValues([
            'gif',
            'png',
            'jpg'
        ]))
    ocr = schema.Bool(
        title=u"OCR",
        default=True)
    auto_select_layout = schema.Bool(
        title=u"Auto select layout",
        description=u"For pdf files",
        default=True)
    auto_layout_file_types = schema.List(
        title=u"Auto layout file types",
        description=u"extra types only work in open office is installed",
        default=['pdf'],
        #missing_value=['pdf'],
        value_type=schema.Choice(
            vocabulary=SimpleVocabulary(FILE_TYPES_VOCAB))
        )
    auto_convert = schema.Bool(
        title=u"Auto Convert",
        description=u"Automatically convert files on creation "
                    u"and modification. ",
        default=True)
    override_contributor = schema.TextLine(
        title=u"Override Contributor",
        description=u"What to override the contributor field on viewer with."
                    u"Leave blank to use document owner")
    override_organization = schema.TextLine(
        title=u"Override Contributor Organization",
        description=u"What to override the organization field on viewer with."
                    u"Leave blank to use site title.")
    override_base_resource_url = schema.URI(
        title=u"Overridden Base Resource URL",
        description=u"If you're syncing your storage to another server you "
                    u"would like to serve the pdf resources from, please "
                    u"specify the base url path.",
        default=None,
        required=False)
    height = schema.Int(
        title=u"Viewer Height",
        description=u"Default height to use for viewer(only for "
                    u"non-fullscreen mode).",
        default=700)
    show_sidebar = schema.Bool(
        title=u"Show sidebar",
        description=u"Default to show sidebar",
        default=True)
    show_search = schema.Bool(
        title=u"Show search box",
        default=True)


class IDocumentViewerSettings(Interface):
    height = schema.Int(
        title=u"Viewer Height",
        default=None,
        required=False)
    fullscreen = schema.Bool(
        title=u"Fullscreen Viewer",
        description=u"Default to fullscreen viewer",
        default=False)
    show_sidebar = schema.Bool(
        title=u"Show sidebar",
        description=u"Default to show sidebar",
        required=False,
        default=None)
    show_search = schema.Bool(
        title=u"Show search box",
        default=None)


class IUtils(Interface):

    def enabled():
        """
        return true is documentviewer is enabled for the object
        """

    def convert():
        """
        force conversion
        """
