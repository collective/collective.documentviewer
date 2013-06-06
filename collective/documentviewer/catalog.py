from Products.ATContentTypes.interface import IFileContent
from plone.indexer import indexer
from collective.documentviewer.settings import Settings


@indexer(IFileContent)
def SearchableText(obj):
    """
    Override searchable text to also
    provide the ocr'd text
    """
    text = obj.SearchableText()
    if obj.getLayout() != 'documentviewer':
        return ''

    settings = Settings(obj)
    catalog = settings.catalog
    if catalog is not None:
        index = catalog['text'].index
        return [text, ' '.join(index._lexicon.words())]
    else:
        return text
