from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import Interface
from zope.interface import Attribute
from zope import schema
from zope.component.interfaces import IObjectEvent
from zope.site.hooks import getSite
from collective.documentviewer.config import CONVERTABLE_TYPES
from collective.documentviewer import mf as _
from OFS.interfaces import IItem

try:
    # older versions of zope.schema do not support defaultFactory
    schema.Int(title=u"", defaultFactory=lambda x: 5)
    SUPPORT_DEFAULT_FACTORY = True
except TypeError:
    SUPPORT_DEFAULT_FACTORY = False


class ILayer(Interface):
    """
    layer class
    """

FILE_TYPES_VOCAB = []

for type_id, doc in CONVERTABLE_TYPES.items():
    FILE_TYPES_VOCAB.append(SimpleTerm(type_id, type_id, doc.name))


class IGlobalDocumentViewerSettings(Interface):
    large_size = schema.Int(
        title=_("Large Image Size"),
        default=1000)
    normal_size = schema.Int(
        title=_("Normal Image Size"),
        default=700)
    thumb_size = schema.Int(
        title=_("Thumb Image Size"),
        default=180)
    storage_type = schema.Choice(
        title=_("Storage Type"),
        description=_("Blob storage using the normal ZODB blob mechanism. "
                      "File storage is for just storage the files on the "
                      "file system with no hard reference on write to the "
                      "ZODB. This allows you to easily push the files to "
                      "be served off-site."),
        default='Blob',
        vocabulary=SimpleVocabulary.fromValues([
            'Blob',
            'File']))
    storage_location = schema.TextLine(
        title=_("Storage location"),
        description=_('Only for file storage not with zodb. '
                      'Plone client must have write access to directory.'),
        default=u"/opt/dvpdffiles")
    storage_obfuscate = schema.Bool(
        title=_("Obfuscate private file paths"),
        description=_("*experimental* If you're serving files straight from "
                      "a web server, there is no way to do permission checks "
                      "on them. This provides a bit more security as the path "
                      "to the resources will be more difficult to guess and "
                      "never publisized. Of course, do not have your web "
                      "server list directory contents. *If you don't know what "
                      "this does, you probably do NOT want to enable it*"),
        default=False)
    pdf_image_format = schema.Choice(
        title=_("Image Format"),
        default=u"gif",
        vocabulary=SimpleVocabulary.fromValues([
            'gif',
            'png',
            'jpg'
        ]))
    enable_indexation = schema.Bool(
        title=_("Make searchable"),
        description=_("If this is enabled, the text will be extracted from "
                      "the PDF and will be searchable using the search widget and "
                      "with the Plone search. "
                      "If this is disabled, the two following parameters 'OCR' "
                      "and 'Detect text' are not taken into account.  Take care "
                      "that this will not make already converted elements searchable/"
                      "not searchable, you will have to convert existing element yourself."
                      ),
        default=True)
    ocr = schema.Bool(
        title=_("OCR"),
        description=_("Extract the text from the PDF using OCR technology."),
        default=False)
    detect_text = schema.Bool(
        title=_("Detect text"),
        description=_("Detect if pdf has text before performing OCR on it. "
                      "If text is found, ocr will be skipped. "
                      "If OCR is disabled, text will always try to be "
                      "retrieved from the PDF file anyways."),
        default=True)
    auto_select_layout = schema.Bool(
        title=_("Auto select layout"),
        description=_("For pdf files."),
        default=True)
    auto_layout_file_types = schema.List(
        title=_("Auto layout file types"),
        description=_("Extra types only work with "
                      "openoffice/libreoffice installed."),
        default=['pdf'],
        value_type=schema.Choice(
            vocabulary=SimpleVocabulary(FILE_TYPES_VOCAB))
        )
    auto_convert = schema.Bool(
        title=_("Auto Convert"),
        description=_("Automatically convert files on creation "
                      "and modification."),
        default=True)
    override_contributor = schema.TextLine(
        title=_("Override Contributor"),
        description=_("What to override the contributor field on viewer with."
                      "Leave blank to use document owner."),
        default=None,
        required=False)
    override_organization = schema.TextLine(
        title=_("Override Contributor Organization"),
        description=_("What to override the organization field on viewer with."
                      "Leave blank to use site title."),
        default=None,
        required=False)
    override_base_resource_url = schema.URI(
        title=_("Override Base Resource URL"),
        description=_("If you're syncing your storage to another server you "
                      "would like to serve the pdf resources from, please "
                      "specify the base url path."),
        default=None,
        required=False)
    width = schema.Int(
        title=_("Viewer Width"),
        description=_("Leave blank to take full width."),
        default=None,
        required=False)
    height = schema.Int(
        title=_("Viewer Height"),
        description=_("Default height to use for viewer (only for "
                      "non-fullscreen mode)."),
        default=700)
    show_sidebar = schema.Bool(
        title=_("Show sidebar"),
        description=_("Default to show sidebar on Document Viewer."),
        default=True)
    show_search = schema.Bool(
        title=_("Show search box"),
        description=_("On Document Viewer."),
        default=True)
    show_search_on_group_view = schema.Bool(
        title=_("Show search on group view"),
        description=_("Enable search on group view."),
        default=True)
    group_view_batch_size = schema.Int(
        title=_("Group View Batch Size"),
        description=_("For folders. Does not apply to topics."),
        default=20)
    async_quota_size = schema.Int(
        title=_("Async Quota Size"),
        description=_("Number of conversions to run at a time. "
                      "The quota name assigned is `dv`."),
        default=3)


