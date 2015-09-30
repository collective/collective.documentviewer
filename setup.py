from setuptools import setup, find_packages
import os

version = '4.0.3'

setup(name='collective.documentviewer',
      version=version,
      description="Document cloud's document viewer integration into plone.",
      long_description="%s\n%s" % (
          open("README.rst").read(),
          open(os.path.join("docs", "HISTORY.txt")).read()
      ),
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Framework :: Plone :: 4.0",
          "Framework :: Plone :: 4.1",
          "Framework :: Plone :: 4.2",
          "Framework :: Plone :: 4.3",
          "Framework :: Plone :: 5.0",
          "Framework :: Plone",
          "Programming Language :: Python",
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
      install_requires=[
          'setuptools',
          'Products.CMFPlone',
          'zope.browserresource',
          'repoze.catalog',
          'plone.app.z3cform',
          'collective.monkeypatcher'
      ],
      extras_require={
          'test': ['plone.app.testing'],
      },
      entry_points="""
      # -*- Entry points: -*-

      [z3c.autoinclude.plugin]
      target = plone

      [celery_tasks]
      documentviewer = collective.documentviewer.async
      """
      )
