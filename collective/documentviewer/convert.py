import os
import glob
import random
import re
import shutil
import subprocess
import tempfile
import traceback
from logging import getLogger

import transaction
from Acquisition import aq_inner
from BTrees.OOBTree import OOBTree
from collective.documentviewer import storage
from collective.documentviewer.events import ConversionFinishedEvent
from collective.documentviewer.interfaces import IFileWrapper, IOCRLanguage
from collective.documentviewer.settings import GlobalSettings, Settings
from collective.documentviewer.utils import getDocumentType, mkdir_p
from DateTime import DateTime
from plone import api
from plone.app.contenttypes.behaviors.leadimage import ILeadImage
from plone.namedfile.file import NamedBlobImage
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from ZODB.blob import Blob
from zope.annotation.interfaces import IAnnotations
from zope.event import notify

word_re = re.compile(r'\W+')
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
            with open(self.filepath, 'r') as fi:
                text = fi.read()
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

    if os.name == 'nt':
        close_fds = False
    else:
        close_fds = True

    def __init__(self):
        binary = self._findbinary()
        self.binary = binary
        if binary is None:
            raise IOError("Unable to find %s binary" % self.bin_name)

    def _findbinary(self):
        if 'PATH' in os.environ:
            path = os.environ['PATH']
            path = path.split(os.pathsep)
        else:
            path = self.default_paths

        for directory in path:
            fullname = os.path.join(directory, self.bin_name)
            if os.path.exists(fullname):
                return fullname

        return None

    def _run_command(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.split()
        cmdformatted = ' '.join(cmd)
        logger.info("Running command %s" % cmdformatted)
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=self.close_fds)
        output, error = process.communicate()
        output = output.decode('utf-8')
        error = error.decode('utf-8')
        process.stdout.close()
        process.stderr.close()
        if process.returncode != 0:
            error = """Command
%s
finished with return code
%i
and output:
%s
%s""" % (cmdformatted, process.returncode, output, error)
            logger.info(error)
            raise Exception(error)
        logger.info("Finished Running Command %s" % cmdformatted)
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
        cmd = [self.binary, filepath]
        hashval = self._run_command(cmd)
        return hashval.split('=')[1].strip()


try:
    md5 = MD5SubProcess()
except IOError:
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
        cmd = [self.binary, filepath]
        hashval = self._run_command(cmd)
        return hashval.split('  ')[0].strip()


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
        bin_name = 'pdffonts.exe'
    else:
        bin_name = 'pdffonts'

    font_line_marker = '%s %s --- --- --- ---------' % (
        '-' * 36, '-' * 17)

    def has(self, filepath):
        cmd = [self.binary, filepath]
        output = self._run_command(cmd)
        if not isinstance(output, str):
            return False
        lines = output.splitlines()
        if len(lines) < 3:
            return False
        try:
            index = lines.index(self.font_line_marker)
        except Exception:
            return False
        return len(lines[index + 1:]) > 0


try:
    textChecker = TextCheckerSubProcess()
except IOError:
    logger.exception("No pdffonts installed. collective.documentviewer "
                     "will not be able to detect if the pdf already"
                     "contains text")
    textChecker = None


class QpdfSubProcess(BaseSubProcess):
    """
    This is used to both strip metadata in pdf files.
    And to strip a page for the screenshot process.
    """
    if os.name == 'nt':
        bin_name = 'qpdf.exe'
    else:
        bin_name = 'qpdf'

    @property
    def extra_parameters(self):
        """Return extra parameters that can be defined using environment variable
        `DOCUMENTVIEWER_QPDF_PARAMETERS`"""
        return os.getenv("DOCUMENTVIEWER_QPDF_PARAMETERS", "").split()

    def __call__(self, filepath):
        outfile = '{}-processed.pdf'.format(filepath[:-4])
        cmd = [self.binary, '--linearize']
        cmd.extend(self.extra_parameters)
        cmd.extend([filepath, outfile])
        self._run_command(cmd)
        shutil.copy(outfile, filepath)

    def strip_page(self, filepath, output_dir):
        output_file = os.path.join(output_dir, 'dump_%d.pdf')
        cmd = [self.bin_name, '--split-pages']
        cmd.extend(self.extra_parameters)
        cmd.extend([filepath, output_file])
        self._run_command(cmd)

    def get_num_pages(self, filepath):
        cmd = [self.binary, "--show-npages"]
        cmd.extend(self.extra_parameters)
        cmd.append(filepath)
        return int(self._run_command(cmd).strip())

    def split_pages(self, filepath, output_dir):
        output_dir = os.path.join(output_dir, TEXT_REL_PATHNAME)
        os.mkdir(output_dir)
        output_file = os.path.join(output_dir, 'dump_%d.pdf')
        cmd = [self.bin_name, '--split-pages']
        cmd.extend(self.extra_parameters)
        cmd.extend([filepath, output_file])
        self._run_command(cmd)
        return output_dir


