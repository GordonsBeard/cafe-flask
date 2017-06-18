# community.py
# Author:       Lana
# Description:  Provides wrappers for interfacing with the Steam Community
# Last Update:  1/30/2015
from bs4 import BeautifulSoup # BeautifulSoup for XML parsing (probably overkill)
import datetime               # datetime for getting the current year and finding cache expiration times
import re                     # regex for regex
import urllib2                # url access interface

import caching                # custom caching module

COMMUNITY_CACHE_FILE  = "community_data.cache"  # filename to cache the community data to
CACHE_EXPIRE_TIME     = 3600                    # time between cache creation and expiration (1 hour)
CONTENT_ONLY_TAG      = "?content_only=true"    # query to only receive XML content from a steam URL
EXPANDED_MONTHS       = { "Jan" : "January",    # expanded form of 3 letter months
                          "Feb" : "February",
                          "Mar" : "March",
                          "Apr" : "April",
                          "May" : "May",
                          "Jun" : "June",
                          "Jul" : "July",
                          "Aug" : "August",
                          "Sep" : "September",
                          "Oct" : "October",
                          "Nov" : "November",
                          "Dec" : "December" }
MODULE_EVENTS         = ""                      # url of the events list module
MODULE_EVENTS_DETAIL  = "events"                # url of the event details module
MODULE_NEWS           = "announcements"         # url of the announcement list module
MODULE_NEWS_DETAIL    = "announcements/detail"  # url of the annoucnement details module
URL_GROUP_BASE        = "https://steamcommunity.com/groups/" # base url of steam groups
URL_LINK_FILTER       = "https://steamcommunity.com/linkfilter/?url=" # steam community link filter

cache                 = caching.Cache( COMMUNITY_CACHE_FILE, CACHE_EXPIRE_TIME, (lambda: None), (lambda: True) )

# gets a string representing when the cache was last updated
def get_cache_update_time( ) :
  return cache.get_modification_time_string( )

# gets the steam info for a particular group
def get_group_info( group, maxevents=0, maxnews=0 ) :
  cache.request = lambda: request_group_info( group, maxevents, maxnews )
  cache.valid   = lambda (data): validate_group_info( data, maxevents, maxnews )
  return cache.get( )

# requests and builds a data structure for a group's steam events and announcements
def request_group_info( group, maxevents=0, maxnews=0 ) :
  return {
      "maxevents" : maxevents,
      "events" : SteamGroup( group ).getEventList( maxevents ),
      "maxnews" : maxnews,
      "announcements" : SteamGroup( group ).getAnnouncementList( maxnews ),
  }

# ensures that the cache data is valid
def validate_group_info( data, maxevents=0, maxnews=0 ) :
  try :
    if data["maxevents"] != maxevents or data["maxnews"] != maxnews :
      return False
    return True
  except KeyError :
    return False

# Format an event's date so it matches with the announcements
def _format_eventdate_for_yr( date, year ) :
  # expand any compact form months
  for month in EXPANDED_MONTHS.keys() :
    date = date.replace( month, EXPANDED_MONTHS[month] )

  # reformat the event date and time
  pattern = "([^@]+) @ ([\S\s]+)"
  match   = re.search( pattern, date )
  return "{}, {} at {}".format( match.group( 1 ), year, match.group( 2 ) )

# Format an event's server info so that it fits in the subtitle
def _format_eventinfo_to_subline( tag ) :
  return str( tag ).split( "\n" )[0]

# Remove the steam community link filter from any links
def _remove_community_linkfilter( s ) :
  return s.replace( URL_LINK_FILTER, "" )

