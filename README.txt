Introduction
============

This package integrates documentcloud's viewer and pdf processing
into plone.

Example viewer: https://www.documentcloud.org/documents/19864-goldman-sachs-internal-emails


Install requirements
--------------------

 - docsplit: http://documentcloud.github.com/docsplit/
    - graphicsmagick
    - ghostscript
    - poppler
    - tesseract
    - pdftk
    - openoffice


 TODO
 ----

  - add text back to pdf(necessary?)
    - slow...
  - be able to override data base url
    - for offsite storage
  - remove images after file is deleted
  - take hash of file to compare if it's already converted