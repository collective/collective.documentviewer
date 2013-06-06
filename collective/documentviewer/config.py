

class DocType(object):

    def __init__(self, name, extensions, requires_conversion=True):
        self.name = name
        self.extensions = extensions
        self.requires_conversion = requires_conversion


CONVERTABLE_TYPES = {
    'pdf': DocType(u'PDF', ('pdf',), False),
    'word': DocType(u'Word Document', ('doc', 'docx', 'dot', 'wiz',
                                       'odt', 'sxw', 'wks', 'wpd',
                                       'vor', 'sdw')),
    'excel': DocType(u'Excel File', ('xls', 'xlsx', 'xlt', 'ods', 'csv', )),
    'ppt': DocType(u'Powerpoint', ('ppt', 'pptx', 'pps', 'ppa', 'pwz',
                                   'odp', 'sxi')),
    'html': DocType(u'HTML File', ('htm', 'html', 'xhtml')),
    'rft': DocType(u'RTF', ('rtf',)),
    'ps': DocType(u'PS Document', ('ps', 'eps', 'ai')),
    'photoshop': DocType(u'Photoshop', ('psd',)),
    'visio': DocType(u'Visio', ('vss', 'vst', 'vsw', 'vsd')),
    'palm': DocType(u'Aportis Doc Palm', ('pdb',)),
    'txt': DocType(u'Plain Text File', ('txt', )),
    'image': DocType(u'Images', ('jpg', 'jpeg', 'png',
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
