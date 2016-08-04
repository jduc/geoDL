**************************************************
geoDL
**************************************************

**Please note that geoDL is in beta version, though expect bug and updates**

.. image:: geoDL/logo.png
    :height: 100px
    :width: 200px
    :align: center

geoDL is a python program to download FASTQ files from `GEO-NCBI <http://www.ncbi.nlm.nih.gov/geo/>`_. The program inputs a #GEO access number and perform a search on the `EMBL-EBI/ENA <http://www.ebi.ac.uk/ena/data/warehouse/search>`_ website to gather metadata and download FASTQ files. The metadata are used to rename the samples with the experiment sample names (rather than the SRR numbers).

Dependencies
------------
- geoDL should work with both **Python3** and **Python2** but test have to be run still
- **Beautifulsoup4**, **colorama** and **six** python package are required
- **wget** is used internally and thus is a dependency of geoDL

Install
-------
On linux and MacOSx

.. code-block:: bash

    $ sudo pip install geoDL

Usage
-------
.. code-block:: bash

    usage: geoDL [-h] [-m] [-d] [-s [SAMPLES [SAMPLES ...]]] GSE

``GSE`` is a GEO accession number, eg: GSE13373

optional arguments:

    -h, --help      show help message and exit
    -m, --meta      Use metadata file instead of fetching it on EBI website
    -d, --dry       Don't actually download anything, just print the wget commands
    -s, --samples   Space separated list of GSM samples to download


Example
-------
Download metadata and all the samples of the serie GSE13373 and rename them to their sample names:

.. code-block:: bash

    $ geoDL GSE13373

Download only some samples:

.. code-block:: bash

    $ geoDL GSE13373 -s GSM00001 GSM00003

Beta test
---------
- Test install on MacOSx and Linux
- Test python2 support
- Test handling of wget
- Test a bunch of different GSE

Changelog
---------

`changelog <changelog.md>`_

