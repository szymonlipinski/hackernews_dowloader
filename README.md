# Hackernews Downloader

A simple stuff for downloading the Hackernews data from tha Algolia API.

## Downloading Stories, Comments, etc.

The main downloading is done with the script `hn.py` which can download data to a set of csv files.

```

usage: hn.py [-h] --data-path DATA_PATH [--min-created-at-i MIN_CREATED_AT_I]
             [--max-created-at-i MAX_CREATED_AT_I]

Downloads Hackernews data

optional arguments:
  -h, --help            show this help message and exit
  --data-path DATA_PATH
                        path to the data directory
  --min-created-at-i MIN_CREATED_AT_I
                        The minimum value for the created_at_i, default is the
                        value for the first post
  --max-created-at-i MAX_CREATED_AT_I
                        The maximum value for the created_at_i, default is
                        current timestamp + some small number

```

### Example Use

```
python hn.py --data-path /home/data/hn/
```

## Downloading Users Data

For users there is a different API endpoint. What's more, it's not possible to get list of users, we can only
get user by name.

For users there is the program `hnusers.py:

```

usage: hnusers.py [-h] --data-path DATA_PATH [--create-users-file]
                  [--get-users-data]

Downloads Hackernews users data

optional arguments:
  -h, --help            show this help message and exit
  --data-path DATA_PATH
                        path to the data directory
  --create-users-file   Creates a file with unique users names from all the
                        csv files
  --get-users-data      Downloads all the data for all users from Algolia API

```

### Getting All Users Names

The first step is to get all the user names from all the csv files downloaded by the `hn.py`.

```
python hnusers.py --data-path=/home/data/hn --create-users-file
```

This will read all the csv files and will create a file named `users` with all the users alphabetically sorted.

### Getting All Users Data

For each user, we need to make a separate API request. The below command should create a file `users.data.csv` with all
the data taken from the API for each user. 

```
python hnusers.py --data-path=/home/data/hn --get-users-data
```

## Algolia API limitations:

- A request answer can have no more than 1k entries.
- There cannot be more than 10k requests per hour. This must be checked at the application level,
  if the limit will be exceeded, then the IP address can be blocked. There is a simple rate limiter in the common.py file.
  Also, both scripts are guarded by a pid file, so it's not possible to run them both at the same time.
  The rate limiter only limits the number of requests for one script. So running two at the same time can
  exceed the limit.
- The main API url part for a request to get the results is `created_at_i<=X`. 
  Then the API returns no more than 1k items created in time smaller than X, beginning with the newest ones. 
  Because of this, I had to parse the whole json response to find the smallest `created_at_i` value 
  (which is an integer of the creation timestamp).
  To load the data to a processing pipeline later, I will have to parse it, so to avoid more json parsing,
  I do it once here, and save it to csv files.
  This also means that I cannot search to get the entries with ids smaller than `X`. I can only use timestamps.
  It is possible to have two or more entries made during the same second.
  To get all the entries, when I get that the minimum created_at_i for a request is `A`, 
  then in the next request I had to use `created_at_i<=A`. This way some of the entries are duplicated.

## Entry Duplication

Some entries in the files are duplicated, which is basically because of the Algolia API limitations.
What's more, Hackernews users can edit their entries, so when downloading the data after some time, some entries may be different. Mechanism of loading the data to a processing pipeline should
update the entries when will have a duplicated entry id.

## Users Data

Algolia allows getting user data only with requests with specific user_id. There is another script hnusers.py
to get the data for all the users from the files.

## Fields Conversion

- created_at field is removed as it's redundant, there already is created_at_i, which is an integer.
- text fields are converted from html entities for proper characters, including unicode versions

## Required Libraries

The requirements.txt file contains lots of stuff, not only the libraries required to download the HN data. I'm not going to strip this down only to the needed libraries.
