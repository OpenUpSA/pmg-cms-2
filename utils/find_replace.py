import csv

from pmg import db
from pmg.models.resources import CommitteeMeeting, File


def read_csv(path):
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['possible_duplicate'] == 'True':
                continue
            yield row


def find_meeting(id):
    meeting = CommitteeMeeting.query.filter_by(id=id).first()
    return meeting


def upload_file(path):
    file = File()
    file.from_file_blob(path)
    return file.file_path


def main():
    # TODO: Pass CSV as arg
    for row in read_csv("utils/output.csv"):
        meeting_id = row['meeting_id']
        print(meeting_id)
        if int(meeting_id) == 1:
            meeting = find_meeting(meeting_id)
            new_file_url = upload_file(row['filesystem_path'])
            meeting.body = meeting.body.replace(row['url'], new_file_url)
            print(meeting.body)
            db.session.commit()


if __name__ == "__main__":
    main()
