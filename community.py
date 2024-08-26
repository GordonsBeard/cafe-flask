"""Provides wrappers for interfacing with the Steam Community (written by Lana)"""

import datetime
import re
import urllib.request

from bs4 import BeautifulSoup

import caching

COMMUNITY_CACHE_FILE = "community_data.cache"
CACHE_EXPIRE_TIME = 3600  # 1 hour
CONTENT_ONLY_TAG = (
    "?content_only=true"  # query to only receive XML content from a steam URL
)
EXPANDED_MONTHS = {
    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",
    "May": "May",
    "Jun": "June",
    "Jul": "July",
    "Aug": "August",
    "Sep": "September",
    "Oct": "October",
    "Nov": "November",
    "Dec": "December",
}
MODULE_EVENTS = ""  # url of the events list module
MODULE_EVENTS_DETAIL = "events"  # url of the event details module
MODULE_NEWS = "announcements"  # url of the announcement list module
MODULE_NEWS_DETAIL = "announcements/detail"  # url of the annoucnement details module
URL_GROUP_BASE = "https://steamcommunity.com/groups/"  # base url of steam groups
URL_LINK_FILTER = (
    "https://steamcommunity.com/linkfilter/?url="  # steam community link filter
)

cache = caching.Cache(
    COMMUNITY_CACHE_FILE, CACHE_EXPIRE_TIME, (lambda: None), (lambda: True)
)


def get_cache_update_time():
    """gets a string representing when the cache was last updated"""
    return cache.get_modification_time_string()


def get_group_info(group, maxevents=0, maxnews=0):
    """gets the steam info for a particular group"""
    cache.request = lambda: request_group_info(group, maxevents, maxnews)
    cache.valid = lambda data: validate_group_info(data, maxevents, maxnews)
    return cache.get()


def request_group_info(group, maxevents=0, maxnews=0):
    """requests and builds a data structure for a group's steam events and announcements"""
    return {
        "maxevents": maxevents,
        "events": SteamGroup(group).get_event_list(maxevents),
        "maxnews": maxnews,
        "announcements": SteamGroup(group).get_announcement_list(maxnews),
    }


def validate_group_info(data, maxevents=0, maxnews=0):
    """ensures that the cache data is valid"""
    try:
        if data["maxevents"] != maxevents or data["maxnews"] != maxnews:
            return False
        return True
    except KeyError:
        return False


def _format_eventdate_for_yr(date, year):
    """Format an event's date so it matches with the announcements"""
    # expand any compact form months
    for month, expmonth in EXPANDED_MONTHS.items():
        date = date.replace(month, expmonth)

    # reformat the event date and time
    pattern = r"([^@]+) @ ([\S\s]+)"
    match = re.search(pattern, date)
    return f"{match.group(1)}, {year} at {match.group(2)}"


def _format_eventinfo_to_subline(tag):
    """Format an event's server info so that it fits in the subtitle"""
    return str(tag).split("\n", maxsplit=1)[0]


def _remove_community_linkfilter(s):
    """Remove the steam community link filter from any links"""
    return str(s).replace(URL_LINK_FILTER, "")


