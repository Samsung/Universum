#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from argparse import ArgumentParser
import re
import json
import urllib
from urllib2 import URLError
import sys
import os
import warnings

from mechanize import Browser, LWPCookieJar
import requests

__all__ = [
    'SwarmCliException',
    'create_session',
    'SwarmSession'
]


# ===================================================================================================
# Functions & classes
# ===================================================================================================

class SwarmCliException(Exception):
    pass


def create_session(user, password, swarm_url):
    """Create new or use existing Swarm session.
    :param user: Swarm user ID (same as p4)
    :param password: Swarm user password (same as p4)
    :param swarm_url: Swarm server URL in format 'https://server.com'
    :return: SwarmSession object
    """

    # Internal function for logging into Swarm system
    def login(user, password, swarm_url):

        link = swarm_url + "/login"
        try:
            br.open(link)
        except URLError as e:
            text = unicode(e) + "\nError occurred when trying to open '" + link + "'"
            raise SwarmCliException(text)

        br.select_form(nr=0)
        br["user"] = user
        br["password"] = password
        br.find_control("remember").items[0].selected = True
        result = br.submit()

        login_reply = json.loads(result.read())
        result.close()

        if login_reply.get("isValid") is True and \
           login_reply.get("user") is not None and \
           login_reply.get("user").get("id") == user and \
           login_reply.get("csrf") is not None:

            return login_reply.get("csrf")
        else:
            text = "Swarm session creation not successful.\n" \
                   "Possible reasons of this error:" \
                   "\n * 'user' or 'password' passed to Swarm CLI module incorrectly" \
                   "\n * Swarm web-interface unexpectedly changed" \
                   "\n * Network errors"
            raise SwarmCliException(text)

    # Internal function for getting CSRF without relogging
    def get_csrf(swarm_url):
        result = br.open(swarm_url + "/reviews")
        response = result.read()
        result.close()
        findings = re.search(r"data-csrf\s*=\s*\"(.*?)\"", response, re.M | re.S)

        return findings.group(1)

    # Actual session creation starts here
    csrf = None

    br = Browser()
    br.set_handle_robots(False)
    cj = LWPCookieJar()
    br.set_cookiejar(cj)
    cookie_file = os.path.expanduser("~/swarm.cookies")

    # Any exceptions while loading cookie just cause relogin, no need for further handling
    # pylint: disable = bare-except
    try:
        cj.load(cookie_file)
        csrf = get_csrf(swarm_url)
    except:
        pass

    if csrf is None:
        csrf = login(user, password, swarm_url)

    session = SwarmSession(user, password, swarm_url, csrf, br)
    # If cookie file is not saved it doesn't affect the further script
    try:
        cj.save(cookie_file, ignore_discard=True, ignore_expires=True)
    except Exception as e:
        warnings.warn("The following error occurred when saving the cookie file:\n" + unicode(e))

    return session


class SwarmSession(object):
    """Current Swarm session. Includes CSRF value, user name, user password and swarm server URL"""

    def __init__(self, user, password, swarm_url, csrf, browser):
        self.user = user
        self.password = password
        self.url = swarm_url
        self.csrf = csrf
        self.br = browser

    def last_version(self, review_id):
        """Return last version number.
        :param review_id: Swarm review ID
        :return: version number
        """

        link = self.url + '/api/v1.2/reviews/' + unicode(review_id)

        # Swarm's API requires HTTP Basic Access Authentication for endpoints.
        # The host-unlocked ticket can be used instead of password.
        r = requests.get(link, auth=(self.user, self.password))

        resp = r.json()
        if (r.status_code != 200) or ('error' in resp):
            text = "Cannot get review " + unicode(review_id) + " using '" + link + "'"
            raise SwarmCliException(text)
        if ('review' not in resp) or ('versions' not in resp['review']):
            text = "Unexpected response format for last version calculation"
            raise SwarmCliException(text)

        result = len(resp['review']['versions'])
        return result

    def send_request(self, params, link, action):
        data = urllib.urlencode(params)
        try:
            result = self.br.open(link, data)
            reply = json.loads(result.read())
            result.close()
            if reply.get("isValid") is False:
                raise SwarmCliException(action + " failed.")
        except Exception as e:
            text = unicode(e) + "\n Possible reasons of this error:" + \
                   "\n * No permission for this action" + \
                   "\n * Network problems" + \
                   "\n * Swarm web-interface unexpectedly changed"
            raise SwarmCliException(text)

    def post_comment(self, review_id, text, filename=None, line=None):

        version = self.last_version(review_id)
        context = ''
        if filename and line:
            context = ',"rightLine":' + unicode(line) + ',"file":"' + unicode(filename) + '"'

        parameters = {
            '_csrf': self.csrf,
            'body': unicode(text),
            'context': '{"review":' + unicode(review_id) +
                       ',"version":' + unicode(version) +
                       context +
                       '}',
            'topic': 'reviews/' + unicode(review_id),
            'user': self.user}
        link = self.url + "/comments/add"
        self.send_request(parameters, link, "Posting comment to Swarm review " + unicode(review_id))

    def vote_review(self, review_id, vote_up):
        version = self.last_version(review_id)
        parameters = {
            '_csrf': self.csrf,
            'version': version,
            'user': self.user}
        if vote_up:
            action = "up"
        else:
            action = "down"
        link = self.url + "/reviews/" + unicode(review_id) + "/vote/" + action
        self.send_request(parameters, link, "Voting " + action + " for Swarm review " + unicode(review_id))


# ===================================================================================================
# Parse script options
# ===================================================================================================

def parse_arguments():
    parser = ArgumentParser()

    parser.add_argument("action", metavar="action", choices=["comment", "up", "down"],
                        help="REQUIRED. One of {comment, up, down}. Action to apply to swarm. "
                             "\"comment\" - posts comment, \"up\" - votes review up. \"down\" - votes review down")
    parser.add_argument("text", nargs="?", help="Comment text. Mandatory parameter for posting comments.")

    parser.add_argument("--id", dest="review_id", required=True,
                        help="REQUIRED. Id of the swarm review to apply action to.")
    parser.add_argument("--user", required=True, help="REQUIRED. Swarm user name.")
    parser.add_argument("--password", required=True, help="REQUIRED. Swarm user password.")
    parser.add_argument("--url", dest="swarm_url", required=True,
                        help="REQUIRED. Swarm main page address, no slash in the end.")

    options = parser.parse_args()
    if options.action == "comment" and options.text is None:
        print "Error: comment text is required for posting comments"
        parser.print_help()
        sys.exit(1)

    return options


# ===================================================================================================
# Main functionality
# ===================================================================================================

def main():
    options = parse_arguments()

    current_session = create_session(options.user, options.password, options.swarm_url)
    if current_session is None:
        print "Session creation was unsuccessful."
        sys.exit(1)

    if options.action == "comment":
        current_session.post_comment(options.review_id, options.text)
    else:
        # both up and down are handled here
        current_session.vote_review(options.review_id, options.action == "up")


# ===================================================================================================
# Actual executing
# ===================================================================================================

if __name__ == '__main__':
    main()
