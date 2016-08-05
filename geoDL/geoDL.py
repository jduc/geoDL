#!/bin/python
"""
Download data from the EBI website using a GSE geo accession number. First search for the
GSE number on EBI website to find the corresponding SRP number. Then fetch the metadata download all
the fastq links.

url: https://github.com/jduc/geoDL/tree/master/geoDL 
author: Julien Duc <julien_dot_duc_dot_0_at_gmail_dot_com>
"""

from __future__ import print_function
import re
import sys
import argparse
import time
from bs4 import BeautifulSoup
from subprocess import call
from colorama import init, Fore
from six.moves.urllib.request import urlopen, urlretrieve

__version__ = 'v1.0.b1'

def main():
    link_re = re.compile('http://.*SRP\d+$')

    logo="""
################################################################################
                   ___  _
      __ _ ___ ___|   \| |
     / _` / -_) _ \ |) | |__
     \__, \___\___/___/|____|
     |___/                   {}

################################################################################
    """.format(__version__)
    print(Fore.BLUE + logo + Fore.RESET)

### Argument parsing
    parser = argparse.ArgumentParser(description="""Download fastq from the ENA \
                                     <http://www.ebi.ac.uk/ena> website using a GSE geo \
                                     <http://www.ncbi.nlm.nih.gov/geo/info/seq.html> accession \
                                     number or a metadata file from ENA.
                                     """,
                                     epilog='[Julien "@jduc" Duc <julien_dot_duc_dot_0_at_gmail_dot_com>]')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--gse', metavar='GSE', type=str, help='GSE accession number, eg: GSE13373')
    group.add_argument('--meta', metavar='ENA metadata file', 
                        help="""Use metadata file instead of fetching it on EBI website (bypass GEO). 
                        Meta data should include at minima the following columns: ['Fastq files
                        (ftp)', 'Submitter's sample name']""", 
                        default=None)
    parser.add_argument('--dry', action='store_true',
                        help="Don't actually download anything, just print the wget cmds")
    parser.add_argument('--samples', type=str, default=[], nargs='*',
                        help='Space separated list of GSM samples to download')
    args = parser.parse_args()
    gse = args.gse
    meta= args.meta
    samples = args.samples

    if gse is None and meta is None:
        parser.error(Fore.RED + '\nMissing argument, either --gse or --meta is required\n' +
                     Fore.RESET)

### Find the META table on EBI website
    if meta is None:
        print('\nLooking for the metadata on EBI website...')
        search_url = 'http://www.ebi.ac.uk/ena/data/warehouse/search?query=%22geo_accession=%22{geo}%22%22&result=study&display=xml'.format(geo=gse)
        try:
            print(' > Visiting EBI website...')
            search_soup = BeautifulSoup(urlopen(search_url).read(), 'lxml')
        except:
            print(Fore.RED + ' > ERROR: Page not found error... exiting!' + Fore.RESET)
            sys.exit(1)
        search_results = search_soup.find_all('secondary_id')

        if len(search_results) != 1:
               print(Fore.RED + ' > ERROR: Multiple or NO SRP link found, solve manually please... exiting!' +
                     Fore.RESET)
               sys.exit(1)

        access = search_results[0].contents[0]
        metafile = 'metadata_{}.xls'.format(gse)
        urlretrieve("http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={}&result=read_run&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,sample_alias,scientific_name,instrument_model,library_layout,read_count,experiment_alias,run_alias,fastq_ftp&download=txt".format(access),
                            metafile)
        print(' > Metafile retrieved {}!'.format(metafile))

### Get the correspondance table for the name
        print('Getting correspondance table from GEO...')
        geo_url = 'http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}'.format(gse)

        try:
            geo_soup = BeautifulSoup(urlopen(geo_url).read(), 'html.parser')
        except URLError:
            print(Fore.RED + ' > ERROR: Could not reach GEO website... exiting!' + Fore.RESET)
            sys.exit(1)
        geo_table_soup = geo_soup.find(text=re.compile('Samples \(\d+\)')).findNext('td')

        map_dict = {}
        all_trs = geo_table_soup.find_all('tr')
        print(Fore.GREEN + ' > Found {} samples on GEO page...'.format(len(all_trs)) + Fore.RESET)
        for tr in all_trs:
            tds = tr.find_all('td')
            map_dict[tds[0].text] = tds[1].text
    else:
        print('\nUsing the {} metadata file ony (bypass GEO)...'.format(meta))
        metafile = meta 


### Start the download from metadata
    print('Starting the downloads...\n')
    with open(metafile) as f, open('geoDL.logs', 'w') as log:
        for i, line in enumerate(f):
            if i == 0:
                header = [h.strip() for h in line.split('\t')]
                log.write('{} download log \n'.format(gse))
                continue
            data = dict(zip(header, [sp.strip() for sp in line.split('\t')]))
            data_urls = data['fastq_ftp'].split(';')
            if meta is None:
                gsm = data['experiment_alias']
                try:
                    outname = map_dict[gsm]
                except KeyError:
                    print(Fore.RED + ' > ERROR: The GSM {} was not found in the GEO page... exiting!' +
                          Fore.RESET)
                    sys.exit(1)
                if len(samples) > 0 and gsm not in samples:
                    continue
                log.write(gsm +  ' --> ' +  outname + '\n')
            else:
                outname = data['sample_alias']
            if len(data_urls) == 2:  # paired end
                suffix = ['_R1', '_R2']
            elif len(data_urls) ==1 :  # single end
                suffix = ['']
            else:
                print(Fore.RED + ' > ERROR: number of urls in fastq url column is unexpected' +
                      Fore.RESET)
                sys.exit(1)
            for r, url in enumerate(data_urls):
                print(Fore.GREEN + '\n > Getting {}_{}...\n'.format(outname, suffix[r]) + 80*"=" + Fore.RESET)
                if args.dry:
                    print(' '.join(['wget', 'ftp://' + url, '-nH', '-O', outname + suffix[r] + '.fq.gz']))
                else:
                    try:
                        wgetcmd = ['wget', 'ftp://' + url, '-nH', '-O', outname + suffix[r] + '.fq.gz']
                        call(wgetcmd)
                    except FileNotFoundError:
                        print(Fore.RED + "  > ERROR: wget not found, please install and try again" +
                              Fore.Reset)
                        sys.exit(1)
                    log.write(" ".join(wgetcmd))

    print(Fore.BLUE  + "\nIt's over, it's done!\n" + Fore.RESET)

if __name__ == "__main__":
    main()
