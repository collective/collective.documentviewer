from zope.annotation.interfaces import IAnnotations
from ZODB.blob import Blob
from BTrees.OOBTree import OOBTree
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
from collective.documentviewer.utils import getDocumentType
import re
import transaction
from plone.app.blob.utils import openBlob
import traceback

word_re = re.compile('\W+')
logger = getLogger('collective.documentviewer')

DUMP_FILENAME = 'dump.pdf'
TEXT_REL_PATHNAME = 'text'
# so we know to resync and do savepoints
LARGE_PDF_SIZE = 40


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
            text = unicode(text, errors='ignore').encode('utf-8')
            # let's strip out the ugly...
            text = word_re.sub(' ', text).strip()
            return ' '.join([word for word in text.split() if len(word) > 3])
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


class BaseSubProcess(object):
    default_paths = ['/bin', '/usr/bin', '/usr/local/bin']
    bin_name = ''

    def __init__(self):
        binary = self._findbinary()
        self.binary = binary
        if binary is None:
            raise IOError("Unable to find %s binary" % self.bin_name)

    def _findbinary(self):
        import os
        if 'PATH' in os.environ:
            path = os.environ['PATH']
            path = path.split(os.pathsep)
        else:
            path = self.default_paths
        for dir in path:
            fullname = os.path.join(dir, self.bin_name)
            if os.path.exists(fullname):
                return fullname
        return None

    def _run_command(self, cmd):
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        output = process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        return output


class MD5SubProcess(BaseSubProcess):
    """
    To get md5 hash of files on the filesystem so
    large files do not need to be loaded into
    memory to be checked
    """
    if os.name == 'nt':
        bin_name = 'md5.exe'
    else:
        bin_name = 'md5'

    def get(self, filepath):
        cmd = "%s %s" % (self.binary, filepath)
        hash = self._run_command(cmd)
        return hash.split('=')[1].strip()

try:
    md5 = MD5SubProcess()
except IOError:
    logger.exception("No md5 installed. collective.documentviewer "
                     "Will check for md5sum.")
    md5 = None


class MD5SumSubProcess(BaseSubProcess):
    """
    To get md5 hash of files on the filesystem so
    large files do not need to be loaded into
    memory to be checked
    """
    if os.name == 'nt':
        bin_name = 'md5sum.exe'
    else:
        bin_name = 'md5sum'

    def get(self, filepath):
        cmd = "%s %s" % (self.binary, filepath)
        hash = self._run_command(cmd)
        return hash.split('  ')[0].strip()

try:
    if md5 is None:
        md5 = MD5SumSubProcess()
except IOError:
    logger.exception("No md5sum or md5 installed. collective.documentviewer "
                     "will not be able to detect if the pdf has "
                     "already been converted")
    md5 = None


class TextCheckerSubProcess(BaseSubProcess):
    if os.name == 'nt':
        bin_name = 'pdffonts.ext'
    else:
        bin_name = 'pdffonts'

    font_line_marker = '%s %s --- --- --- ---------' % (
        '-' * 36, '-' * 17)

    def has(self, filepath):
        cmd = "%s %s" % (self.binary, filepath)
        output = self._run_command(cmd)
        if not isinstance(output, basestring):
            return False
        lines = output.splitlines()
        if len(lines) < 3:
            return False
        try:
            index = lines.index(self.font_line_marker)
        except:
            return False
        return len(lines[index + 1:]) > 0


try:
    textChecker = TextCheckerSubProcess()
except IOError:
    logger.exception("No pdffonts installed. collective.documentviewer "
                     "will not be able to detect if the pdf already"
                     "contains text")
    textChecker = None


