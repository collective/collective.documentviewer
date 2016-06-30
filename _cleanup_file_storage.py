from AccessControl.SecurityManagement import newSecurityManager
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.storage import getResourceDirectory
from plone.app.uuid.utils import uuidToObject
from zope.component.hooks import setSite

import argparse
import os
import shutil


parser = argparse.ArgumentParser(
    description='Generate Gruntfile.js from Plone site')
parser.add_argument('--site-id', dest='siteid', default='Plone',
                    help='Some scripts care about site id')
parser.add_argument('--commit', dest='commit', type=bool, default=False,
                    help='Some scripts care about site id')
args, _ = parser.parse_known_args()

site_id = args.siteid
site = app[site_id]  # noqa

setSite(site)

user = app.acl_users.getUser('admin')  # noqa
newSecurityManager(None, user.__of__(app.acl_users))  # noqa


gsettings = GlobalSettings(site)

stats = {
    'keep': 0,
    'remove': 0,
    'total': 0,
    'obfuscated': 0
}

obfuscated_paths = {}
obfuscated_uids = []
for brain in site.portal_catalog(portal_type='File'):
    stats['total'] += 1
    obj = brain.getObject()
    settings = Settings(obj)
    if settings.obfuscated_filepath:
        stats['obfuscated'] += 1
        settings.obfuscate_secret
        storage_dir = getResourceDirectory(gsettings=gsettings,
                                           settings=settings)
        secret_dir = os.path.join(storage_dir, settings.obfuscate_secret)
        obfuscated_paths[secret_dir] = brain.UID
        obfuscated_uids.append(brain.UID)


def process_directory(directory):
    for sub_directory in os.listdir(directory):
        if '@@' in sub_directory:
            continue
        sub_directory_path = os.path.join(directory, sub_directory)
        if not os.path.isdir(sub_directory_path):
            continue
        if sub_directory_path in obfuscated_paths:
            # private, obfuscated path
            continue
        if sub_directory in obfuscated_uids:
            continue

        if len(sub_directory) > 10:
            # check if UID
            obj = uuidToObject(sub_directory)
            if obj is None:
                stats['remove'] += 1
                print('Could not find object related to: ' + sub_directory_path)
                if args.commit:
                    shutil.rmtree(sub_directory_path)
                    continue
            else:
                stats['keep'] += 1
        process_directory(sub_directory_path)


process_directory(gsettings.storage_location)

print('Total files %i' % stats['total'])
print('Total Obfuscated %i' % stats['obfuscated'])
print('Removed %i directories' % stats['remove'])
print('Kept %i directories' % stats['keep'])
