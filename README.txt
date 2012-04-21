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
 - md5 or md5sum command line tool


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
Auto layout file types
    Types that should automatically be converted to document viewer


File storage integration
------------------------

If you choose to use basic file storage instead of zodb blob storage,
there are a few things you'll want to keep in mind.

1) Use nginx to then serve the file system files. This might require
   you install a local nginx just for serving file storage on the
   plone server. You can get creative with how your file storage
   is used though.

2) Since in plone's operation, it can be interrupted and the deletion
   of a file on the OS system system can not be done within a transaction,
   no files are ever deleted. However, there is an action you can
   put in a cron task to clean up your file storage directory. Just call the
   url `http://zeoinstace/plone/@@dvcleanup-filestorage`.


Upgrading from page turner
--------------------------

If you currently have page turner installed, this project will supercede 
it. Your page turner views will work but no future files added to the site
will be converted to page turner.

To convert existing view, on every page turner enabled file, there will
be a button `Document Viewer Convert` that you can click to manually
convert page turner to document viewer.

To convert all existing views, go to portal_setup in the zmi, upgrades,
select collective.documentviewer, click to show old upgrades and there
should be an `upgrade-all` step to run.


Upgrading from pdfpal
---------------------

If you want to upgrade from pdfpal, it is recommended that you simply
uninstall pdf pal.

Document viewer will disable parts of pdfpal if installed with it
otherwise. If you still want both installed, you'll need to upgrade
to at least version 0.7b5 in order for it to play nice with document
viewer.

Also, version 0.7b5 has the best uninstall support so if you're going
to uninstall the product, first upgrade your egg to 0.7b5.


TODO
----

 - check why there are some error during async operations:
    - ConflictError: database conflict error (oid 0x4d10, class BTrees.IOBTree.IOBucket, serial this txn started with 0x0395f478bc2cb377 2012-04-21 03:36:44.103425, serial currently committed 0x0395f479b09de4cc 2012-04-21 03:37:41.394556)
    - ERROR ZODB.Connection Shouldn't load state for 0x319d when the connection is closed
