"""
    Python script to upload and replace broken links with new ones.

    Example Usage: python utils/find_replace.py --csv input.csv --out output.csv

    Outputs a csv with meeting_id previous_url previous_filesystem_path new_file_url file_id event_file_id columns
"""
import argparse
import csv
import logging
import os
import shutil
import tempfile
from collections import namedtuple

from pmg import app, db
from pmg.models.resources import CommitteeMeeting, EventFile, File


def create_logger():
    logging.basicConfig(level=logging.INFO, filemode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    logger = logging.getLogger(__name__)
    file_handler = logging.FileHandler(args.logfile)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def read_csv(path):
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["possible_duplicate"] == "True":
                continue
            yield row


def find_meeting_by_id(id):
    meeting = db.session.query(CommitteeMeeting).filter_by(id=int(id)).first()
    return meeting


def upload_file(path):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, os.path.basename(path))
        shutil.copyfile(path, temp_path)
        file = File()
        file.from_file_blob(temp_path)
        file.file_path = path
        return file


def process_and_upload_files(args):
    logger = create_logger()
    csv_row = namedtuple(
        "Row",
        "meeting_id previous_url previous_filesystem_path new_file_url file_id event_file_id",
    )
    for row in read_csv(args.csv):
        row_url = row["url"]
        meeting_id = row["meeting_id"]
        filesystem_path = row["filesystem_path"]
        meeting = find_meeting_by_id(meeting_id)
        if not meeting:
            logger.error("Could not find meeting {}".format(meeting_id))
            continue
        new_file_url = ""
        try:
            with app.app_context():
                file = upload_file(filesystem_path)
                new_file_url = file.url
        except FileNotFoundError:
            logger.error(
                f"Could not find file {filesystem_path} for meeting id: {meeting_id}, {new_file_url}"
            )
            continue
        if new_file_url and meeting.body and row_url in meeting.body:
            meeting.body = meeting.body.replace(row_url, new_file_url)
            event_file = EventFile(event=meeting, file=file)
            db.session.add(file)
            db.session.add(event_file)
            db.session.add(meeting)
            db.session.commit()
            yield csv_row(
                meeting_id,
                row_url,
                row["filesystem_path"],
                new_file_url,
                file.id,
                event_file.id,
            )


def write_to_csv(csv_path, rows):
    with open(csv_path, "a") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "meeting_id",
                "previous_url",
                "previous_filesystem_path",
                "new_file_url",
                "file_id",
                "event_file_id",
            ]
        )
        for row in rows:
            writer.writerow(row)


def main(args):
    logger = create_logger()
    logger.info("Started")
    write_to_csv(args.out, process_and_upload_files(args))
    logger.info("Finished")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__name__)
    parser.add_argument(
        "--csv", required=True, help="path to csv file with extracted urls"
    )
    parser.add_argument(
        "--out", required=True, help="path to csv file with the results"
    )
    parser.add_argument("--logfile", required=True, help="path to logfile")
    args = parser.parse_args()
    main(args)
