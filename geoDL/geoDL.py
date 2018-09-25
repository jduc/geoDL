#!/usr/bin/env python3
"""
Download data from the ENA website using a GSE geo accession number, ENA study accession number or
metadata spreadsheet.

url: https://github.com/jduc/geoDL
author: Julien Duc <julien_dot_duc_dot_0_at_gmail_dot_com>
"""

from __future__ import print_function
import re
import sys
import argparse
import time
import csv
from bs4 import BeautifulSoup
from subprocess import call
from colorama import init, Fore
from six.moves.urllib.request import urlopen, urlretrieve
if sys.version_info >= (3, 0):
    from urllib.error import URLError
else:
    from urllib2 import URLError


__version__ = 'v1.0.b7'
logo="""
################################################################################
               ___  _
  __ _ ___ ___|   \| |
 / _` / -_) _ \ |) | |__
 \__, \___\___/___/|____|
 |___/                   {}

################################################################################
""".format(__version__)

class SmartFormatter(argparse.HelpFormatter):
    """Quick hack for formatting helper of argparse with new lines"""
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)

def raiseError(errormsg):
    print("\n" + Fore.RED + errormsg + Fore.RESET)
    sys.exit(1)


def main():
    print(Fore.BLUE + logo + Fore.RESET)

### Argument parsing
    parser = argparse.ArgumentParser(description="""Download fastq from The European Nucleotide Archive (ENA)
                                     <http://www.ebi.ac.uk/ena> website using a GSE geo
                                     <http://www.ncbi.nlm.nih.gov/geo/info/seq.html> accession, ENA
                                     study accession or a metadata file from ENA""",
                                     formatter_class=SmartFormatter, 
                                     epilog='Made with <3 at the batcave')
    parser.add_argument('mode', choices=['geo', 'meta', 'ena'],
                        help="Specify which type of input")
    parser.add_argument('inputvalue', metavar='GSE|metadata|ENA',
                        help="""R|geo:  GSE accession number, eg: GSE13373
      Map the GSE accession to the ENA study accession and fetch the metadata

meta: Use metadata file instead of fetching it on ENA website (bypass GEO)
      Meta data should include at minima the following columns: ['Fastq files
      (ftp)', 'Submitter's sample name']

ena:  ENA study accession number, eg: PRJEB13373
      Fetch the metadata directely on the ENA website""")
    parser.add_argument('--dry', action='store_true',
                        help="Don't actually download anything, just print the wget cmds")
    parser.add_argument('--samples', type=str, default=[], nargs='*',
                        help="Space separated list of GSM samples to download.\
                        For ENA mode, subset the metadata")
    parser.add_argument('--colname', type=str, default='sample_alias',
                        help="Name of the column to use in the metadata file \
                        to name the samples")
    args = parser.parse_args()
    mode = args.mode.strip()
    inputvalue = args.inputvalue
    samples = args.samples
    colname = args.colname

