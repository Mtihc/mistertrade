from setuptools import setup
import os

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
  return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name='mistertrade',
  version='0.1',
  description='Combine the power of multiple crypto currency exchanges',
  long_description=read('README.md'),
  url='https://github.com/Mtihc/mistertrade',
  author='Mtihc',
  author_email='mitchstoffels@gmail.com',
  license='MIT',
  packages=['mistertrade'],
  python_requires='>=2.7',
  install_requires=[
    'requests >= 2.18.4',
    'PyYaml >= 3.12'
  ],
  entry_points={
    "console_scripts": [
      "mistertrade = mistertrade:main"
    ]
  }
)
