__version__ = '0.1.0'

import argparse
import sys
import os
import time
import calendar
import datetime
import pathlib
import pickle

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
    tvm_news_dir = pathlib.Path(__file__).parent.absolute()
    with open(tvm_news_dir.joinpath('template.md', 'r')) as template:
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

    # get activities
    report = {}
    for member in team:
        report[member] = get_user_activity(github, member, date_filter)
        print("{}, committed {}, reviewed {}".format(colored(member, 'blue'), len(report[member]['author']), len(report[member]['review'])))
        sys.stdout.flush()
        time.sleep(5)

    return (prs, report, team)

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
    if os.path.isfile('~/.tvm_news_cache'):
        data = pickle.load('~/.tvm_news_cache')
    else:
        data = download_report(github, month, year)
        print(colored("Caching the results from GitHub ...", 'green'))
        pickle.dump('~/.tvm_news_cache')
        print(colored("Cached!", 'green'))

    prs, report, team = data

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
        'authors': authors_string,
        'reviewers': reviewers_string,
    })