class DocSplitSubProcess(BaseSubProcess):
    """
    idea of how to handle this shamelessly
    stolen from ploneformgen's gpg calls
    """

    if os.name == 'nt':
        bin_name = 'docsplit.exe'
    else:
        bin_name = 'docsplit'

    def dump_images(self, filepath, output_dir, sizes, format):
        # docsplit images pdf.pdf --size 700x,300x,50x
        # --format gif --output
        cmd = "%s images %s --size %s --format %s --rolling --output %s" % (
            self.binary, filepath,
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
            self.binary, filepath,
            not ocr and 'no-' or '',
            output_dir)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        # XXX Check for error..

    def get_num_pages(self, filepath):
        cmd = "%s length %s" % (self.binary, filepath)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        result = process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)
        return int(result.strip())

    def convert_to_pdf(self, filepath, filename, output_dir):
        inputfilepath = os.path.join(output_dir, filename)
        shutil.move(filepath, inputfilepath)
        cmd = "%s pdf %s --output %s" % (self.binary, inputfilepath,
                                         output_dir)
        logger.info("Running command %s" % cmd)
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        process.communicate()[0]
        logger.info("Finished Running Command %s" % cmd)

        # remove original
        os.remove(inputfilepath)

        # move the file to the right location now
        files = os.listdir(output_dir)
        if len(files) != 1:
            raise Exception("Error converting to pdf")
        converted_path = os.path.join(output_dir, files[0])
        shutil.move(converted_path, os.path.join(output_dir, DUMP_FILENAME))

    def convert(self, output_dir, inputfilepath=None, filedata=None,
                converttopdf=False, sizes=(('large', 1000),), ocr=True,
                detect_text=True, format='gif', filename=None):
        if inputfilepath is None and filedata is None:
            raise Exception("Must provide either filepath or filedata params")
        path = os.path.join(output_dir, DUMP_FILENAME)
        if inputfilepath is not None:
            # copy file to be able to work with.
            shutil.copy(inputfilepath, path)
        else:
            fi = open(path, 'wb')
            fi.write(filedata)
            fi.close()
        if converttopdf:
            self.convert_to_pdf(path, filename, output_dir)

        self.dump_images(path, output_dir, sizes, format)
        if ocr and detect_text and textChecker is not None:
            if textChecker.has(path):
                logger.info('Text already found in pdf. Skipping OCR.')
                ocr = False
        self.dump_text(path, output_dir, ocr)
        num_pages = self.get_num_pages(path)

        os.remove(path)
        return num_pages

try:
    docsplit = DocSplitSubProcess()
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