def default_width():
    # take the value from the global settings
    from collective.documentviewer.settings import GlobalSettings
    gsettings = GlobalSettings(getSite())
    return gsettings.width


def default_height():
    # take the value from the global settings
    from collective.documentviewer.settings import GlobalSettings
    gsettings = GlobalSettings(getSite())
    return gsettings.height


def default_enable_indexation():
    # take the value from the global settings
    from collective.documentviewer.settings import GlobalSettings
    gsettings = GlobalSettings(getSite())
    return gsettings.enable_indexation


def default_show_sidebar():
    # take the value from the global settings
    from collective.documentviewer.settings import GlobalSettings
    gsettings = GlobalSettings(getSite())
    return gsettings.show_sidebar


def default_show_search():
    # take the value from the global settings
    from collective.documentviewer.settings import GlobalSettings
    gsettings = GlobalSettings(getSite())
    return gsettings.show_search


def _default(factory, value):
    # if defaultFactory supported, use it, otherwise, just use provided default
    if SUPPORT_DEFAULT_FACTORY:
        return {'defaultFactory': factory}
    else:
        return {'default': value}


class IDocumentViewerSettings(Interface):
    width = schema.Int(
        title=_("Viewer Width"),
        description=_("Leave blank to take full width."),
        required=False,
        **_default(default_width,
            IGlobalDocumentViewerSettings['width'].default))
    height = schema.Int(
        title=_("Viewer Height"),
        required=False,
        **_default(default_height,
            IGlobalDocumentViewerSettings['height'].default))
    fullscreen = schema.Bool(
        title=_("Fullscreen Viewer"),
        description=_("Default to fullscreen viewer."),
        default=False)
    enable_indexation = schema.Bool(
        title=_("Make searchable"),
        description=_("If this is enabled, the text will be extracted from "
                      "the PDF and will be searchable using the search widget and "
                      "with the Plone search.  You will need to run conversion again "
                      "for this parameter to be taken into account."
                      ),
        **_default(default_enable_indexation,
            IGlobalDocumentViewerSettings['width'].default))
    show_sidebar = schema.Bool(
        title=_("Show sidebar"),
        description=_("Default to show sidebar."),
        required=False,
        **_default(default_show_sidebar,
            IGlobalDocumentViewerSettings['width'].default))
    show_search = schema.Bool(
        title=_("Show search box"),
        **_default(default_show_search,
            IGlobalDocumentViewerSettings['width'].default))


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


class IOCRLanguage(Interface):
    """ Adapter interface that returns the relevant
        language for the OCR converter (Tesseract) encoded
        as ISO 639-2 code (3 char codes).
    """

    def getLanguage(context):
        """ Return ISO 639-2 language code for given
            Plone context object
        """


class IFileWrapper(Interface):
    has_enclosure = Attribute("If object has enclosure")
    file = Attribute("BlobWrapper or NamedFile")
    file_length = Attribute("File size")
    file_type = Attribute("File mime type")
    blob = Attribute("ZODB blob")
    filename = Attribute("Filename")
