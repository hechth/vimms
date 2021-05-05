from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="vimms",
    version="1.1.0",
    author="Joe Wandy, Vinny Davies, Justin J.J. van der Hooft, Stefan Weidt, Ronan Daly, Simon Rogers",
    author_email="Simon.Rogers@glasgow.ac.uk",
    description="ViMMS is an LC-MS/MS simulator.",
    long_description="ViMMS is a modular LC-MS/MS simulator framework for metabolomics that allows for real-time scan-level control of the MS2 acquisition process in-silico. ViMMS allows users to simulate and test different fragmentation strategies and obtain fragmentation files in .mzML format as output from the simulation (the entire state of the simulator can also be saved for inspection later).",
    long_description_content_type="text/markdown",
    url="https://github.com/sdrogers/vimms",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    packages=find_packages(),
    install_requires=[
        "appdirs==1.4.4",
        "argon2-cffi==20.1.0",
        "async-generator==1.10; python_version >= '3.5'",
        "atomicwrites==1.4.0; sys_platform == 'win32'",
        "attrs==20.3.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "ax-platform==0.1.20",
        "backcall==0.2.0",
        "black==19.10b0; python_version >= '3.6'",
        "bleach==3.3.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "botorch==0.4.0; python_version >= '3.7'",
        "cached-property==1.5.2",
        "cerberus==1.3.3",
        "certifi==2020.12.5",
        "cffi==1.14.5",
        "chardet==4.0.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "click==7.1.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "colorama==0.4.4; sys_platform == 'win32' and sys_platform == 'win32' and sys_platform == 'win32'",
        "cycler==0.10.0",
        "decorator==4.4.2",
        "defusedxml==0.7.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "distlib==0.3.1",
        "entrypoints==0.3; python_version >= '2.7'",
        "events==0.4",
        "flake8==3.9.1",
        "gpy==1.9.9",
        "gpytorch==1.4.1; python_version >= '3.6'",
        "greenlet==1.0.0; python_version >= '3'",
        "idna==2.10; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "importlib-metadata==4.0.1; python_version < '3.8' and python_version < '3.8'",
        "iniconfig==1.1.1",
        "intervaltree==3.1.0",
        "ipykernel==5.5.3; python_version >= '3.5'",
        "ipyparallel==6.3.0",
        "ipython==7.23.0; python_version >= '3.3'",
        "ipython-genutils==0.2.0",
        "ipywidgets==7.6.3",
        "jedi==0.18.0; python_version >= '3.6'",
        "jinja2==2.11.3; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "joblib==1.0.1",
        "json5==0.9.5",
        "jsonpickle==2.0.0",
        "jsonschema==3.2.0",
        "jupyter==1.0.0",
        "jupyter-client==6.1.12; python_version >= '3.5'",
        "jupyter-console==6.4.0; python_version >= '3.6'",
        "jupyter-core==4.7.1; python_version >= '3.6'",
        "jupyterlab==2.3.1",
        "jupyterlab-pygments==0.1.2",
        "jupyterlab-server==1.2.0; python_version >= '3.5'",
        "jupyterlab-widgets==1.0.0; python_version >= '3.6'",
        "kiwisolver==1.3.1; python_version >= '3.6'",
        "loguru==0.5.3",
        "lxml==4.6.3; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "markupsafe==1.1.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "mass-spec-utils==0.0.12",
        "matplotlib==3.4.1",
        "matplotlib-inline==0.1.2; python_version >= '3.5'",
        "mccabe==0.6.1",
        "mistune==0.8.4",
        "molmass==2020.6.10; python_version >= '3.6'",
        "nbclient==0.5.3; python_full_version >= '3.6.1'",
        "nbconvert==6.0.7; python_version >= '3.6'",
        "nbformat==5.1.3; python_version >= '3.5'",
        "nest-asyncio==1.5.1; python_version >= '3.5'",
        "networkx==2.5.1",
        "notebook==6.3.0; python_version >= '3.6'",
        "numpy==1.20.2",
        "orderedmultidict==1.0.1",
        "packaging==20.9; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pandas==1.2.4",
        "pandocfilters==1.4.3",
        "paramz==0.9.5",
        "parso==0.8.2; python_version >= '3.6'",
        "pathspec==0.8.1",
        "patsy==0.5.1",
        "pbr==5.6.0; python_version >= '2.6'",
        "pep517==0.10.0",
        "pickleshare==0.7.5",
        "pillow==8.2.0; python_version >= '3.6'",
        "pip-shims==0.5.3; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "pipenv-setup==3.1.1",
        "pipfile==0.0.2",
        "plette[validation]==0.2.3; python_version >= '2.6' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "plotly==4.14.3",
        "pluggy==0.13.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "prometheus-client==0.10.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "prompt-toolkit==3.0.18; python_full_version >= '3.6.1'",
        "psims==0.1.37",
        "py==1.10.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pycodestyle==2.7.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pycparser==2.20; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pyflakes==2.3.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "pygments==2.9.0; python_version >= '3.5'",
        "pymzml==2.4.7",
        "pyparsing==2.4.7; python_version >= '2.6' and python_version not in '3.0, 3.1, 3.2'",
        "pyrsistent==0.17.3; python_version >= '3.5'",
        "pysmiles==1.0.1",
        "pytest==6.2.3",
        "python-dateutil==2.8.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2'",
        "pytz==2021.1",
        "pywin32==300; sys_platform == 'win32'",
        "pywinpty==1.0.1; os_name == 'nt'",
        "pyzmq==22.0.3; python_version >= '3.6'",
        "qtconsole==5.1.0; python_version >= '3.6'",
        "qtpy==1.9.0",
        "regex==2021.4.4",
        "requests==2.25.1",
        "requirementslib==1.5.16; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "retrying==1.3.3",
        "scikit-learn==0.24.2",
        "scipy==1.6.3",
        "seaborn==0.11.1",
        "send2trash==1.5.0",
        "six==1.15.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2'",
        "sortedcontainers==2.3.0",
        "sqlalchemy==1.4.13; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'",
        "statsmodels==0.12.2",
        "tabulate==0.8.9",
        "terminado==0.9.4; python_version >= '3.6'",
        "testpath==0.4.4",
        "threadpoolctl==2.1.0; python_version >= '3.5'",
        "toml==0.10.2; python_version >= '2.6' and python_version not in '3.0, 3.1, 3.2'",
        "tomlkit==0.7.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "torch==1.8.1",
        "tornado==6.1; python_version >= '3.5'",
        "tqdm==4.60.0",
        "traitlets==5.0.5; python_version >= '3.7'",
        "typed-ast==1.4.3",
        "typeguard==2.12.0; python_full_version >= '3.5.3'",
        "typing-extensions==3.10.0.0; python_version < '3.8'",
        "urllib3==1.26.4; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4' and python_version < '4'",
        "vistir==0.5.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'",
        "wcwidth==0.2.5",
        "webencodings==0.5.1",
        "wheel==0.36.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'",
        "widgetsnbextension==3.5.1",
        "win32-setctime==1.0.3; sys_platform == 'win32'",
        "zipp==3.4.1; python_version < '3.8'",
    ],
)
