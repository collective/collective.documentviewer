from collective.documentviewer import _


class DocType(object):

    def __init__(self, name, extensions, requires_conversion=True):
        self.name = name
        self.extensions = extensions
        self.requires_conversion = requires_conversion


CONVERTABLE_TYPES = {
    'pdf': DocType(_(u'PDF'), ('pdf',), False),
    'word': DocType(_(u'Word Document'), ('doc', 'docx', 'dot', 'wiz',
                                          'odt', 'sxw', 'wks', 'wpd',
                                          'vor', 'sdw')),
    'excel': DocType(_(u'Excel File'), ('xls', 'xlsx', 'xlt', 'ods', 'csv', )),
    'ppt': DocType(_(u'Powerpoint'), ('ppt', 'pptx', 'pps', 'ppa', 'pwz',
                                      'odp', 'sxi')),
    'html': DocType(_(u'HTML File'), ('htm', 'html', 'xhtml')),
    'rft': DocType(_(u'RTF'), ('rtf',)),
    'ps': DocType(_(u'PS Document'), ('ps', 'eps', 'ai')),
    'photoshop': DocType(_(u'Photoshop'), ('psd',)),
    'visio': DocType(_(u'Visio'), ('vss', 'vst', 'vsw', 'vsd')),
    'palm': DocType(_(u'Aportis Doc Palm'), ('pdb',)),
    'txt': DocType(_(u'Plain Text File'), ('txt', )),
    'image': DocType(_(u'Images'), ('jpg', 'jpeg', 'png',
                                    'gif', 'bmp',
                                    'tif', 'tiff', )),
}

EXTENSION_TO_ID_MAPPING = {}

for type_id, doc in CONVERTABLE_TYPES.items():
    for ext in doc.extensions:
        EXTENSION_TO_ID_MAPPING[ext] = type_id


GROUP_VIEW_DISPLAY_TYPES = (
    'Folder',
    'Large Plone Folder',
    'Plone Site',
    'Topic'
)