try:
    qpdf = QpdfSubProcess()
except IOError:
    qpdf = None
    logger.warn("qpdf not installed.  Some metadata might remain in PDF files."
                "You will also not able to make screenshots")


class GraphicsMagickSubProcess(BaseSubProcess):
    """
    Allows us to create small images using graphicsmagick
    """
    if os.name == 'nt':
        bin_name = 'gm.exe'
    else:
        bin_name = 'gm'

    def dump_images(self, filepath, output_dir, sizes, format, lang='eng'):
        for size in sizes:
            output_folder = os.path.join(output_dir, size[0])
            os.makedirs(output_folder)
            try:
                qpdf.strip_page(filepath, output_folder)
            except Exception:
                raise Exception
            for filename in os.listdir(output_folder):
                # For documents whose number of pages is 2 or higher digits we need to cut out the zeros
                # at the beginning of dump the page number or the browser viewer won't work.
                output_file = filename.split('_')
                output_file[1] = output_file[1][:-4]
                output_file[1] = int(output_file[1])
                output_file = "%s_%i.%s" % (output_file[0], output_file[1], format)
                output_file = os.path.join(output_folder, output_file)
                filename = os.path.join(output_folder, filename)

                cmd = [
                    self.binary, "convert",
                    '-resize', str(size[1]) + 'x',
                    '-density', '150',
                    '-format', format,
                    filename, output_file]

                self._run_command(cmd)
                os.remove(filename)

    def convert_multiple_pdfs(self, file_list, filepath, format):
        cmd = []
        for single_file in file_list:
            output_file = single_file[:-3] + format
            cmd = [self.bin_name, "convert", single_file, output_file]
            self._run_command(cmd)
            os.remove(single_file)


try:
    gm = GraphicsMagickSubProcess()
except IOError:
    logger.exception("Graphics Magick is not installed, DocumentViewer "
                     "Will not be able to make screenshots")
    gm = None


class TesseractSubProcess(BaseSubProcess):
    """
    Uses the tesseract Optical Character Recognition to read and output
    text from images.
    """
    if os.name == 'nt':
        bin_name = 'tesseract.exe'
    else:
        bin_name = 'tesseract'

    def dump_text(self, file_list, output_dir, lang='eng'):
        gm.convert_multiple_pdfs(file_list, output_dir, 'jpeg')
        cmd = []
        file_list = glob.glob(os.path.join(output_dir, "*.jpeg"))

        for single_file in file_list:
            output_file = single_file[:-5]
            cmd = [self.bin_name, single_file, output_file, '-l', lang]
            self._run_command(cmd)
            os.remove(single_file)


try:
    tesseract = TesseractSubProcess()
except IOError:
    logger.exception("Tesseract is not installed, Documentviewer "
                     "Will not be able to convert pdfs or images to text "
                     "Using Optical Character Recognition")
    tesseract = None


class PdfToTextSubProcess(BaseSubProcess):
    """
    Uses the pdftotext utility from poppler-utils.
    """
    if os.name == 'nt':
        bin_name = 'pdftotext.exe'
    else:
        bin_name = 'pdftotext'

    def dump_text(self, filepath, output_dir, ocr, lang='eng'):
        qpdf = QpdfSubProcess()
        output_dir = qpdf.split_pages(filepath, output_dir)
        find_file = os.path.join(output_dir, "*.pdf")
        file_list = glob.glob(find_file)
        cmd = []
        if ocr:
            tesseract = TesseractSubProcess()
            tesseract.dump_text(file_list, output_dir, lang)
        else:
            for single_file in file_list:
                cmd = [self.bin_name, single_file]
                self._run_command(cmd)
                os.remove(single_file)

        # Reorder the end numbers of the files so that document viewer can pick it up.

        for single_file in os.listdir(output_dir):
            new_file = single_file
            new_file = new_file.split('_')
            new_file[1], format = new_file[1].split('.')
            new_file[1] = int(new_file[1])
            new_file = "%s_%i.%s" % (new_file[0], new_file[1], format)
            new_file = os.path.join(output_dir, new_file)
            single_file = os.path.join(output_dir, single_file)
            shutil.move(single_file, new_file)


