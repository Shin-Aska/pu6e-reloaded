# setup.py
from distutils.core import setup
import py2exe

setup(name="pu6edit",
      scripts=["pu6e.py"],
      data_files=[ ("", ["pu6e.conf", "00README.txt", "00LICENSE.txt", "00GPL.txt", "00INSTALL.txt"] ) ]
)
