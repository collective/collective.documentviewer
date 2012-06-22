from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import Interface
from zope.interface import Attribute
from zope import schema
from zope.component.interfaces import IObjectEvent
from collective.documentviewer.config import CONVERTABLE_TYPES
from OFS.interfaces import IItem


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
        description=u"Blob storage using the normal ZODB blob mechanism. "
                    u"File storage is for just storage the files on the "
                    u"file system with no hard reference on write to the "
                    u"ZODB. This allows you to easily push the files to "
                    u"be served off-site.",
        default='Blob',
        vocabulary=SimpleVocabulary.fromValues([
            'Blob',
            'File']))
    storage_location = schema.TextLine(
        title=u"Storage location",
        description=u'Only for file storage not with zodb. '
                    u'Plone client must have write access to directory.',
        default=u"/opt/dvpdffiles")
    storage_obfuscate = schema.Bool(
        title=u"Obfuscate private file paths",
        description=u"*experimental* If you're serving files straight from "
                    u"a web server, there is no way to do permission checks "
                    u"on them. This provides a bit more security as the path "
                    u"to the resources will be more difficult to guess and "
                    u"never publisized. Of course, do not have your web "
                    u"server list directory contents. *If you don't know what "
                    u"this does, you probably do NOT want to enable it*",
        default=False)
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
        description=u"extract the text from the PDF using OCR technology",
        default=False)
    detect_text = schema.Bool(
        title=u"Detect text",
        description=u"Detect if pdf has text before performing OCR on it. "
                    u"If text is found, ocr will be skipped. "
                    u"If OCR is disabled, text will always try to be "
                    u"retrieved from the PDF file anyways.",
        default=True)
    auto_select_layout = schema.Bool(
        title=u"Auto select layout",
        description=u"For pdf files",
        default=True)
    auto_layout_file_types = schema.List(
        title=u"Auto layout file types",
        description=u"extra types only work with "
                    u"openoffice/libreoffice installed",
        default=['pdf'],
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
                    u"Leave blank to use document owner",
        default=None,
        required=False)
    override_organization = schema.TextLine(
        title=u"Override Contributor Organization",
        description=u"What to override the organization field on viewer with."
                    u"Leave blank to use site title.",
        default=None,
        required=False)
    override_base_resource_url = schema.URI(
        title=u"Override Base Resource URL",
        description=u"If you're syncing your storage to another server you "
                    u"would like to serve the pdf resources from, please "
                    u"specify the base url path.",
        default=None,
        required=False)
    width = schema.Int(
        title=u"Viewer Width",
        description=u"Leave blank to take full width.",
        default=None,
        required=False)
    height = schema.Int(
        title=u"Viewer Height",
        description=u"Default height to use for viewer(only for "
                    u"non-fullscreen mode).",
        default=700)
    show_sidebar = schema.Bool(
        title=u"Show sidebar",
        description=u"Default to show sidebar on Document Viewer.",
        default=True)
    show_search = schema.Bool(
        title=u"Show search box",
        description=u"On Document Viewer.",
        default=True)
    show_search_on_group_view = schema.Bool(
        title=u"Show search on group view",
        description=u"Enable search on group view.",
        default=True)
    group_view_batch_size = schema.Int(
        title=u"Group View Batch Size",
        description=u"For folders. Does not apply to topics.",
        default=20)
    async_quota_size = schema.Int(
        title=u"Async Quota Size",
        description=u"Number of conversions to run at a time. "
                    u"The quota name assigned is `dv`.",
        default=3)


class IDocumentViewerSettings(Interface):
    width = schema.Int(
        title=u"Viewer Width",
        description=u"Leave blank to take full width.",
        default=None,
        required=False)
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

    def settings_enabled():
        """
        if settings button should appear
        """

    def convert():
        """
        force conversion
        """
    def async_enabled():
        """
        whether async is installed
        """


class IConversionFinishedEvent(IObjectEvent):

    status = Attribute("The status of the conversion")


class IBlobFileWrapper(IItem):
    pass
