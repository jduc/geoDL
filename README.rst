**************************************************
geoDL
**************************************************

**Please note that geoDL is in beta version, therefore expect bugd and updates**

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

    $ pip install --user geoDL


Note it is possible that the flag `--pre` is needed for installing the beta version.

Usage
-------

.. code-block:: bash

    usage: geoDL.py [-h] [--dry] [--samples [SAMPLES [SAMPLES ...]]] [--colname COLNAME]
                    {geo,meta,ena} GSE|metadata|ENA

  {geo,meta,ena}        Specify which type of input
  GSE|metadata|ENA      geo:  GSE accession number, eg: GSE13373
                              Map the GSE accession to the ENA study accession and fetch the metadata

                        meta: Use metadata file instead of fetching it on ENA website (bypass GEO)
                              Meta data should include at minima the following columns: ['Fastq files
                              (ftp)', 'Submitter's sample name']

                        ena:  ENA study accession number, eg: PRJEB13373
                              Fetch the metadata directely on the ENA website

    optional arguments:
      -h, --help            show this help message and exit
      --dry                 Don't actually download anything, just print the wget
                            cmds
      --samples [SAMPLES [SAMPLES ...]]
                            Space separated list of GSM samples to download. For
                            ENA mode, subset the metadata
      --colname COLNAME     Name of the column to use in the metadata file to name
                            the samples


Example
-------
Download metadata and all the samples of the serie GSE13373 and rename them to their sample names:

.. code-block:: bash

    $ geoDL geo GSE13373

Download only some samples:

.. code-block:: bash

    $ geoDL GSE13373 -s GSM00001 GSM00003

Download use a pre downloaded metadata and use column run_alias as name for the samples: 

.. code-block:: bash

    $ geoDL meta my_metadata.txt --column run_alias


Use a ENA code instead of a GSE code:

.. code-block:: bash

    $ geoDL ena PRJEB13373

Beta test
---------
- Test install on MacOSx and Linux
- Test python2 support
- Test handling of wget
- Test a bunch of different GSE

Changelog
---------

`changelog <changelog.md>`_

