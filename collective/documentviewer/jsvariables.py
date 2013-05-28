from zope.publisher.browser import BrowserView
from zope.i18n import translate

TEMPLATE = """\
var dv_translated_label_zoom = '%(dv_translated_label_zoom)s';
var dv_translated_label_page = '%(dv_translated_label_page)s';
var dv_translated_label_of = '%(dv_translated_label_of)s';
var dv_translated_label_document = '%(dv_translated_label_document)s';
var dv_translated_label_pages = '%(dv_translated_label_pages)s';
var dv_translated_label_notes = '%(dv_translated_label_notes)s';
var dv_translated_label_text = '%(dv_translated_label_text)s';
var dv_translated_label_loading = '%(dv_translated_label_loading)s';
var dv_translated_label_search = '%(dv_translated_label_search)s';
var dv_translated_label_for = '%(dv_translated_label_for)s';
var dv_translated_label_previous = '%(dv_translated_label_previous)s';
var dv_translated_label_next = '%(dv_translated_label_next)s';
var dv_translated_label_close = '%(dv_translated_label_close)s';
var dv_translated_label_remove = '%(dv_translated_label_remove)s';
var dv_translated_label_link_to_note = '%(dv_translated_label_link_to_note)s';
var dv_translated_label_previous_annotation = '%(dv_translated_label_previous_annotation)s';
var dv_translated_label_next_annotation = '%(dv_translated_label_next_annotation)s';
"""


class JSVariables(BrowserView):

    def __call__(self, *args, **kwargs):
        request = self.request
        response = request.response
        response.setHeader('content-type', 'text/javascript;;charset=utf-8')

        d = 'collective.documentviewer'
        r = request
        dv_translated_label_zoom = translate('js_label_zoom', domain=d, context=r, default='Zoom')
        dv_translated_label_page = translate('js_label_page', domain=d, context=r, default='Page')
        dv_translated_label_of = translate('js_label_of', domain=d, context=r, default='of')
        dv_translated_label_document = translate('js_label_document', domain=d, context=r, default='Document')
        dv_translated_label_pages = translate('js_label_pages', domain=d, context=r, default='Pages')
        dv_translated_label_notes = translate('js_label_notes', domain=d, context=r, default='Notes')
        dv_translated_label_loading = translate('js_label_loading', domain=d, context=r, default='Loading')
        dv_translated_label_text = translate('js_label_text', domain=d, context=r, default='Text')
        dv_translated_label_search = translate('js_label_search', domain=d, context=r, default='Search')
        dv_translated_label_for = translate('js_label_for', domain=d, context=r, default='for')
        dv_translated_label_previous = translate('js_label_previous', domain=d, context=r, default='Previous')
        dv_translated_label_next = translate('js_label_next', domain=d, context=r, default='Next')
        dv_translated_label_close = translate('js_label_close', domain=d, context=r, default='Close')
        dv_translated_label_remove = translate('js_label_remove', domain=d, context=r, default='Remove')
        dv_translated_label_link_to_note = translate('js_label_link_to_note',
                                                     domain=d,
                                                     context=r,
                                                     default='Link to this note')
        dv_translated_label_previous_annotation = translate('js_label_previous_annotation',
                                                            domain=d,
                                                            context=r,
                                                            default='Previous annotation')
        dv_translated_label_next_annotation = translate('js_label_next_annotation',
                                                        domain=d,
                                                        context=r,
                                                        default='Next annotation')

        # escape_for_js
        dv_translated_label_zoom = dv_translated_label_zoom.replace("'", "\\'")
        dv_translated_label_page = dv_translated_label_page.replace("'", "\\'")
        dv_translated_label_of = dv_translated_label_of.replace("'", "\\'")
        dv_translated_label_document = dv_translated_label_document.replace("'", "\\'")
        dv_translated_label_pages = dv_translated_label_pages.replace("'", "\\'")
        dv_translated_label_notes = dv_translated_label_notes.replace("'", "\\'")
        dv_translated_label_loading = dv_translated_label_loading.replace("'", "\\'")
        dv_translated_label_text = dv_translated_label_text.replace("'", "\\'")
        dv_translated_label_search = dv_translated_label_search.replace("'", "\\'")
        dv_translated_label_for = dv_translated_label_for.replace("'", "\\'")
        dv_translated_label_previous = dv_translated_label_previous.replace("'", "\\'")
        dv_translated_label_next = dv_translated_label_next.replace("'", "\\'")
        dv_translated_label_close = dv_translated_label_close.replace("'", "\\'")
        dv_translated_label_remove = dv_translated_label_remove.replace("'", "\\'")
        dv_translated_label_link_to_note = dv_translated_label_link_to_note.replace("'", "\\'")
        dv_translated_label_previous_annotation = dv_translated_label_previous_annotation.replace("'", "\\'")
        dv_translated_label_next_annotation = dv_translated_label_next_annotation.replace("'", "\\'")

        return TEMPLATE % dict(
            dv_translated_label_zoom=dv_translated_label_zoom,
            dv_translated_label_page=dv_translated_label_page,
            dv_translated_label_of=dv_translated_label_of,
            dv_translated_label_document=dv_translated_label_document,
            dv_translated_label_pages=dv_translated_label_pages,
            dv_translated_label_notes=dv_translated_label_notes,
            dv_translated_label_loading=dv_translated_label_loading,
            dv_translated_label_text=dv_translated_label_text,
            dv_translated_label_search=dv_translated_label_search,
            dv_translated_label_for=dv_translated_label_for,
            dv_translated_label_previous=dv_translated_label_previous,
            dv_translated_label_next=dv_translated_label_next,
            dv_translated_label_close=dv_translated_label_close,
            dv_translated_label_remove=dv_translated_label_remove,
            dv_translated_label_link_to_note=dv_translated_label_link_to_note,
            dv_translated_label_previous_annotation=dv_translated_label_previous_annotation,
            dv_translated_label_next_annotation=dv_translated_label_next_annotation,
        )
