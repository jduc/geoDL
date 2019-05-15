#!/usr/bin/env python3
"""
Download data from the ENA website using a GSE geo accession number, ENA study accession number or
metadata spreadsheet.

url: https://github.com/jduc/geoDL
author: Julien Duc <julien_dot_duc_dot_0_at_gmail_dot_com>
"""
import sys
import os
import re
import argparse
import csv
import requests
import bs4
from bs4 import BeautifulSoup
from subprocess import call
from colorama import Fore
from six.moves.urllib.request import urlopen, urlretrieve

if sys.version_info >= (3, 0):
    from urllib.error import URLError
else:
    from urllib2 import URLError


__version__ = "v1.0.b13"
logo = """
################################################################################
               ___  _
  __ _ ___ ___|   \| |
 / _` / -_) _ \ |) | |__
 \__, \___\___/___/|____|
 |___/                   {}

################################################################################
""".format(
    __version__
)


class SmartFormatter(argparse.HelpFormatter):
    """Quick hack for formatting helper of argparse with new lines"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(self, text, width)


def raiseError(errormsg):
    print("\n" + Fore.RED + errormsg + Fore.RESET)
    sys.exit(1)


def get_args():
    """Parse and return all arguments"""
    parser = argparse.ArgumentParser(
        description="""Download fastq from The European Nucleotide Archive (ENA)
                                     <http://www.ebi.ac.uk/ena> website using a GSE geo
                                     <http://www.ncbi.nlm.nih.gov/geo/info/seq.html> accession, ENA
                                     study accession or a metadata file from ENA""",
        formatter_class=SmartFormatter,
        epilog="Made with <3 at the batcave",
    )
    parser.add_argument(
        "mode", choices=["geo", "meta", "ena", "prefetch"], help="Which mode the program runs."
    )
    parser.add_argument(
        "inputvalue",
        metavar="GSE|metadata|ENA",
        help="""R|geo:  GSE accession number, eg: GSE13373
      Map the GSE accession to the ENA study accession and fetch the metadata from ENA.

meta: Use metadata file instead of fetching it on ENA website (bypass GEO)
      Meta data should include at minima the following columns: ['Fastq files
      (ftp)', 'Submitter's sample name']

ena:  ENA study accession number, eg: PRJEB13373
      Fetch the metadata directely on the ENA website