class SteamGroup:
    """make a group content request to steam, getting only the necessary xml back"""

    def _request_group_content(self, fn, module, group_id=None):
        if group_id:
            url = self.group_url + "/" + module + "/" + str(group_id) + CONTENT_ONLY_TAG
        else:
            url = self.group_url + "/" + module + CONTENT_ONLY_TAG

        # construct and send a request
        req = urllib.request.Request(url)
        f = urllib.request.urlopen(req)
        return fn(f)

    @staticmethod
    def _parse_event_details(req):
        """reads through an xml response and builds a dict of data to construct a new event"""
        bsdata = BeautifulSoup(_remove_community_linkfilter(req.read()))
        data = {
            "title": str(bsdata.h2.string),
            "date": str(
                _format_eventdate_for_yr(
                    bsdata.find("div", class_="announcement_byline").get_text(),
                    datetime.date.today().year,
                )
            ),
            "headline": str(bsdata.p),
            "desc": str(bsdata.p.find_next("p")).replace("</br>", ""),
            "img": str(bsdata.img["src"]),
        }

        if data["desc"] == "None":
            data["desc"] = data["headline"]
            data["headline"] = ""

        return data

    @staticmethod
    def _parse_event_list(req):
        """reads through an xml response and builds a list of all event ids"""
        pattern = re.compile(r"#events/(\d+)")
        bsdata = BeautifulSoup(req.read(), features="html.parser")
        try:
            return [
                re.search(pattern, e.a["href"]).group(1)
                for e in bsdata.find_all("div", class_="upcoming_event")
            ]
        except (AttributeError, IndexError):
            return []

    @staticmethod
    def _parse_announcement_details(req):
        """reads through an xml response and builds a dict of data to construct an announcement"""

        bsdata = BeautifulSoup(req.read(), features="html.parser")

        bodytexts = [str(x).strip() for x in bsdata.find("div", class_="bodytext")]

        data = {
            "title": str(bsdata.h2.string),
            "date": bsdata.find("div", class_="announcement_byline").get_text(),
            "desc": " ".join(bodytexts),
        }
        return data

    @staticmethod
    def _parse_announcement_list(req):
        """reads through an xml response and build a list of all announcement ids"""
        pattern = r"abody_(\d+)"
        bsdata = BeautifulSoup(req.read(), features="html.parser")
        try:
            return [
                re.search(pattern, e["id"]).group(1)
                for e in bsdata.find_all("div", class_="bodytext")
            ]
        except (AttributeError, IndexError):
            return []

    def get_event_details(self, event_id):
        """gets the details of a particular event by event id"""
        data = self._request_group_content(
            self._parse_event_details, MODULE_EVENTS_DETAIL, event_id
        )
        return Event(
            data["title"],
            data["date"],
            data["headline"],
            data["desc"],
            data["img"],
            self.group_url + "/" + MODULE_EVENTS_DETAIL + "/" + event_id,
        )

    def get_event_list(self, maxresults=0):
        """gets a list of all event ids this month"""
        data = []
        for eid in self._request_group_content(self._parse_event_list, MODULE_EVENTS):
            data.append(self.get_event_details(eid))

            # limit our query to the maximum number of results
            maxresults -= 1
            if maxresults == 0:  # note the == is important here
                break
        return data

    def get_announcement_details(self, announcement_id):
        """gets the details of a particular announcement by id"""
        data = self._request_group_content(
            self._parse_announcement_details, MODULE_NEWS_DETAIL, announcement_id
        )
        return Announcement(
            data["title"],
            data["date"],
            data["desc"],
            self.group_url + "/" + MODULE_NEWS_DETAIL + "/" + announcement_id,
        )

    def get_announcement_list(self, maxresults=0):
        """gets a list of the past 5 announcement ids"""
        data = []
        for aid in self._request_group_content(
            self._parse_announcement_list, MODULE_NEWS
        ):
            data.append(self.get_announcement_details(aid))

            # limit our query to the maximum number of results
            maxresults -= 1
            if maxresults == 0:  # note the == is important here
                break
        return data

    def __init__(self, group_id):
        self.group_id = group_id
        self.group_url = URL_GROUP_BASE + group_id


class Announcement:
    """Steam Announcement"""

    def __init__(self, title, date, desc, link):
        self.title = title
        self.date = date
        self.subline = "witty comment goes here"
        self.content = desc
        self.link = link


class Event:
    """Steam Event"""

    def __init__(self, title, date, headline, desc, img, link):
        print(f"desc: '{desc}'; headline: '{headline}'")

        self.title = title
        self.date = date
        self.subline = _format_eventinfo_to_subline(headline)
        self.content = desc
        self.link = link
        self.image = img
