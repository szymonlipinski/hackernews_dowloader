"""
A simple script for downloading user data.
"""
import argparse
import csv
import json
import os
from dataclasses import dataclass

import requests as r

users_file_name = "users"
users_data_file_name = "users.data.csv"


# Base URL for the requests
base_url = "https://hn.algolia.com/api/v1/users/{user_name}"


@dataclass(frozen=True)
class ProgramArguments:
    data_path: str
    create_users_file: str
    get_users_data: str


def get_data(user_name: str) -> str:
    url = base_url.format(user_name=user_name)
    return r.get(url).text


def parse_response(response: str) -> dict:
    res = json.loads(response)
    return dict(
        id = res["id"],
        username = res["username"],
        karma = int(res["karma"]),
        created_at = 
    )



def get_users_data(args: ProgramArguments):
    """Creates a csv file with unique and sorted user data from all the data csv files.
    The file is saved to args.data_path/users_data_file_name
    """
    print("Downloading users data")



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
            index = header.index("author")
            for line in reader:
                users.add(line[index])

    users_file_path = os.path.join(args.data_path, users_file_name)
    with open(users_file_path, "w") as f:
        for user in sorted(users):
            f.write(f"{user}\n")

    print(f"Written names of {len(users)} users to {users_file_path}")


def run(args: ProgramArguments):
    if args.create_users_file:
        create_users_file(args)
    if args.get_users_data:
        get_users_data(args)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Downloads Hackernews users data')

    parser.add_argument("--data-path", required=True, help="path to the data directory")
    parser.add_argument("--create-users-file", action='store_true',
                        help="Creates a file with unique users names from all the csv files")
    parser.add_argument("--get-users-data", action='store_true',
                        help="Downloads all the data for all users from Algolia API")

    args = parser.parse_args()
    return ProgramArguments(**vars(args))


if __name__ == "__main__":
    args = parse_arguments()
    if not os.path.isdir(args.data_path):
        os.makedirs(args.data_path)

    run(args)
