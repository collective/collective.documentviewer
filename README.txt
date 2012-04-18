Introduction
============

This package integrates documentcloud's viewer and pdf processing
into plone.

Example viewer: https://www.documentcloud.org/documents/19864-goldman-sachs-internal-emails

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

 - add text back to pdf(necessary?)
   - slow...
 - remove images after file is deleted for plain file storage
 - take hash of file to compare if it's already converted