class SteamGroup :
  # make a group content request to steam, getting only the necessary xml back
  def _requestGroupContent( self, fn, module, id=None ) :
    if id :
      url = self.groupUrl + '/' + module + '/' + str( id ) + CONTENT_ONLY_TAG
    else :
      url = self.groupUrl + '/' + module + CONTENT_ONLY_TAG

    # construct and send a request
    req = urllib2.Request( url )
    f   = urllib2.urlopen( req )
    return fn( f )

  # reads through an xml response and builds a dict of data to construct a new event
  @staticmethod
  def _parseEventDetails( req ) :
    bsdata = BeautifulSoup( _remove_community_linkfilter( req.read( ) ) )
    data = {
      "title"     : str( bsdata.h2.string ),
      "date"      : str( _format_eventdate_for_yr( bsdata.find( "div", class_="announcement_byline" ).get_text(), datetime.date.today().year ) ),
      "headline"  : str( bsdata.p ),
      "desc"      : str( bsdata.p.find_next( "p" ) ).replace( '</br>', '' ),
      "img"       : str( bsdata.img["src"] )
    }

    if data['desc'] == 'None' :
        data['desc'] = data['headline']
        data['headline'] = ''

    return data

  # reads through an xml response and builds a list of all event ids
  @staticmethod
  def _parseEventList( req ) :
    pattern = re.compile( "#events/(\d+)" )
    bsdata = BeautifulSoup( req.read() )
    try :
      return [re.search( pattern, e.a['href'] ).group( 1 ) for e in bsdata.find_all( "div", class_="upcoming_event" )]
    except (AttributeError, IndexError) :
      return []

  # reads through an xml response and builds a dict of data to construct a new announcement
  @staticmethod
  def _parseAnnouncementDetails( req ) :
    bsdata = BeautifulSoup( _remove_community_linkfilter( req.read( ) ) )
    data = {
      "title"     : str( bsdata.h2.string ),
      "date"      : str( bsdata.find( "div", class_="announcement_byline" ).get_text() ),
      "desc"      : str( "".join( map( unicode, bsdata.find( "div", class_="bodytext" ).contents ) ) ).replace( '</br>', '' ),
    }
    return data

  # reads through an xml response and build a list of all announcement ids
  @staticmethod
  def _parseAnnouncementList( req ) :
    pattern = "abody_(\d+)"
    bsdata = BeautifulSoup( req.read() )
    try :
      return [re.search( pattern, e['id'] ).group( 1 ) for e in bsdata.find_all( "div", class_="bodytext" )]
    except (AttributeError, IndexError) :
      return []

  # gets the details of a particular event by event id
  def getEventDetails( self, id ) :
    data = self._requestGroupContent( self._parseEventDetails, MODULE_EVENTS_DETAIL, id )
    return Event( data['title'], data['date'], data['headline'], data['desc'], data['img'], self.groupUrl + '/' + MODULE_EVENTS_DETAIL + '/' + id )

  # gets a list of all event ids this month
  def getEventList( self, maxresults=0 ) :
    data = []
    for eid in self._requestGroupContent( self._parseEventList, MODULE_EVENTS ) :
      data.append( self.getEventDetails( eid ) )

      # limit our query to the maximum number of results
      maxresults -= 1
      if maxresults == 0 :  # note the == is important here
        break;
    return data

  # gets the details of a particular announcement by id
  def getAnnouncementDetails( self, id ) :
    data = self._requestGroupContent( self._parseAnnouncementDetails, MODULE_NEWS_DETAIL, id )
    return Announcement( data['title'], data['date'], data['desc'], self.groupUrl + '/' + MODULE_NEWS_DETAIL + '/' + id )

  # gets a list of the past 5 announcement ids
  def getAnnouncementList( self, maxresults=0 ) :
    data = []
    for aid in self._requestGroupContent( self._parseAnnouncementList, MODULE_NEWS ) :
      data.append( self.getAnnouncementDetails( aid ) )

      # limit our query to the maximum number of results
      maxresults -= 1
      if maxresults == 0 :  # note the == is important here
        break;
    return data

  def __init__( self, id ) :
    self.groupId      = id
    self.groupUrl     = URL_GROUP_BASE + id

class Announcement :
  def __init__( self, title, date, desc, link ) :
    self.title    = title
    self.date     = date
    self.subline  = "witty comment goes here"
    self.content  = desc
    self.link     = link

class Event :
  def __init__( self, title, date, headline, desc, img, link ) :
    print( "desc: '{}'; headline: '{}'".format( desc, headline ) )

    self.title    = title
    self.date     = date
    self.subline  = _format_eventinfo_to_subline( headline )
    self.content  = desc
    self.link     = link
    self.image    = img
