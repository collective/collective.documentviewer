Introduction
============

This package integrates documentcloud's viewer and pdf processing
into plone.

Example viewer: https://www.documentcloud.org/documents/19864-goldman-sachs-internal-emails

Features
--------

 - very nice document viewer
 - OCR
 - Searchable on OCR text
 - works with many different document types
 - plone.app.async integration with task monitor
 - lots of configuration options
 - PDF Album view for display groups of PDFs


Works with
----------

Besides displaying PDFs, it will also display:

 - Word
 - Excel
 - Powerpoint
 - HTML
 - RTF


Install requirements
--------------------

 - docsplit: http://documentcloud.github.com/docsplit/
 - graphicsmagick
 - ghostscript
 - poppler
 - tesseract
 - pdftk
 - openoffice(for doc, excel, ppt, etc types)


Async Integration
-----------------

It it highly recommended to install and configure plone.app.async
in combination with this package. Doing so will manage all pdf
conversions processes asynchronously so the user isn't delayed
so much when saving files.


Settings
--------

The product can be configured via a control panel item
`Document Viewer Settings`.

Some interesting configuration options:

Storage Type
    If you want to be able to serve you files via amazon cloud, 
    this will allow you to store the data in flat files that
    can be synced to another server.
Storage Location
    Where are the server to store the files.
OCR
    Use tesseract to scan the document for text. This process ca be
    slow so if your pdfs do not need to be OCR'd, you may disable.
Auto Select Layout
    For pdf files added to the site, automatically select the
    document viewer display.
Auto Convert
    When pdf files are added and modified, automatically convert.


TODO
----

 - remove images after file is deleted for plain file storage
 - change folder view
    - to not do the large thumb popup
    - be able to local searchable
    - remove colorbox(just a holdover from pdfpal)
    - placeholder for missing pdfs
 - handle very large PDFs
    - try to not load into memory--use file handlers if possible
    - get zodb blob file handle
 - be able to cancel jobs
    - remove from queue
 - in converting status message, provide link to queue management
 - reject converting pdf if too large and no async support provided
