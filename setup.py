from setuptools import setup, find_packages
import os

version = '6.0.2'

setup(name='collective.documentviewer',
      version=version,
      description="Document cloud's document viewer integration into plone.",
      long_description="%s\n%s" % (
          open("README.rst").read(),
          open(os.path.join("docs", "HISTORY.txt")).read()
      ),
      # Get more from https://pypi.org/classifiers/
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Environment :: Web Environment",
          "Framework :: Plone",
          "Framework :: Plone :: Addon",
          "Framework :: Plone :: 5.0",
          "Framework :: Plone :: 5.1",
          "Framework :: Plone :: 5.2",
          "Framework :: Plone",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Operating System :: OS Independent",
          ],
      keywords='plone documentviewer pdf ocr doc viewer',
      author='Nathan Van Gheem',
      author_email='vangheem@gmail.com',
      url='https://github.com/collective/collective.documentviewer',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*,!=3.5.*',
      install_requires=[
          'setuptools',
          'plone.api',
          'Products.CMFPlone',
          'zope.browserresource',
          'repoze.catalog>=0.9.0',
          'plone.app.z3cform',
          'collective.monkeypatcher',
          'plone.app.contenttypes'
      ],
      extras_require={
          'test': [
              'plone.api',
              'plone.app.testing',
              'plone.testing',
              'plone.app.contenttypes',
              'collective.celery[test]'
          ]
      },
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone

      [celery_tasks]
      documentviewer = collective.documentviewer.async_utils
      """
      )
