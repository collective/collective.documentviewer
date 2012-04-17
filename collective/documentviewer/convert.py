from ZODB.blob import Blob
from persistent.dict import PersistentDict
import subprocess
import os
from settings import Settings, GlobalSettings
from Acquisition import aq_inner
from DateTime import DateTime
from logging import getLogger
from zope.app.component.hooks import getSite
import shutil
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
import tempfile

logger = getLogger('collective.documentviewer')

DUMP_FILENAME = 'dump.pdf'
TEXT_REL_PATHNAME = 'text'


class Page(object):
    def __init__(self, page, filepath):
        self.page = page
        self.filepath = filepath

    @property
    def contents(self):
        if os.path.exists(self.filepath):
            fi = open(self.filepath)
            text = fi.read()
            fi.close()
            return unicode(text, errors='ignore').encode('utf-8')
        return ''


def get_text(page, default):
    return page.contents


def get_page(page, default):
    return page.page


def CatalogFactory():
    catalog = Catalog()
    catalog['text'] = CatalogTextIndex(get_text)
    catalog['page'] = CatalogFieldIndex(get_page)
    return catalog


class docsplit_subprocess:
    """
    idea of how to handle this shamelessly
    stolen from ploneformgen's gpg calls
    """
    paths = ['/bin', '/usr/bin', '/usr/local/bin']

    def __init__(self):
        if os.name == 'nt':
            bin_name = 'docsplit.exe'
        else:
            bin_name = 'docsplit'
        docsplit_binary = self._findbinary(bin_name)
        self.docsplit_binary = docsplit_binary
        if docsplit_binary is None:
            raise IOError("Unable to find docsplit binary")

    def _findbinary(self, binname):
        import os
        if 'PATH' in os.environ:
            path = os.environ['PATH']
            path = path.split(os.pathsep)
        else:
            path = self.paths
        for dir in path:
            fullname = os.path.join(dir, binname)
            if os.path.exists(fullname):
                return fullname
        return None

    def dump_images(self, filepath, output_dir, sizes, format):
        # docsplit images pdf.pdf --size 700x,300x,50x
        # --format gif --output
        cmd = "%s images %s --size %s --format %s --rolling --output %s" % (
            self.docsplit_binary, filepath,
            ','.join([str(s[1]) + 'x' for s in sizes]),
            format, output_dir)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        # XXX Check for error..

        # now, move images to correctly named folders
        for name, size in sizes:
            dest = os.path.join(output_dir, name)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            source = os.path.join(output_dir, '%ix' % size)
            shutil.move(source, dest)

    def dump_text(self, filepath, output_dir, ocr):
        # docsplit text pdf.pdf --[no-]ocr --pages all
        output_dir = os.path.join(output_dir, TEXT_REL_PATHNAME)
        cmd = "%s text %s --%socr --pages all --output %s" % (
            self.docsplit_binary, filepath,
            not ocr and 'no-' or '',
            output_dir)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        # XXX Check for error..

    def get_num_pages(self, filepath):
        cmd = "%s length %s" % (self.docsplit_binary, filepath)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        result = process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        return int(result.strip())

    def convert(self, filedata, output_dir,
                sizes=(('large', 1000),), ocr=True, format='gif'):
        path = os.path.join(output_dir, DUMP_FILENAME)
        fi = open(path, 'wb')
        fi.write(filedata)
        fi.close()

        self.dump_images(path, output_dir, sizes, format)
        self.dump_text(path, output_dir, ocr)
        num_pages = self.get_num_pages(path)

        os.remove(path)
        return num_pages

try:
    docsplit = docsplit_subprocess()
except IOError:
    logger.exception("No docsplit installed. collective.documentviewer "
                     "will not work.")
    docsplit = None


def saveFileToBlob(filepath):
    blob = Blob()
    fi = open(filepath)
    bfile = blob.open('w')
    bfile.write(fi.read())
    bfile.close()
    fi.close()
    return blob


def convert(context):
    """
    Convert PDF to Images
    """
    settings = Settings(context)

    if DateTime(settings.last_updated) < DateTime(context.ModificationDate()):
        context = aq_inner(context)
        field = context.getField('file') or context.getPrimaryField()
        site = getSite()
        gsettings = GlobalSettings(site)
        if gsettings.storage_type == 'Blob':
            storage_dir = tempfile.mkdtemp()
        else:
            storage_dir = os.path.join(gsettings.storage_location,
                                       context.UID())
            if not os.path.exists(storage_dir):
                os.mkdir(storage_dir)
        if settings.catalog is None:
            settings.catalog = CatalogFactory()

        try:
            pages = docsplit.convert(str(field.get(context).data), storage_dir,
                sizes=(('large', gsettings.large_size),
                       ('normal', gsettings.normal_size),
                       ('small', gsettings.thumb_size)),
                ocr=gsettings.ocr,
                format=gsettings.pdf_image_format)
            settings.successfully_converted = True
            settings.num_pages = pages

            logger.info('indexing pdf %s' % repr(context))
            catalog = settings.catalog
            catalog.clear()
            text_dir = os.path.join(storage_dir, TEXT_REL_PATHNAME)
            dump_path = DUMP_FILENAME.rsplit('.', 1)[0]
            for page_num in range(1, pages + 1):
                filepath = os.path.join(text_dir, "%s_%i.txt" % (
                    dump_path, page_num))
                page = Page(page_num, filepath)
                catalog.index_doc(page_num, page)

            if gsettings.storage_type == 'Blob':
                logger.info('setting blob data for %s' % repr(context))
                # go through temp folder and move items into blob storage
                files = PersistentDict()
                for size in ('large', 'normal', 'small'):
                    path = os.path.join(storage_dir, size)
                    for filename in os.listdir(path):
                        filepath = os.path.join(path, filename)
                        filename = '%s/%s' % (size, filename)
                        files[filename] = saveFileToBlob(filepath)
                textfilespath = os.path.join(storage_dir, TEXT_REL_PATHNAME)
                for filename in os.listdir(textfilespath):
                    filepath = os.path.join(textfilespath, filename)
                    filename = '%s/%s' % (TEXT_REL_PATHNAME, filename)
                    files[filename] = saveFileToBlob(filepath)
                settings.blob_files = files
                shutil.rmtree(storage_dir)

                #check for old storage to remove... Just in case.
                old_storage_dir = os.path.join(gsettings.storage_location,
                                               context.UID())
                if os.path.exists(old_storage_dir):
                    shutil.rmtree(old_storage_dir)
            else:
                # if settings used to be blob, delete file data
                if settings.storage_type == 'Blob' and settings.blob_files:
                    del settings._metadata['blob_files']
            settings.storage_type = gsettings.storage_type
        except:
            logger.exception('Error converting PDF')
            settings.successfully_converted = False
        settings.last_updated = DateTime().ISO8601()
        settings.converting = False
