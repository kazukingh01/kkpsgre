from setuptools import setup, find_packages

packages = find_packages(
        where='.',
        include=['kkpsgre*']
)

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='kkpsgre',
    version='1.2.13',
    description='augmentation wrapper package for albumentations',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kazukingh01/kkpsgre",
    author='Kazunoki',
    author_email='kazukingh01@gmail.com',
    license='Public License',
    packages=packages,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Private License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'psycopg2-binary==2.9.9',
        'pandas>=2.2.1',
        'numpy>=1.26.4',
        'joblib>=1.3.2',
        'setuptools>=62.0.0',
        'wheel>=0.37.0',
        'mysql-connector-python==9.0.0',
    ],
    python_requires='>=3.12.2'
)