### Find the META table on ENA website
    if mode == 'geo':
        print('Getting correspondance table from GEO...')
        geo_url = 'http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}'.format(inputvalue)
        try:
            geo_soup = BeautifulSoup(urlopen(geo_url).read(), 'html.parser')
        except URLError:
            raiseError(' > ERROR: Could not reach GEO website... exiting!')
        geo_table_soup = geo_soup.find(text=re.compile('Samples \(\d+\)')).findNext('td')

        map_dict = {}
        all_trs = geo_table_soup.find_all('tr')
        print(Fore.GREEN + ' > Found {} samples on GEO page...'.format(len(all_trs)) + Fore.RESET)
        for tr in all_trs:
            tds = tr.find_all('td')
            map_dict[tds[0].text] = tds[1].text

        print('\nLooking for the metadata on ENA website...')
        search_url = 'http://www.ebi.ac.uk/ena/data/warehouse/search?query=%22geo_accession=%22{geo}%22%22&result=study&display=xml'.format(geo=inputvalue)
        print(search_url)
        try:
            print(' > Visiting ENA website...')
            search_soup = BeautifulSoup(urlopen(search_url).read(), 'lxml')
        except URLError:
            raiseError(' > ERROR: Page not found error at {} ... exiting!'.format(search_url))
        except bs4.FeatureNotFound:
            raiseError(' > ERROR: Module lxml not found. pip install --user lxml'.format(search_url))
        search_results = search_soup.find_all('secondary_id')

        if len(search_results) != 1:
               raiseError(' > ERROR: the XML at {} looks weird, probably missing entry!'.format(search_url))

        ena_access = search_results[0].contents[0]
        metafile = 'metadata_{}.xls'.format(inputvalue)
        urlretrieve("http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={}&result=read_run&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,sample_alias,scientific_name,instrument_model,library_layout,read_count,experiment_alias,run_alias,fastq_ftp&download=txt".format(ena_access),
                            metafile)
        print(Fore.GREEN + ' > Metafile retrieved {}!'.format(metafile) + Fore.RESET)

    elif mode == 'ena':
        metafile = 'metadata_{}.xls'.format(inputvalue)
        urlretrieve("http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={}&result=read_run&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,sample_alias,scientific_name,instrument_model,library_layout,read_count,experiment_alias,run_alias,fastq_ftp&download=txt".format(inputvalue),
                            metafile)
        print(Fore.GREEN + ' > Metafile retrieved from ENA {}!'.format(metafile) + Fore.RESET)

    elif mode == 'meta':
        print('\nUsing the {} metadata file ony (bypass GEO)...'.format(inputvalue))
        metafile = inputvalue

    # check that the column selected for naming is uniq
    with open(metafile) as f:
        reader = csv.reader(f, delimiter='\t')
        samplenames = []
        for i,row in enumerate(reader):
            if i == 0:
                if colname not in row:
                    raiseError("  > ERROR: Column {col} not in the metadata file "
                               "{meta}".format(col=colname, meta=metafile))
                for j, c in enumerate(row):
                    if c == colname:
                        idx = j
            else:
                if row[idx] in samplenames:
                    raiseError("  > ERROR: Non uniq sample names in the column {col} "
                               "of the meta file {meta}\n".format(col=colname, meta=metafile))
                samplenames.append(row[idx])

### Start the download from metadata
    print('Starting the downloads...\n')
    with open(metafile) as f, open('geoDL.logs', 'w') as log:
        for i, line in enumerate(f):
            if i == 0:
                header = [h.strip() for h in line.split('\t')]
                log.write('{} download log \n'.format(inputvalue))
                continue
            data = dict(zip(header, [sp.strip() for sp in line.split('\t')]))
            try:
                data_urls = data['fastq_ftp'].split(';')
            except KeyError:
                raiseError("  > ERROR: Fastq urls (ftp) is not in the metadata, \
                           make sure to add the column and try again.")
            if mode == 'geo' :
                m = re.search('(GSM\d+)', data[colname])
                if m is None:
                    raiseError('  > ERROR: Regexp did not match...')
                if len(m.groups()) >1:
                    raiseError('  > ERROR: Regexp matched multiple times...')
                gsm = m.group(1)
                try:
                    outname = map_dict[gsm].replace(' ', '_')
                except KeyError:
                    raiseError('  > ERROR: The GSM {} was not found in the GEO page...  exiting!'.format(gsm))
                if len(samples) > 0 and gsm not in samples:
                    continue
                log.write(gsm) +  ' --> ' +  outname + '\n'
            else:
                outname = data[colname].replace(' ', '_')
            if len(data_urls) == 2:  # paired end
                suffix = ['_R1', '_R2']
                pair = True
            elif len(data_urls) == 1 :  # single end
                suffix = ['']
                pair = False
            else:
                raiseError(' > ERROR: number of urls in fastq url column is unexpected')
            for r, url in enumerate(data_urls):
                if pair:
                    print(Fore.GREEN + '\n > Getting {}_{}...\n'.format(outname, suffix[r]) + 80*"=" + Fore.RESET)
                else:
                    print(Fore.GREEN + '\n > Getting {}...\n'.format(outname, suffix[r]) + 80*"=" + Fore.RESET)
                wgetcmd = ['wget', 'ftp://' + url, '-nH', '-O', outname + suffix[r] + '.fq.gz']
                if args.dry:
                    print(' '.join(wgetcmd))
                else:
                    try:
                        call(wgetcmd)
                    except FileNotFoundError:
                        raiseError('  > ERROR: wget not found, please install and try again !')
                log.write(" ".join(wgetcmd) + '\n')

    print(Fore.BLUE  + "\nIt's over, it's done!\n" + Fore.RESET)

if __name__ == "__main__":
    main()
