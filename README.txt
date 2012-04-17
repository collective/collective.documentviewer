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

TODO
----

 - add text back to pdf(necessary?)
   - slow...
 - remove images after file is deleted for plain file storage
 - take hash of file to compare if it's already converted