try:
    pdftotext = PdfToTextSubProcess()
except IOError:
    logger.exception("poppler_utils are not installed. "
                     "You wil not be able to index text or "
                     "see the text dump in Document Viewer")
    pdftotext = None


class LibreOfficeSubProcess(BaseSubProcess):
    """
    Converts files of other formats into other file types using libreoffice.
    """
    if os.name == 'nt':
        bin_name = 'soffice.exe'
    else:
        bin_name = 'soffice'

    def convert_to_pdf(self, filepath, filename, output_dir):
        ext = os.path.splitext(os.path.normcase(filename))[1][1:]
        inputfilepath = os.path.join(output_dir, 'dump.%s' % ext)
        shutil.move(filepath, inputfilepath)
        orig_files = set(os.listdir(output_dir))
        # HTML takes unnecesarily too long using standard settings.
        if ext == 'html':
            cmd = [
                self.binary, '--headless', '--convert-to', 'pdf:writer_pdf_Export',
                inputfilepath, '--outdir', output_dir]
        else:
            cmd = [
                self.binary, '--headless', '--convert-to', 'pdf', inputfilepath,
                '--outdir', output_dir]
        self._run_command(cmd)

        # remove original
        os.remove(inputfilepath)

        # move the file to the right location now
        files = set(os.listdir(output_dir))

        if len(files) != len(orig_files):
            # we should have the same number of files as when we first began
            # since we removed libreoffice.
            # We do this in order to keep track of the files being created
            # and used...
            raise Exception("Error converting to pdf")

        converted_path = os.path.join(output_dir,
                                      [f for f in files - orig_files][0])
        shutil.move(converted_path, os.path.join(output_dir, DUMP_FILENAME))


try:
    loffice = LibreOfficeSubProcess()
except IOError:
    logger.exception("Libreoffice not installed, Documentviewer "
                     "will not be able to convert text files to pdf.")
    loffice = None


class DocSplitSubProcess(object):
    """
    Currently exists as a compatibility layer for older code now that
    Docsplit has been replaced.
    """

    def dump_images(self, filepath, output_dir, sizes, format, lang='eng'):
        # now exists as a compatibility layer.
        gm.dump_images(filepath, output_dir, sizes, format, lang)

    def dump_text(self, filepath, output_dir, ocr, lang='eng'):
        # Compatibility layer for pdftotext
        pdftotext.dump_text(filepath, output_dir, ocr, lang)

    def get_num_pages(self, filepath):
        return qpdf.get_num_pages(filepath)

    def convert_to_pdf(self, filepath, filename, output_dir):
        # get ext from filename
        loffice.convert_to_pdf(filepath, filename, output_dir)

    def convert(self, output_dir, inputfilepath=None, filedata=None,
                converttopdf=False, sizes=(('large', 1000),), enable_indexation=True,
                ocr=True, detect_text=True, format='gif', filename=None, language='eng'):
        sc = Safe_Convert()
        return sc.convert(output_dir, inputfilepath, filedata, converttopdf,
                          sizes, enable_indexation,
                          ocr, detect_text, format, filename, language)


docsplit = DocSplitSubProcess()


class Safe_Convert(object):
    """
    Acts as a way to safely convert the pdf.
    """

    def convert(self, output_dir, inputfilepath=None, filedata=None,
                converttopdf=False, sizes=(('large', 1000),), enable_indexation=True,
                ocr=True, detect_text=True, format='gif', filename=None, language='eng'):
        if inputfilepath is None and filedata is None:
            raise Exception("Must provide either filepath or filedata params")

        path = os.path.join(output_dir, DUMP_FILENAME)
        if os.path.exists(path):
            os.remove(path)

        if inputfilepath is not None:
            # copy file to be able to work with.
            shutil.copy(inputfilepath, path)
        else:
            fi = open(path, 'wb')
            fi.write(filedata)
            fi.close()

        if converttopdf:
            loffice.convert_to_pdf(path, filename, output_dir)

        gm.dump_images(path, output_dir, sizes, format, language)
        if enable_indexation and ocr and detect_text and textChecker is not None:
            if textChecker.has(path):
                logger.info('Text already found in pdf. Skipping OCR.')
                ocr = False

        num_pages = qpdf.get_num_pages(path)

        if enable_indexation:
            try:
                pdftotext.dump_text(path, output_dir, ocr, language)
            except Exception:
                logger.info('Error extracting text from PDF', exc_info=True)

        # We don't need to cleanup the PDF right
        # The PDF will be removed by handle_storage, which delete the tempdir.
        return num_pages


