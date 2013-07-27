from plone.indexer import indexer
from collective.documentviewer.settings import Settings


def SearchableTextIndexer(obj):
    """
    Override searchable text to also
    provide the ocr'd text
    """
    text = obj.SearchableText()
    if obj.getLayout() != 'documentviewer':
        return text

    settings = Settings(obj)
    catalog = settings.catalog
    if catalog is not None:
        index = catalog['text'].index
        return [text, ' '.join(index._lexicon.words())]
    else:
        return text

try:
    from Products.ATContentTypes.interface import IFileContent

    @indexer(IFileContent)
    def SearchableTextArchetypes(obj):
        return SearchableTextIndexer(obj)
except ImportError:
    pass

try:
    from plone.app.contenttypes.interfaces import IFile

    @indexer(IFile)
    def SearchableTextDexterity(obj):
        return SearchableTextIndexer(obj)
except ImportError:
    pass
