=========================
collective.documentviewer
=========================

``collective.documentviewer`` integrates `DocumentCloud`_ viewer and PDF processing
into `Plone`_.


Examples
========

You can be seen in action the functionality that implements this add-on
at the following sites:

- Example viewer: https://www.documentcloud.org/documents/3219331-FOIA-Request-17-OIG-015.html


Features
========

- Very nice document viewer.

- OCR.

- Searchable on OCR text.

- Works with many different document types.

- `collective.celery`_ integration.

- Lots of configuration options.

- PDF Album view for display groups of PDFs.


Works with
----------

Besides displaying PDFs, it will also display:

- Word.

- Excel.

- Powerpoint.

- HTML.

- RTF.


Translations
============

This product has been translated into

- German.

- Spanish.

- Basque.

- French.

- Italian.

- Dutch.

- Simplified Chinese.

You can contribute for any message missing or other new languages, join us at
`Plone Collective Team <https://www.transifex.com/plone/plone-collective/>`_
into *Transifex.net* service with all world Plone translators community.


Installation
============


Install requirements
--------------------

- GraphicsMagick.

- ghostscript (version 9.0 preferred).

- Poppler

- tesseract (optional)

- qpdf

- OpenOffice or LibreOffice (optional, for doc, excel, ppt, etc. types)

- md5 or md5sum command line tool.


Installation on Cent OS/Red hat
-------------------------------

Special instructions for CentOS have been contributed by Eric Tyrer.
You can access them via `the git hub repo file location <https://github.com/collective/collective.documentviewer/blob/master/CENTOS-INSTALL.rst>`_.


Installation on Debian
----------------------

Special instructions for Debian have been contributed by Leonardo J. Caballero G.
You can access them via the `git hub repo file location <https://github.com/collective/collective.documentviewer/blob/master/DEBIAN-INSTALL.rst>`_.


Issues installation
-------------------

If on a Linux/Ubuntu/Debian machine you run into an error like::

    /var/lib/gems/1.9.1/gems/docsplit-0.7.2/lib/docsplit/image_extractor.rb:51:in `exists?': can't convert nil into String (TypeError)
    from /var/lib/gems/1.9.1/gems/docsplit-0.7.2/lib/docsplit/image_extractor.rb:51:in `ensure in convert'

This is because the ruby docsplit library is having an issue with the temp
folder accesses, and removal of temp files.   Just run the following command::

    sudo chmod 1777 /tmp && sudo chmod 1777 /var/tmp

And retry the conversion of your document


Development
===========

Normal flow: ::

    git clone git@github.com:collective/collective.documentviewer.git

    cd collective.documentviewer

    virtualenv .

    bin/pip install -r requirements.txt

    bin/buildout


Async Integration
-----------------

It it highly recommended to install and configure `collective.celery`_
in combination with this package. Doing so will manage all PDF
conversions processes asynchronously so the user isn't delayed
so much when saving files.


Settings
--------

The product can be configured via a control panel item
`Document Viewer Settings`.

Some interesting configuration options:

Storage Type
    If you want to be able to serve you files via Amazon Cloud,
    this will allow you to store the data in flat files that
    can be synced to another server.
Storage Location
    Where are the server to store the files.
OCR
    Use ``tesseract`` to scan the document for text. This process can be
    slow so if your PDFs do not need to be OCR'd, you may disable.
Auto Select Layout
    For PDF files added to the site, automatically select the
    document viewer display.
Auto Convert
    When PDF files are added and modified, automatically convert.
Auto layout file types
    Types that should automatically be converted to document viewer.


Dexterity support
-----------------

If you want to use it with your own Dexterity content type. You need to edit
the ``FTI`` in ``ZMI/portal_types/yourtype`` to add "documentviewer" in
the available view methods like this: ::

    <property name="view_methods" purge="False">
      <element value="documentviewer"/>
    </property>

Also you need to set the primary field in the schema, for example: ::

    <field name="myfile" marshal:primary="true"
           type="plone.namedfile.field.NamedBlobFile">


File storage integration
------------------------

If you choose to use basic file storage instead of ZODB blob storage,
there are a few things you'll want to keep in mind.

1) Use `Nginx`_ to then serve the file system files. This might require
   you install a local Nginx just for serving file storage on the
   Plone server. You can get creative with how your file storage
   is used though.

2) Since in Plone's delete operation, it can be interrupted and the deletion
   of a file on the OS system system can not be done within a transaction,
   no files are ever deleted. However, there is an action you can
   put in a `cron`_ task to clean up your file storage directory. Just call the
   url `http://zeoinstace/plone/@@dvcleanup-filestorage`.


Upgrading from page turner
--------------------------

If you currently have page turner installed, this project will supercede 
it. Your page turner views will work but no future files added to the site
will be converted to page turner.

To convert existing view, on every page turner enabled file, there will
be a button `Document Viewer Convert` that you can click to manually
convert page turner to document viewer.

To convert all existing views, go to ``portal_setup`` in the ZMI, upgrades,
select ``collective.documentviewer``, click to show old upgrades and there
should be an `upgrade-all` step to run.


Tests status
============

This add-on is tested using Travis CI. The current status of the add-on is:

.. image:: https://travis-ci.org/collective/collective.documentviewer.svg?branch=master
   :alt: Travis CI badge
   :target: https://travis-ci.org/collective/collective.documentviewer

.. image:: http://img.shields.io/pypi/v/collective.documentviewer.svg
   :alt: PyPI badge
   :target: https://pypi.org/project/collective.documentviewer


Contribute
==========

Have an idea? Found a bug? Let us know by `opening a ticket`_.

- Issue Tracker: https://github.com/collective/collective.documentviewer/issues
- Source Code: https://github.com/collective/collective.documentviewer
- Documentation: https://www.documentcloud.org/


Authors
=======

This product was developed by Wildcard Corp. team.

.. image:: https://raw.githubusercontent.com/collective/collective.documentviewer/i18n_improvements/docs/_static/wildcardcorp_logo.png
   :height: 111px
   :width: 330px
   :alt: Produced by wildcardcorp.com
   :align: right


License
=======

The project is licensed under the GPLv2.

.. _DocumentCloud: https://www.documentcloud.org/
.. _Plone: https://plone.org/
.. _collective.celery: https://pypi.org/project/collective.celery/
.. _Nginx: https://nginx.org/
.. _cron: https://crontab.guru/
.. _`opening a ticket`: https://github.com/collective/collective.documentviewer/issues
