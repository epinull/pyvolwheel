#!/usr/bin/env python

from distutils.core import setup
import pyvolwheel

if __name__ == '__main__':
    setup(name="pyvolwheel",
          version=pyvolwheel.__version__,
          description='Volume control tray icon',
          author='epinull',
          author_email='epinull@gmail.com',
          url=pyvolwheel.__url__,
          license=pyvolwheel.__license__,
          requires=['pygtk (>=2.12)'],
          packages=['pyvolwheel'],
          scripts=['bin/pyvolwheel'],
          classifiers=['Development Status :: 3 - Alpha',
                       'Environment :: X11 Applications :: GTK',
                       'Intended Audience :: End Users/Desktop',
                       'License :: OSI Approved :: GNU General Public License (GPL)',
                       'Natural Language :: English',
                       'Operating System :: POSIX :: Linux',
                       'Topic :: Multimedia :: Sound/Audio :: Mixers'])

