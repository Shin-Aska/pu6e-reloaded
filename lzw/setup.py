from distutils.core import setup, Extension

module1 = Extension('_lzw',
                    libraries = ['u6lzw'],
					include_dirs = ['../u6decode'],
					library_dirs = ['../u6decode'],
                    sources = ['lzw_wrap.c'])

setup (name = 'lzw',
	version = '1.0',
	description = 'libu6lzw interface package',
	ext_modules = [module1],
	scripts = ['lzw.py'])
