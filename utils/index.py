"""
    Python script to find broken links from a csv file and try match the filenames
    to existing backup files

    Example Usage: python index.py --csv input.csv --out output.csv

    Outputs a csv with meeting_id, url, filesystem_paths, possible_duplicate columns
"""
import argparse
import csv
import glob
import hashlib
import os
from collections import namedtuple


def get_backup_file_path(path):
    with open(path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            yield row[0], row[2]


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def compare_and_yield_row(files, hashes, csv_row, event_info):
    unique_hash = set()
    possible_duplicate = False
    for file in files:
        try:
            md5_hash = md5(file)
        except IsADirectoryError:
            continue
        unique_hash.add(md5_hash)
        if len(unique_hash) > 1:
            possible_duplicate = True
        if not hashes.get(md5_hash):
            hashes[md5_hash] = file
            yield csv_row(event_info[0], event_info[1], hashes[md5_hash], possible_duplicate)


def find_lost_files(csv_path):
    csv_row = namedtuple('Row', 'meeting_id url filesystem_paths possible_duplicate')
    hashes = {}
    for event_info in get_backup_file_path(csv_path):
        # TODO: check if event info is already in csv
        filename = os.path.basename(event_info[1])
        # escape characters such as []
        dir = f"**/{glob.escape(filename)}"
        files_found = glob.glob(dir, recursive=True)
        if not len(files_found):
            continue
        yield from compare_and_yield_row(
            files_found,
            hashes, csv_row,
            event_info
        )


def write_to_csv(csv_path, rows):
    with open(csv_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['meeting_id', 'url', 'filesystem_path', 'possible_duplicate'])
        for row in rows:
            writer.writerow(row)


def main(args):
    # Generate csv with meeting_id, url, filesystem_paths
    OUTPUT_CSV = args.out
    if not args.out:
        OUTPUT_CSV = 'output.csv'
    write_to_csv(OUTPUT_CSV, find_lost_files(args.csv))
    print(f'Output csv written to {OUTPUT_CSV}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument(
        '--csv',
        required=True,
        help='path to csv file with extracted urls'
    )
    parser.add_argument(
        '--out',
        help='output csv path'
    )

    args = parser.parse_args()

    main(args)
