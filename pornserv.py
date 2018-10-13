#!/usr/bin/env python3

import argparse
import itertools
import pickle
import random
import uuid
import os

import irc3
from irc3.plugins.cron import cron
import praw
import requests


CHANNEL = None
NICK = None
USERNAME = None
REALNAME = None
browsers = []


class RedditBrowser(object):
    def __init__(self, subreddits):
        self.reddit = praw.Reddit(user_agent='Pornserv 0.3')
        args = parse_args()
        dump_path = os.path.dirname(os.path.abspath(__file__))
        self.dump_file = args.nick + '.dump'
        self.subs = {sub_name: None for sub_name in subreddits}
        try:
            with open(self.dump_file, 'rb') as f:
                last_ids = {k: v for k, v in pickle.load(f).items()
                            if k in self.subs}
                self.subs.update(last_ids)
        except FileNotFoundError:
            pass

    def _dump_subs(self):
        with open(self.dump_file, 'wb') as f:
            pickle.dump(self.subs, f)

    def parse_subreddits(self):
        r = []
        for sub in self.subs:
            r.append(self.parse_subreddit(sub))
        self._dump_subs()
        return itertools.chain.from_iterable(r)

    def parse_subreddit(self, sub):
        s = self.reddit.get_subreddit(sub)
        posts = list(s.get_new(limit=1))
        r = []
        for post in posts:
            if post.id == self.subs[sub]:
                break
            r.append((post.title, post.url))
        self.subs[sub] = posts[0].id
        return r

    def poll(self):
        return self.parse_subreddits()


def https_if_possible(url):
    if url.startswith('https://'):
        return url
    https_url = 'https' + url[4:]
    try:
        r = requests.head(https_url, timeout=5)
        if r.status_code == 200:
            return https_url
        else:
            return url
    except:
        return url


def parse_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--server', required=True,
                        help='IRC server to connect to')
    parser.add_argument('--port', required=True, type=int,
                        help='Port to use to connect to IRC')
    parser.add_argument('--channel', required=True,
                        help='Channel to join')
    parser.add_argument('--nick', required=True,
                        help='Nick used by the IRC bot')
    parser.add_argument('--username', required=True,
                        help='Username used by the IRC bot')
    parser.add_argument('--realname', required=True,
                        help='Realname used by the IRC bot')
    parser.add_argument('--password',
                        help='NickServ password (optional)')
    parser.add_argument('--reddit', required=True,
                        help='Comma-separated list of subreddits to parse')
    parser.add_argument('--interval', required=True, type=int,
                        help='Post interval in minutes')
    return parser.parse_args()


@cron('*/' + str(parse_args().interval) + ' * * * *')
def fetch_porn(bot):
    for browser in browsers:
        posts = list(browser.poll())
        for (title, url) in posts:
            url = https_if_possible(url)
            #url_uid = str(uuid.uuid4())[:6]
            bot.privmsg(CHANNEL, "\x0304NSFW\x0F %s" % (url))
			
args = parse_args()
@irc3.event(r'(@(?P<tags>\S+) )?:(?P<ns>NickServ)!service@rizon.net'
            r' NOTICE (?P<nick>'+args.nick+') :This nickname is registered.*')
def register(bot, ns=None, nick=None, **kw):
    try:
        args = parse_args()
        password = args.password
    except KeyError:
        pass
    else:
        if(isinstance(password, str) and len(password) > 0):
            bot.privmsg(ns, 'identify %s' % (password))

def main():
    args = parse_args()
    global browsers, CHANNEL, NICK, REALNAME, USERNAME
    CHANNEL = args.channel
    NICK = args.nick
    REALNAME = args.realname
    USERNAME = args.username
    subreddits = args.reddit.split(',')
    browsers.append(RedditBrowser(subreddits))

    irc3.IrcBot(
        nick=NICK,
        realname=REALNAME,
        username=USERNAME,
        autojoins=[CHANNEL],
        host=args.server,
        port=args.port,
        ssl=True,
        ssl_verify='CERT_NONE',
        verbose=True,
        includes=[
            __name__,
        ]).run()


if __name__ == '__main__':
    main()