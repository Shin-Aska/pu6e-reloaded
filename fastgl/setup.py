from distutils.core import setup, Extension
import os

if os.name == "posix":
	libs = ['GL']
else:
	libs = ['opengl32']

module1 = Extension('fastgl',
                    libraries = libs,
                    sources = ['fastgl.c'])

setup (name = 'PackageName',
	version = '1.0',
	description = 'fastgl package',
	ext_modules = [module1])
