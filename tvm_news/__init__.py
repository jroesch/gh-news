__version__ = '0.1.0'

import sys
import os
import time

from termcolor import colored  # pip install termcolor
from github import Github      # pip install PyGithub

DATE_FILTER = '2019-04-01..2019-04-30'
GITHUB_TOKEN = "206d62ecaabcf5c81f08b761bfbbb7cb5c868709"

def get_user_activity(g, user_name, date_filter):
    review_template = 'repo:dmlc/tvm commenter:{} updated:{} is:pr'
    author_template = 'repo:dmlc/tvm author:{}    updated:{} is:pr'

    q = review_template.format(user_name, date_filter)
    review_activity = [i.title + " (#" + str(i.number) + ")" for i in g.search_issues(query=q)]
    q = author_template.format(user_name, date_filter)
    author_activity = [i.title + " (#" + str(i.number) + ")" for i in g.search_issues(query=q)]

    return {
        'author': set(author_activity),
        'review': set(review_activity) - set(author_activity),
    }


def main():
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo("dmlc/tvm")
    team = [c.login for c in repo.get_contributors()]

    # get activities
    report = {}
    for member in team:
        report[member] = get_user_activity(g, member, DATE_FILTER)
        print("{}, committed {}, reviewed {}".format(colored(member, 'blue'), len(report[member]['author']), len(report[member]['review'])))
        sys.stdout.flush()
        time.sleep(5)

    print("\n# People Whose Pull Requests are Updated:\n" + "=" * 70)
    authors = [member for member in team if report[member]['author']]
    authors.sort(key=lambda x:-len(report[x]['author']))
    print(", ".join(["%s (%d)" % (x, len(report[x]['author'])) for x in authors]))

    print("\n# People Who Reviewed Pull Requests:\n" + "=" * 70)
    reviewers = [member for member in team if report[member]['review']]
    reviewers.sort(key=lambda x:-len(report[x]['review']))
    print(", ".join(["%s (%d)" % (x, len(report[x]['review'])) for x in reviewers]))

    print("\n# Author details:\n" + "=" * 70)
    for member in authors:
        print(colored(member, 'blue'))
        print("\n".join(report[member]['author']))

    print("\n# Reviewer details:\n" + "=" * 70)
    for member in reviewers:
        print(colored(member, 'green'))
        print("\n".join(report[member]['review']))
