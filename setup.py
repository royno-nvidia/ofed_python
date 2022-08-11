import setuptools
from setuptools import setup
requires_modules = [
        'argparse',
        're'
        ]

setup(
    name='Backport Parser',
    version='1.0.0',
    install_requires=requires_modules,
    packages=setuptools.find_packages(),
    url='https://github.com/nasr-saab/Nasr_backports_reviewer',
    license='',
    author='Nasr Saab',
    author_email='nsaab@nvidia.com',
    description='This python script take a file and read it line by line and check if the pattern is found '
                'and return the match string to the pattern ',
    python_requre='>=3',
    py_modules=['backport_module']
)
