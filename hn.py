"""
This is a very simple script for downloading Hackernews data from Algolia API.

It stores the data in csv files.

Algolia API limitations:

- The answer can have no more than 1k replies
- There cannot be more than 10k requests per hour. This must be checked at the application level,
  if the limit will be exceeded, then the IP address can be blocked.
- The main request to get the results is `created_at_i<=X`. Then the API returns no more than 1k items
  created in time smaller than X, beginning with the newest ones. Because of this, I had to parse
  the whole json response to find the smallest `created_at_i` value (which is an integer of the creation timestamp).
  To load the data to a processing pipeline later, I will have to parse it, so to avoid more json parsing,
  I do it once here, and save it to csv files.
  This also means that I cannot search to get the entries smaller than X, just the timestamps. It is possible to have
  two or more entries made during the same second. To get all the entries, when I get that the minimum created_at_i
  for a request is `A`, then in the next request I had to use `created_at_i<=A`. This way some of the entries
  are duplicated.

Entry Duplication

Some entries between the files are duplicated, which is basically because of the Algolia API limitations.
What's more, Hackernews users can edit their entries, so when downloading the data after some time, it's possible
that some entries will be different. Mechanism of loading the data to some processing pipeline should
updated the entries when will have a duplicated entry id.

Users Data

Algolia allows to get user data only with requests with specific user_id. There is another script hnusers.py
to get the data for all the users from the files.
"""


import argparse
import csv
import json
import os
from dataclasses import dataclass
from shutil import move
from typing import Optional

import requests as r

from .common import convert, limit_rate

# there is about 20M of entries
# each request returns no more than 1k of entries
# this value can decrease the number of files,
# automatically increasing the files' size
number_of_requests_for_one_file = 1000

# how many entries should be returned per request
entries_per_request = 1000

# Algolia has a limit of 10k requests per hour
max_request_per_hour = 9_000

# Temporary file
temp_fname = "tmp.data.csv"

# Base URL for the requests
base_url = "http://hn.algolia.com/api/v1/search_by_date?" \
           "hitsPerPage={hits_per_page}&" \
           "numericFilters=created_at_i<={max_created_at_i},created_at_i>={min_created_at_i}"

# This is created_at_i field for the entry number 1
# https://hn.algolia.com/api/v1/items/1
default_min_created_at_i: int = 1160418111

default_max_created_at_i: int = 41 + int(time.time())


@dataclass
class ParsedResponse:
    hits_count: int
    min_created_at_i: int
    max_created_at_i: int
    min_id: int
    max_id: int
    entries: list


@limit_rate(max_request_per_hour, 3600)
def get_data(min_created_at_i: int, max_created_at_i: int) -> str:

    url = base_url.format(
        max_created_at_i=max_created_at_i,
        min_created_at_i=min_created_at_i,
        hits_per_page=entries_per_request
    )
    return r.get(url).text


def parse_response(response: str) -> ParsedResponse:
    res = json.loads(response)
    min_created_at_i = 100000000000
    max_created_at_i = 0
    min_id = 100000000000000
    max_id = 0
    hits = res["hits"]

    entries = []
    for hit in hits:
        entry = dict(
            created_at=hit["created_at"],
            title=convert(hit["title"]),
            url=hit["url"],
            author=convert(hit["author"]),
            points=hit["points"],
            story_text=convert(hit["story_text"]),
            comment_text=convert(hit["comment_text"]),
            num_comments=hit["num_comments"],
            story_id=hit["story_id"],
            story_title=convert(hit["story_title"]),
            story_url=hit["story_url"],
            parent_id=hit["parent_id"],
            created_at_i=hit["created_at_i"],
            type=hit["_tags"][0],
            object_id=int(hit["objectID"])
        )
        entries.append(entry)
        created_at_i = entry["created_at_i"]
        obj_id = entry["object_id"]
        min_created_at_i = min(min_created_at_i, created_at_i)
        max_created_at_i = max(max_created_at_i, created_at_i)
        min_id = min(min_id, obj_id)
        max_id = max(max_id, obj_id)

    nbHits = int(res["nbHits"])

    return ParsedResponse(
        hits_count=nbHits,
        min_created_at_i=min_created_at_i,
        max_created_at_i=max_created_at_i,
        min_id=min_id,
        max_id=max_id,
        entries=entries
    )


@dataclass(frozen=True)
class ProgramArguments:
    data_path: str
    min_created_at_i: int
    max_created_at_i: int


@dataclass(frozen=True)
class ProgramState:
    min_created_at_i: int
    max_created_at_i: int
    min_id: Optional[int]
    max_id: Optional[int]
    data_path: str


def parse_arguments():
    parser = argparse.ArgumentParser(description='Downloads Hackernews data')

    parser.add_argument("--data-path", required=True, help="path to the data directory")
    parser.add_argument("--min-created-at-i", type=int,
                        help="The minimum value for the created_at_i, default is the value for the first post")
    parser.add_argument("--max-created-at-i", type=int,
                        help="The maximum value for the created_at_i, default is current timestamp + some small number")

    args = parser.parse_args()
    return ProgramArguments(**vars(args))


def build_file_name(min_created_at_i, min_id, max_created_at_i, max_id):
    return f"{min_created_at_i}_{max_created_at_i}__{min_id}_{max_id}.data.csv"


def run(state: ProgramState):
    temp_fpath = os.path.join(state.data_path, temp_fname)

    use_min_created_at_i = state.min_created_at_i
    use_max_created_at_i = state.max_created_at_i

    no_more_results = False

    while True:
        # stats for the temp file
        this_min_id = 10000000000000000
        this_max_id = 0
        this_min_created_at_i = 10000000000000000
        this_max_created_at_i = 0
        header_written = False

        # fill the temp file
        with open(temp_fpath, "w", encoding="utf-8") as f:
            for _ in range(number_of_requests_for_one_file):

                writer = csv.writer(f)
                res = get_data(use_min_created_at_i, use_max_created_at_i)
                res = parse_response(res)
                print(f"got {len(res.entries)} entries")

                if res.hits_count == 0:
                    no_more_results = True
                    break

                if not header_written:
                    writer.writerow(res.entries[0].keys())
                    header_written = True
                for entry in res.entries:
                    writer.writerow(entry.values())

                this_min_id = min(this_min_id, res.min_id)
                this_max_id = max(this_max_id, res.max_id)
                this_min_created_at_i = min(this_min_created_at_i, res.min_created_at_i)
                this_max_created_at_i = max(this_max_created_at_i, res.max_created_at_i)
                use_max_created_at_i = this_min_created_at_i

        # now copy the temp file to the final file
        new_fname = build_file_name(this_min_created_at_i, this_min_id, this_max_created_at_i, this_max_id)
        file_path = os.path.join(state.data_path, new_fname)
        move(temp_fpath, file_path)
        print(f"Written data to a new file: {new_fname}")

        if no_more_results:
            break


if __name__ == "__main__":
    args = parse_arguments()
    if not os.path.isdir(args.data_path):
        os.makedirs(args.data_path)

    state = ProgramState(
        min_created_at_i=args.min_created_at_i or default_min_created_at_i,
        max_created_at_i=args.max_created_at_i or default_max_created_at_i,
        min_id=None,
        max_id=None,
        data_path=args.data_path
    )
    run(state)
