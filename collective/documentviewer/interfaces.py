from zope.schema.vocabulary import SimpleVocabulary
from zope.interface import Interface
from zope import schema


class ILayer(Interface):
    """
    layer class
    """


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
    # XXX try to detect default var location
    storage_location = schema.TextLine(
        title=u"Storage location",
        default=u"../var/dvpdffiles")
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
    override_contributor = schema.TextLine(
        title=u"Override Contributor",
        description=u"What to override the contributor field on viewer with."
                    u"Leave blank to use document owner")
    override_organization = schema.TextLine(
        title=u"Override Contributor Organization",
        description=u"What to override the organization field on viewer with."
                    u"Leave blank to use site title.")
    height = schema.Int(
        title=u"Viewer Height",
        description=u"Default height to use for viewer(only for "
                    u"non-fullscreen mode).",
        default=500)
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
