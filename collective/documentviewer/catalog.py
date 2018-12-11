from plone.indexer import indexer
from collective.documentviewer.settings import Settings
from plone.dexterity.interfaces import IDexterityContent
from plone.app.contenttypes.interfaces import IFile


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


@indexer(IDexterityContent)
def SearchableTextDexterity(obj):
    return SearchableTextIndexer(obj)


@indexer(IFile)
def SearchableTextPAC(obj):
    return SearchableTextIndexer(obj)