class Converter(object):

    def __init__(self, context):
        self.context = aq_inner(context)
        self.settings = Settings(self.context)
        field = self.context.getField('file') or context.getPrimaryField()
        wrapper = field.get(self.context)
        self.blob = wrapper.getBlob()
        self.initialize_blob_filepath()
        self.filehash = None

    def initialize_filehash(self):
        if md5 is not None and self.filehash is None and self.blob_filepath:
            try:
                self.filehash = md5.get(self.blob_filepath)
            except IndexError:
                pass

    @property
    def can_convert(self):
        modified = DateTime(self.settings.last_updated) < \
            DateTime(self.context.ModificationDate())
        if modified and md5 and self.blob_filepath is not None and \
                self.settings.filehash is not None and \
                not self.settings.converting:
            # okay, it's been modified and we have the md5
            # library, check the hash now
            self.initialize_filehash()
            return self.filehash != self.settings.filehash
        else:
            return modified

    def get_storage_dir(self):
        if self.gsettings.storage_type == 'Blob':
            storage_dir = tempfile.mkdtemp()
        else:
            storage_dir = os.path.join(self.gsettings.storage_location,
                                       self.context.UID())
            if not os.path.exists(storage_dir):
                os.mkdir(storage_dir)
        return storage_dir

    def initialize_catalog(self):
        """
        Always set a new catalog to restart the
        search weights
        """
        self.settings.catalog = CatalogFactory()

    def run_conversion(self):
        context = self.context
        gsettings = self.gsettings
        field = context.getField('file') or context.getPrimaryField()
        args = dict(sizes=(('large', gsettings.large_size),
                       ('normal', gsettings.normal_size),
                       ('small', gsettings.thumb_size)),
                ocr=gsettings.ocr,
                detect_text=gsettings.detect_text,
                format=gsettings.pdf_image_format,
                converttopdf=self.doc_type.requires_conversion,
                filename=field.getFilename(context))
        if self.blob_filepath is None:
            args['filedata'] = str(field.get(context).data)
        else:
            args['inputfilepath'] = self.blob_filepath
        return docsplit.convert(self.storage_dir, **args)

    def index_pdf(self, pages):
        logger.info('indexing pdf %s' % repr(self.context))
        catalog = self.settings.catalog
        text_dir = os.path.join(self.storage_dir, TEXT_REL_PATHNAME)
        dump_path = DUMP_FILENAME.rsplit('.', 1)[0]
        for page_num in range(1, pages + 1):
            filepath = os.path.join(text_dir, "%s_%i.txt" % (
                dump_path, page_num))
            page = Page(page_num, filepath)
            catalog.index_doc(page_num, page)

    def handle_storage(self):
        gsettings = self.gsettings
        storage_dir = self.storage_dir
        settings = self.settings
        context = self.context
        if self.gsettings.storage_type == 'Blob':
            logger.info('setting blob data for %s' % repr(context))
            # go through temp folder and move items into blob storage
            files = OOBTree()
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

    def sync_db(self):
        try:
            self.context._p_jar.sync()
        except AttributeError:
            # ignore, probably in a unit test
            pass

    def initialize_blob_filepath(self):
        try:
            opened = openBlob(self.blob)
            self.blob_filepath = opened.name
            opened.close()
        except IOError:
            self.blob_filepath = None

    def savepoint(self):
        # every savepoint will move the file descriptor
        # so we need to reset it.
        savepoint = transaction.savepoint()
        self.initialize_blob_filepath()
        return savepoint

    def handle_layout(self):
        """
        This will check if the file does not have the
        document viewer display selected.

        In addition, if the currently selected display
        is for wc.pageturner, we'll clean out the annotations
        from that product. Additionally, we'll also look
        for wildcard.pdfpal related values.
        """
        current = self.context.getLayout()
        if current != 'documentviewer':
            self.context.layout = 'documentviewer'
            # remove page turner related
            if current == 'page-turner':
                annotations = IAnnotations(self.context)
                data = annotations.get('wc.pageturner', None)
                if data:
                    del annotations['wc.pageturner']

            # remove pdfpal related
            field = self.context.getField('ocrText')
            if field:
                field.set(self.context, '')

            data = annotations.get('wildcard.pdfpal', None)
            if data:
                del annotations['wildcard.pdfpal']

    def __call__(self):
        settings = self.settings
        self.gsettings = GlobalSettings(getSite())
        self.storage_dir = self.get_storage_dir()
        self.doc_type = getDocumentType(self.context,
            self.gsettings.auto_layout_file_types)

        savepoint = None
        try:
            pages = self.run_conversion()
            if pages > LARGE_PDF_SIZE:
                # conversion can take a long time.
                # let's sync before we save the changes
                self.sync_db()
                self.initialize_catalog()
                savepoint = self.savepoint()
                self.index_pdf(pages)
                savepoint = self.savepoint()
            else:
                self.initialize_catalog()
                self.index_pdf(pages)
            self.handle_storage()
            self.handle_layout()
            settings.num_pages = pages
            settings.successfully_converted = True
            settings.storage_type = self.gsettings.storage_type
            settings.pdf_image_format = self.gsettings.pdf_image_format
            self.context.reindexObject(idxs=['SearchableText'])
            # store hash of file
            self.initialize_filehash()
            self.settings.filehash = self.filehash
            result = 'success'
        except:
            if savepoint is not None:
                savepoint.rollback()
            logger.exception('Error converting PDF:\n%s' % (
                traceback.format_exc()))
            settings.successfully_converted = False
            result = 'failure'
        settings.last_updated = DateTime().ISO8601()
        settings.converting = False
        return result


def runConversion(context):
    """
    Create document viewer files
    """
    converter = Converter(context)
    return converter()
