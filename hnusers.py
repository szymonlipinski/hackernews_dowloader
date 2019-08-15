"""
A simple script for downloading user data.
"""
import argparse
import csv
import json
import os
from dataclasses import dataclass
from shutil import move

import requests as r

from common import convert, limit_rate, max_request_per_hour, pid_run

users_file_name = "users"
users_data_file_name = "users.data.csv"
temp_file_name = "tmp.users.data.csv"

# Base URL for the requests
base_url = "https://hn.algolia.com/api/v1/users/{user_name}"


@dataclass(frozen=True)
class ProgramArguments:
    """
    Arguments passed to the program
    """
    data_path: str
    create_users_file: str
    get_users_data: str


@limit_rate(max_request_per_hour, 3600)
def get_data(user_name: str) -> str:
    """
    Makes request to the API and returns text reply.
    """
    url = base_url.format(user_name=user_name)
    return r.get(url).text


def parse_response(response: str) -> dict:
    """
    Parses the response from the API and returns dictionary with converted fields.
    """
    res = json.loads(response)
    return dict(
        id=res["id"],
        username=res["username"],
        about=convert(res["about"]),
        karma=int(res["karma"]),
        avg=res["avg"],
        delay=res["avg"],
        submitted=res["submitted"],
        updated_at=res["updated_at"],
        submission_count=res["submission_count"],
        comment_count=res["comment_count"],
        created_at_i=res["created_at_i"],
        object_id=res["objectID"]
    )


def show_progress(now, max, step=0.01):
    print(f" ➛ {now:,}/{max:,} ➛ {now / max * 100:.02f}%")


def get_users_data(args: ProgramArguments):
    """Creates a csv file with unique and sorted user data from all the data csv files.
    The file is saved to args.data_path/users_data_file_name
    """
    print("Downloading users data")
    users_file_path = os.path.join(args.data_path, users_file_name)
    users_data_file_path = os.path.join(args.data_path, users_file_name)
    temp_file_path = os.path.join(args.data_path, temp_file_name)

    # read all users to a list, it shouldn't be large
    # and will be useful for showing progress
    users = list()
    with open(users_file_path) as fusers:
        for user in fusers:
            users += [user.strip()]

    print(f"Getting data for {len(users):,} users")

    with open(temp_file_path, "w") as users_data:
        header_written = False
        writer = csv.writer(users_data)

        counter = 0
        for user in users:
            counter += 1
            show_progress(now=counter, max=len(users))
            user = user.strip()
            res = get_data(user)
            res = parse_response(res)
            if not header_written:
                writer.writerow(res.keys())
                header_written = True
            writer.writerow(res.values())

    move(temp_file_path, users_data_file_path)
    print("DONE")


def create_users_file(args: ProgramArguments):
    """Creates a file with unique and sorted user names from all the data csv files.
    The file is saved to args.data_path/users_file_name
    """
    print("Creating a file with unique users names")

    users = set()

    for f in os.listdir(args.data_path):
        if not f.endswith(".data.csv"):
            continue

        fname = os.path.join(args.data_path, f)
        print(f"Reading file {fname}")
        with open(fname) as csvfile:
            reader = csv.reader(csvfile)

            # read the header first
            header = next(reader)
            # and search for the place where the created_at_i is
            try:
                index = header.index("author")
                for line in reader:
                    users.add(line[index])
            except Exception:
                pass

    users_file_path = os.path.join(args.data_path, users_file_name)
    with open(users_file_path, "w") as f:
        for user in sorted(users):
            f.write(f"{user}\n")

    print(f"Written names of {len(users):,} users to {users_file_path}")


def run(args: ProgramArguments):
    """
    The main program function.
    """
    if args.create_users_file:
        create_users_file(args)
    if args.get_users_data:
        get_users_data(args)


def parse_arguments() -> ProgramArguments:
    """
    Parses arguments and returns parsed version.
    """
    parser = argparse.ArgumentParser(description='Downloads Hackernews users data')

    parser.add_argument("--data-path", required=True, help="path to the data directory")
    parser.add_argument("--create-users-file", action='store_true',
                        help="Creates a file with unique users names from all the csv files")
    parser.add_argument("--get-users-data", action='store_true',
                        help="Downloads all the data for all users from Algolia API")

    return ProgramArguments(**vars(parser.parse_args()))


if __name__ == "__main__":
    args = parse_arguments()
    if not os.path.isdir(args.data_path):
        os.makedirs(args.data_path)

    pid_run(lambda: run(args))