sc = Safe_Convert()


def saveFileToBlob(filepath):
    blob = Blob()
    bfile = blob.open('w')
    with open(filepath, 'rb') as fi:
        bfile.write(fi.read())
    bfile.close()
    return blob


class Converter(object):

    def __init__(self, context):
        self.context = aq_inner(context)
        self.settings = Settings(self.context)
        fw = IFileWrapper(self.context)
        self.blob = fw.blob
        self.initialize_blob_filepath()
        self.filehash = None
        self.gsettings = GlobalSettings(api.portal.get())
        self.storage_dir = self.get_storage_dir()
        self.doc_type = getDocumentType(self.context,
                                        self.gsettings.auto_layout_file_types)

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
            storage_dir = storage.getResourceDirectory(gsettings=self.gsettings,
                                                       settings=self.settings)
            if not os.path.exists(storage_dir):
                mkdir_p(storage_dir)

        return storage_dir

    def run_conversion(self):
        context = self.context
        gsettings = self.gsettings
        fw = IFileWrapper(context)
        filename = fw.filename
        language = IOCRLanguage(context).getLanguage()
        args = dict(sizes=((u'large', gsettings.large_size),
                           (u'normal', gsettings.normal_size),
                           (u'small', gsettings.thumb_size)),
                    enable_indexation=self.isIndexationEnabled(),
                    ocr=gsettings.ocr,
                    detect_text=gsettings.detect_text,
                    format=gsettings.pdf_image_format,
                    converttopdf=self.doc_type.requires_conversion,
                    language=language,
                    filename=filename)
        if self.blob_filepath is None:
            args['filedata'] = str(fw.file.data)
        else:
            args['inputfilepath'] = self.blob_filepath

        return sc.convert(self.storage_dir, **args)

    def index_pdf(self, pages, catalog):
        logger.info('indexing pdf %s' % repr(self.context))
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
        # save lead image if available
        if ILeadImage.providedBy(self.context):
            path = os.path.join(storage_dir, u'large')
            filename = os.listdir(path)
            filename.sort()
            filename = filename[0]
            filepath = os.path.join(path, filename)
            tmppath = '%s.tmp' % (filepath)

            # NamedBlobImage eventually calls blob.consume,
            # destroying the image, so we need to make a temporary copy.
            shutil.copyfile(filepath, tmppath)
            NamedBlobImagefailed = False
            with open(tmppath, 'rb') as fi:
                try:
                    self.context.image = NamedBlobImage(fi, filename=filename)
                except Exception:
                    NamedBlobImagefailed = True
            # If we are using python2 we need to recreate the file and try again
            if NamedBlobImagefailed:
                shutil.copyfile(filepath, tmppath)
                with open(tmppath, 'rb') as fi:
                    self.context.image = NamedBlobImage(fi, filename=filename.decode("utf8"))

        if self.gsettings.storage_type == 'Blob':
            logger.info('setting blob data for %s' % repr(context))
            # go through temp folder and move items into blob storage
            files = OOBTree()
            for size in (u'large', u'normal', u'small'):
                path = os.path.join(storage_dir, size)
                for file in os.listdir(path):
                    filename = '%s/%s' % (size, file)
                    filepath = os.path.join(path, file)
                    files[filename] = saveFileToBlob(filepath)

            if self.settings.enable_indexation:
                textfilespath = os.path.join(storage_dir, TEXT_REL_PATHNAME)
                for filename in os.listdir(textfilespath):
                    filepath = os.path.join(textfilespath, filename)
                    filename = '%s/%s' % (TEXT_REL_PATHNAME, filename)
                    files[filename] = saveFileToBlob(filepath)

            # Store converted PDF
            dump_pdf_path = os.path.join(storage_dir, DUMP_FILENAME)
            filename = 'pdf/%s' % DUMP_FILENAME
            files[filename] = saveFileToBlob(dump_pdf_path)

            settings.blob_files = files
            shutil.rmtree(storage_dir)

            # check for old storage to remove... Just in case.
            old_storage_dir = os.path.join(gsettings.storage_location,
                                           context.UID())
            if os.path.exists(old_storage_dir):
                shutil.rmtree(old_storage_dir)
        else:
            # if settings used to be blob, delete file data
            if settings.storage_type == 'Blob' and settings.blob_files:
                del settings._metadata['blob_files']

    def sync_db(self):
        # circular
        from collective.documentviewer.async_utils import celeryInstalled
        if celeryInstalled():
            from collective.celery.utils import getCelery
            if not getCelery().conf.task_always_eager:
                self.context._p_jar.sync()

    def initialize_blob_filepath(self):
        try:
            opened = self.blob.open('r')
            self.blob_filepath = opened.name
            opened.close()
        except (IOError, AttributeError):
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
        """
        current = self.context.getLayout()
        if current != 'documentviewer':
            self.context.layout = 'documentviewer'

    def anonCanView(self):
        can = False
        for perm in self.context.rolesOfPermission("View"):
            if perm['name'] == 'Anonymous' and perm["selected"] != "":
                can = True
                break

        return can

    def handleFileObfuscation(self):
        """
        This is in case you have serve file storage outside
        of the plone server and you have no way of doing
        permission checks. This will only work if editors
        are on the same server as the files getting stored.
        DV's file storage traverser is the only resolver
        that will know how to handle the secret location.

        Publishing content is the only way to get it out
        of this secret location.
        """
        settings = self.settings
        if not settings.obfuscate_secret:
            settings.obfuscate_secret = str(random.randint(1, 9999999999))

        storage_dir = self.storage_dir
        secret_dir = os.path.join(storage_dir,
                                  settings.obfuscate_secret)
        if self.gsettings.storage_obfuscate is True and \
                settings.storage_type == 'File' and not self.anonCanView():
            # alright, we know we should be obfuscating the path now.
            # conversions are always done on the same path structure
            # so we just move that path structure into the secret folder
            settings.obfuscated_filepath = True
            if os.path.exists(secret_dir):
                # already exists
                if len(os.listdir(secret_dir)) > 0 and \
                        len(os.listdir(storage_dir)) == 1:
                    return
            else:
                mkdir_p(secret_dir)

            for folder in os.listdir(storage_dir):
                path = os.path.join(storage_dir, folder)
                if not os.path.isdir(path) or \
                        folder == settings.obfuscate_secret:
                    continue

                newpath = os.path.join(secret_dir, folder)
                shutil.move(path, newpath)
        else:
            settings.obfuscated_filepath = False
            if os.path.exists(secret_dir):
                shutil.rmtree(secret_dir)

    def isIndexationEnabled(self):
        '''
          Return True if indexation is enabled, False either.
          The setting 'enable_indexation' can be either defined on the object
          (annotations) or if not, we take the value defined in the global settings.
        '''
        annotations = IAnnotations(self.context)['collective.documentviewer']
        if 'enable_indexation' in annotations:
            return annotations['enable_indexation']
        else:
            return self.gsettings.enable_indexation

    def __call__(self, asynchronous=True):
        settings = self.settings
        try:
            pages = self.run_conversion()
            # conversion can take a long time.
            # let's sync before we save the changes
            if asynchronous:
                self.sync_db()

            catalog = None
            # regarding enable_indexation, either take the value on the context
            # if it exists or take the value from the global settings
            if self.isIndexationEnabled():
                catalog = CatalogFactory()
                self.index_pdf(pages, catalog)
            settings.catalog = catalog
            self.handle_storage()
            self.context.reindexObject()
            self.handle_layout()
            settings.num_pages = pages
            settings.successfully_converted = True
            settings.storage_type = self.gsettings.storage_type
            settings.pdf_image_format = self.gsettings.pdf_image_format
            # store hash of file
            self.initialize_filehash()
            settings.filehash = self.filehash
            self.handleFileObfuscation()
            result = 'success'
        except Exception as ex:
            logger.exception('Error converting PDF:\n%s\n%s' % (
                getattr(ex, 'message', ''),
                traceback.format_exc()))
            settings.successfully_converted = False
            settings.exception_msg = getattr(ex, 'message', '')
            settings.exception_traceback = traceback.format_exc()
            result = 'failure'

        notify(ConversionFinishedEvent(self.context, result))
        settings.last_updated = DateTime().ISO8601()
        settings.converting = False
        return result


def runConversion(context):
    """
    Create document viewer files
    """
    converter = Converter(context)
    return converter()
