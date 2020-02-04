__version__ = '0.1.0'

import argparse
import sys
import os
import time
import calendar
import datetime
import pathlib
import pickle
import html

from collections import defaultdict

import pystache
from termcolor import colored
from github import Github

REPO = "apache/incubator-tvm"

def date_filter_for_month(month, year):
    _, num_days = calendar.monthrange(year, month)
    first_day = datetime.date(year, month, 1)
    last_day = datetime.date(year, month, num_days)
    first_day = first_day.strftime('%Y-%m-%d')
    last_day = last_day.strftime('%Y-%m-%d')
    return first_day, f"{first_day}..{last_day}"

def get_user_activity(g, user_name, date_filter):
    review_template = f"repo:{REPO} commenter:{{}} updated:{{}} is:pr"
    author_template = f"repo:{REPO} author:{{}}    updated:{{}} is:pr"

    q = review_template.format(user_name, date_filter)
    review_activity = [i.title + " (#" + str(i.number) + ")" for i in g.search_issues(query=q)]
    q = author_template.format(user_name, date_filter)
    author_activity = [i.title + " (#" + str(i.number) + ")" for i in g.search_issues(query=q)]

    return {
        'author': set(author_activity),
        'review': set(review_activity) - set(author_activity),
    }



def render_report(out_path, report_content):
    tvm_news_dir = pathlib.Path(__file__).parent.absolute().parent
    with open(tvm_news_dir.joinpath('template.md'), 'r') as template:
        content = pystache.render(template.read(), report_content)
        with open(out_path, 'w') as out_file:
            out_file.write(content)


def download_report(github, month, year):
    repo = github.get_repo(REPO)
    team = [c.login for c in repo.get_contributors()]
    first_day, date_filter = date_filter_for_month(month, year)

    # Get Pull Requests
    prs_query = f"repo:{REPO} merged:>={first_day} sort:updated-asc"
    prs = list(github.search_issues(prs_query))

    # WARNING: Search API only supports 30 req/s: https://developer.github.com/v3/search/
    time.sleep(60)

    # get activities
    report = {}
    for member in team:
        report[member] = get_user_activity(github, member, date_filter)
        print("{}, committed {}, reviewed {}".format(colored(member, 'blue'), len(report[member]['author']), len(report[member]['review'])))
        sys.stdout.flush()
        time.sleep(5)

    return (prs, report, team)

CACHE_PATH = os.path.expanduser('~/.tvm_news_cache')

def parse_title(pr):
    title = html.unescape(pr.title)
    splits = title.split("]")
    tags = []
    raw_tags = splits[:-1]

    for tag in raw_tags:
        tags += tag.split(",")

    title = splits[-1]
    return tags, title.strip("] \t")

def normalize_tag(tag):
    return tag.strip(" []{}\t,").lower().capitalize()

def bucket_by_tag(prs):
    tag_count = {}
    final_tags = defaultdict(list)
    tagged_prs = []

    for pr in prs:
        tags, title = parse_title(pr)
        tags = [normalize_tag(tag) for tag in tags]

        for tag in tags:
            tag_count[tag] = tag_count.get(tag, 0) + 1

        tagged_prs.append((tags, title, pr))

    for tags, title, pr in tagged_prs:
        top_tag = None
        for tag in tags:
            if tag_count.get(top_tag, 0) < tag_count[tag]:
                top_tag = tag

        if tag_count.get(top_tag, 0) < 5:
            final_tags["Fixes"].append((title, pr))
        else:
            final_tags[top_tag].append((title, pr))

    return final_tags


def render_prs(tagged_prs):
    out_string = ""
    for tag in tagged_prs:
        out_string += f"# {tag}\n"
        for title, pr in tagged_prs[tag]:
            out_string += f"- {title} [#{pr.number}]({pr.html_url})\n"
        out_string += "\n"
    return out_string

def main():
    # Grab your GH token.
    token = os.environ.get("GITHUB_TOKEN")

    if token is None:
        print("Please set your GITHUB_TOKEN environment variable.")
        exit(1)

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--year', metavar='YEAR', type=int, nargs=1,
                    help='the year to generate a report for')
    parser.add_argument('--month', metavar='MONTH', type=int, nargs=1,
                    help='the month to generate a report for')
    parser.add_argument('--clean', help="remove and regenerate the cached data from the month")

    args = parser.parse_args()
    month = args.month[0]
    year = args.year[0]

    github = Github(token)

    if os.path.isfile(CACHE_PATH):
        with open(CACHE_PATH, 'rb+') as cache_file:
            data = pickle.load(cache_file)
    else:
        data = download_report(github, month, year)
        print(colored("Caching the results from GitHub ...", 'green'))
        with open(CACHE_PATH, 'wb+') as cache_file:
            pickle.dump(data, cache_file)
        print(colored("Cached!", 'green'))

    prs, report, team = data

    tagged_prs = bucket_by_tag(prs)
    prs_string = render_prs(tagged_prs)

    authors = [member for member in team if report[member]['author']]
    authors.sort(key=lambda x:-len(report[x]['author']))
    authors_string = ", ".join(["%s (%d)" % (x, len(report[x]['author'])) for x in authors])

    reviewers = [member for member in team if report[member]['review']]
    reviewers.sort(key=lambda x:-len(report[x]['review']))
    reviewers_string = ", ".join(["%s (%d)" % (x, len(report[x]['review'])) for x in reviewers])

    print("\n# Author details:\n" + "=" * 70)
    for member in authors:
        print(colored(member, 'blue'))
        print("\n".join(report[member]['author']))

    print("\n# Reviewer details:\n" + "=" * 70)
    for member in reviewers:
        print(colored(member, 'green'))
        print("\n".join(report[member]['review']))

    render_report("the_report.md", {
        'month': month,
        'year': year,
        'prs': prs_string,
        'authors': authors_string,
        'reviewers': reviewers_string,
    })