prefetch: Use NCBI prefetch (on NCBI server) to download the data, bypass the ENA website
      entirely. This gives back SRA files - use NCBI tools for conversion. """,
    )
    parser.add_argument(
        "--ascp",
        action="store_true",
        help="Use Aspera for the download (requires an already configured aspera)",
    )
    parser.add_argument(
        "--asperakey",
        type=str,
        default="/etc/asperaweb_id_dsa.openssh",
        help="The ssh key of apsera (/etc/asperaweb_id_dsa.openssh)",
    )
    parser.add_argument(
        "--samples",
        type=str,
        default=[],
        nargs="*",
        help="Space separated list of GSM samples to download. For ENA mode, subset the metadata",
    )
    parser.add_argument(
        "--colname",
        type=str,
        default="sample_alias",
        help="Name of the column to use in the metadata file to name the samples",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Don't actually download anything, just print the wget cmds",
    )
    return parser.parse_args()


def get_metadata(args):
    """Get the metadata. If geo mode, search on ENA website, if ENA, directely take
    from the ENA website. Also return the mapping between GEO and ENA naming"""
    if args.mode == "geo":
        print("Getting correspondance table from GEO...")
        geo_url = "http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}".format(
            args.inputvalue
        )
        try:
            geo_soup = BeautifulSoup(urlopen(geo_url).read(), "html.parser")
        except URLError:
            raiseError(" > ERROR: Could not reach GEO website... exiting!")
        geo_table_soup = geo_soup.find(text=re.compile("Samples \(\d+\)")).findNext(
            "td"
        )

        map_dict = {}
        all_trs = geo_table_soup.find_all("tr")
        print(
            Fore.GREEN
            + " > Found {} samples on GEO page...".format(len(all_trs))
            + Fore.RESET
        )
        for tr in all_trs:
            tds = tr.find_all("td")
            map_dict[tds[0].text] = tds[1].text

        print("\nLooking for the metadata on ENA website...")
        search_url = "http://www.ebi.ac.uk/ena/data/warehouse/search?query=%22geo_accession=%22{geo}%22%22&result=study&display=xml".format(
            geo=args.inputvalue
        )
        print(search_url)
        try:
            print(" > Visiting ENA website...")
            search_soup = BeautifulSoup(urlopen(search_url).read(), "lxml")
        except URLError:
            raiseError(
                " > ERROR: Page not found error at {} ... exiting!".format(search_url)
            )
        except bs4.FeatureNotFound:
            raiseError(
                " > ERROR: Module lxml not found. pip install --user lxml".format(
                    search_url
                )
            )
        search_results = search_soup.find_all("secondary_id")

        if len(search_results) != 1:
            raiseError(
                " > ERROR: the XML at {} looks weird, probably missing entry!".format(
                    search_url
                )
            )

        ena_access = search_results[0].contents[0]
        metafile = "metadata_{}.xls".format(args.inputvalue)
        urlretrieve(
            "http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={}&result=read_run&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,sample_alias,scientific_name,instrument_model,library_layout,read_count,experiment_alias,run_alias,fastq_ftp&download=txt".format(
                ena_access
            ),
            metafile,
        )
        print(Fore.GREEN + " > Metafile retrieved {}!".format(metafile) + Fore.RESET)

    elif args.mode == "ena":
        metafile = "metadata_{}.xls".format(args.inputvalue)
        urlretrieve(
            "http://www.ebi.ac.uk/ena/data/warehouse/filereport?accession={}&result=read_run&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,sample_alias,scientific_name,instrument_model,library_layout,read_count,experiment_alias,run_alias,fastq_ftp&download=txt".format(
                args.inputvalue
            ),
            metafile,
        )
        print(
            Fore.GREEN
            + " > Metafile retrieved from ENA {}!".format(metafile)
            + Fore.RESET
        )
    elif args.mode == "meta":
        print(
            "\nUsing the {} metadata file ony (bypass GEO)...".format(args.inputvalue)
        )
        metafile = args.inputvalue

    elif args.mode == "prefetch":
        print("Prefetch mode: getting the SRR list...")
        metafile = "metadata_{}.xls".format(args.inputvalue)
        r = requests.get(
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse}".format(
                gse=args.inputvalue
            )
        )
        geosoup = BeautifulSoup(r.text, "html.parser")
        projurl = [url for url in geosoup.find_all("a") if "PRJ" in url.get_text()][0]
        payload = {"db": "SRA",
                   "term": "{}".format(projurl.get_text()),
                   "retmax": 10000}
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=payload
        )
        esearchsoup = BeautifulSoup(r.text, "lxml")
        ids = [i.get_text() for i in esearchsoup.idlist.find_all("id")]
        print(Fore.GREEN + "> Found {} entries...".format(len(ids)) + Fore.RESET)
        payload = {"db": "SRA",
                   "id": ','.join(ids)}
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params=payload)
        efetchsoup = BeautifulSoup(r.text, "lxml")
        exps = efetchsoup.find_all("run_set")
        assert len(exps) == len(ids)
        runs = efetchsoup.find_all("run")
        map_dict = {}
        n_rep = len(set([run["alias"].split("_")[1] for run in runs]))
        with open(metafile, "w") as meta:
            for i, run in enumerate(runs):
                name = run.pool.member["sample_title"]
                if n_rep > 1:
                    suffix = run["alias"].split("_")[1]  # e.g. GSM20202020_r2
                    rename = "_".join([re.sub(r"\s+", "_", name), suffix])
                else:
                    rename = "_".join(re.sub(r"\s+", "_", name))
                map_dict[run["accession"]] = rename
                if i == 0:
                    header = "\t".join(list(run.attrs.keys()) + \
                                       list(run.pool.member.attrs.keys()) + \
                                       ["paired", "rename"]) + \
                                       "\n"
                    meta.write(header)
                paired = "SE" if len(run.statistics.find_all("read")) == 1 else "PE"
                data = "\t".join(list(run.attrs.values()) + \
                                 list(run.pool.member.attrs.values()) + \
                                 [paired, rename]) + \
                                 "\n"
                meta.write(data)
    return metafile, map_dict


def ena_dl(args, metafile, map_dict):
    """Download the data from ENA using wget or ascp, using the metadta the metadata
    """

    # check that the column selected for naming is uniq
    with open(metafile) as f:
        reader = csv.reader(f, delimiter="\t")
        samplenames = []
        for i, row in enumerate(reader):
            if i == 0:
                if args.colname not in row:
                    raiseError(
                        "  > ERROR: Column {col} not in the metadata file "
                        "{meta}".format(col=args.colname, meta=metafile)
                    )
                for j, c in enumerate(row):
                    if c == args.colname:
                        idx = j
            else:
                if row[idx] in samplenames:
                    raiseError(
                        "  > ERROR: Non uniq sample names in the column {col} "
                        "of the meta file {meta}\n".format(
                            col=args.colname, meta=metafile
                        )
                    )
                samplenames.append(row[idx])
    return metafile, map_dict

    dlsoft = "aspera" if args.ascp else "wget"
    print("Starting the downloads with {}\n".format(dlsoft))
    with open(metafile) as f, open("geoDL.logs", "w") as log:
        for i, line in enumerate(f):
            if i == 0:
                header = [h.strip() for h in line.split("\t")]
                log.write("{} download log \n".format(args.inputvalue))
                continue
            data = dict(zip(header, [sp.strip() for sp in line.split("\t")]))
            try:
                data_urls = data["fastq_ftp"].split(";")
            except KeyError:
                raiseError(
                    "  > ERROR: Fastq urls (ftp) is not in the metadata, \
                           make sure to add the column and try again."
                )
            if args.mode == "geo":
                m = re.search("(GSM\d+)", data[args.colname])
                if m is None:
                    raiseError("  > ERROR: Regexp did not match...")
                if len(m.groups()) > 1:
                    raiseError("  > ERROR: Regexp matched multiple times...")
                gsm = m.group(1)
                try:
                    outname = map_dict[gsm].replace(" ", "_")
                except KeyError:
                    raiseError(
                        "  > ERROR: The GSM {} was not found in the GEO page...  exiting!".format(
                            gsm
                        )
                    )
                if len(args.samples) > 0 and gsm not in args.samples:
                    continue
                log.write(gsm + " --> " + outname + "\n")
            else:
                outname = data[args.colname].replace(" ", "_")
            if len(data_urls) == 2:  # paired end
                suffix = ["_R1", "_R2"]
                pair = True
            elif len(data_urls) == 1:  # single end
                suffix = [""]
                pair = False
            else:
                raiseError(" > ERROR: number of urls in fastq url column is unexpected")
            for r, url in enumerate(data_urls):
                if pair:
                    print(
                        Fore.GREEN
                        + "\n > Getting {}{}...\n".format(outname, suffix[r])
                        + 80 * "="
                        + Fore.RESET
                    )
                else:
                    print(
                        Fore.GREEN
                        + "\n > Getting {}...\n".format(outname, suffix[r])
                        + 80 * "="
                        + Fore.RESET
                    )
                wgetcmd = [
                    "wget",
                    "--no-use-server-timestamps",
                    "-nH",
                    "ftp://" + url,
                    "-O",
                    outname + suffix[r] + ".fq.gz",
                ]

                ascp = os.popen("which ascp").read().strip()
                ascpcmd = [
                    ascp,
                    "-T",
                    "--policy",
                    "high",
                    "-l",
                    "10G",
                    "-i",
                    args.asperakey,
                    "-P",
                    "33001",
                    url.replace("ftp.sra.ebi.ac.uk", "era-fasp@fasp.sra.ebi.ac.uk:"),
                    outname + suffix[r] + ".fq.gz",
                ]
                if args.dry:
                    if args.ascp:
                        print(" ".join(ascpcmd))
                    else:
                        print(" ".join(wgetcmd))
                else:
                    if args.ascp:
                        try:
                            ret = call(ascpcmd)
                            if ret != 0:
                                print("  > ERROR: ascp returned {}".format(ret))
                                print("  > cmd was: \n{}".format(" ".join(ascpcmd)))
                                sys.exit(1)
                        except FileNotFoundError:
                            raiseError(
                                "  > ERROR: ascp not found, please install and try again !"
                            )
                        log.write(" ".join(ascpcmd) + "\n")
                    else:
                        try:
                            ret = call(wgetcmd)
                            if ret != 0:
                                print("  > ERROR: wget returned {}".format(ret))
                                print("  > cmd was: \n{}".format(" ".join(wgetcmd)))
                        except FileNotFoundError:
                            raiseError(
                                "  > ERROR: wget not found, please install and try again !"
                            )
                            sys.exit(1)
                        log.write(" ".join(wgetcmd) + "\n")


def prefetch_dl(args, metafile, map_dict):
    """Use the NCBI prefetch program to download the data"""
    assert len(set(map_dict.values())) == len(map_dict.keys()), "Non unique sample name"
    with open(metafile) as meta, open("geoDL.logs", "w") as log:
        for n, sample in enumerate(meta):
            sp = sample.strip().split("\t")
            if n == 0:  # header
                continue
            srr = sp[1]
            if args.ascp:
                ascp = os.popen("which ascp").read().strip()
                cmd = ["prefetch", "-v", "-X", "100GB", "-t", "ascp",
                       "-a", ascp+"|"+args.asperakey, srr]
            else:
                cmd = ["prefetch", "-v", "-X", "100GB", srr]
            log.write(" ".join(cmd) + "\n")
            call(cmd)
            call(["touch", srr])
            call(["mv", srr, map_dict[srr]+".sra"])


def main():
    print(Fore.BLUE + logo + Fore.RESET)
    args = get_args()
    metafile, map_dict = get_metadata(args)
    if args.mode == "prefetch":
        prefetch_dl(args, metafile, map_dict)
    else:
        ena_dl(args, metafile, map_dict)
    print(Fore.BLUE + "\nIt's over, it's done!\n" + Fore.RESET)


if __name__ == "__main__":
    main()
