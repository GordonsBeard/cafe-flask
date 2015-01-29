# community.py
# Author:       Lancey
# Description:  Provides wrappers for interfacing with the Steam Community
# Last Update:  1/28/2015
from bs4 import BeautifulSoup # BeautifulSoup for XML parsing (probably overkill)
import cPickle as pickle      # pickle for saving data to our cache
import datetime               # datetime for getting the current year and finding cache expiration times
import os                     # os interface for checking if the cache already exists
import re                     # regex for regex
import urllib2                # url access interface

COMMUNITY_CACHE_FILE  = "community_data.cache"  # filename to cache the community data to
CACHE_EXPIRE_TIME     = 3600                    # time between cache creation and expiration (15 minutes)
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
MODULE_EVENTS         = "events"                # url of the events list module
MODULE_EVENTS_DETAIL  = "events"                # url of the event details module
MODULE_NEWS           = "announcements"         # url of the announcement list module
MODULE_NEWS_DETAIL    = "announcements/detail"  # url of the annoucnement details module
URL_GROUP_BASE        = "https://steamcommunity.com/groups/" # base url of steam groups
URL_LINK_FILTER       = "https://steamcommunity.com/linkfilter/?url=" # steam community link filter

# gets the modification time of a file as datetime
def modification_time( filename ) :
  t = os.path.getmtime( filename )
  return datetime.datetime.fromtimestamp( t )

# gets a string representing when the cache was last updated
def get_cache_update_time( ) :
  if not os.path.exists( COMMUNITY_CACHE_FILE ) :
    return "Never"
  rightnow  = datetime.datetime.now()
  infomtime = modification_time( COMMUNITY_CACHE_FILE )
  difftime  = rightnow - infomtime
  if difftime.seconds < 60 or difftime.seconds > CACHE_EXPIRE_TIME :
    return "Just now"
  return "{} minutes ago".format( difftime.seconds // 60 )

# gets the group info dict from the cache or requests a new dict
def get_group_info( group, maxevents=0, maxnews=0 ) :
  # check that the cache exists and create it if it doesn't
  if not os.path.exists( COMMUNITY_CACHE_FILE ) :
    return request_group_info( group, maxevents, maxnews )

  # check that the cache is still up to date
  rightnow  = datetime.datetime.now()
  infomtime = modification_time( COMMUNITY_CACHE_FILE )
  difftime  = datetime.timedelta( 0, CACHE_EXPIRE_TIME, 0 )

  if (rightnow - infomtime) > difftime :
    return request_group_info( group, maxevents, maxnews )

  # read the group info from the cache
  else :
    with open( COMMUNITY_CACHE_FILE, 'rb' ) as f :
      try :
        # make sure that we've queried enough information
        data = pickle.load( f )
        if data["maxevents"] != maxevents or data["maxnews"] != maxnews :
          return request_group_info( group, maxevents, maxnews )
        return data
      except IOError :
        # a read error occurred, just query the info again
        return request_group_info( group, maxevents, maxnews )

# requests a new copy of the group events and announcements from steam
def request_group_info( group, maxevents=0, maxnews=0 ) :
  with open( COMMUNITY_CACHE_FILE, 'wb' ) as f :
    # query our data and then dump it to the cache
    data = {
      "maxevents" : maxevents,
      "events" : SteamGroup( group ).getEventList( maxevents ),
      "maxnews" : maxnews,
      "announcements" : SteamGroup( group ).getAnnouncementList( maxnews ),
    }
    pickle.dump( data, f )
    return data

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
      "headline"  : str( bsdata.find_all( "p" )[0] ),
      "desc"      : str( bsdata.find_all( "p" )[1] ).replace( '</br>', '' ),
    }
    return data

  # reads through an xml response and builds a list of all event ids
  @staticmethod
  def _parseEventList( req ) :
    pattern = "(\d+)_eventBlock"
    bsdata = BeautifulSoup( req.read() )
    return [re.search( pattern, e['id'] ).group( 1 ) for e in bsdata.find_all( "div", class_="eventBlock" )]

  # reads through an xml response and builds a dict of data to construct a new announcement
  @staticmethod
  def _parseAnnouncementDetails( req ) :
    bsdata = BeautifulSoup( _remove_community_linkfilter( req.read( ) ) )
    data = {
      "title"     : str( bsdata.h2.string ),
      "date"      : str( bsdata.find( "div", class_="announcement_byline" ).get_text() ),
      "desc"      : str( bsdata.find( "div", class_="bodytext" ) ).replace( '</br>', '' ),
    }
    return data

  # reads through an xml response and build a list of all announcement ids
  @staticmethod
  def _parseAnnouncementList( req ) :
    pattern = "abody_(\d+)"
    bsdata = BeautifulSoup( req.read() )
    return [re.search( pattern, e['id'] ).group( 1 ) for e in bsdata.find_all( "div", class_="bodytext" )]

  # gets the details of a particular event by event id
  def getEventDetails( self, id ) :
    data = self._requestGroupContent( self._parseEventDetails, MODULE_EVENTS_DETAIL, id )
    return Event( data['title'], data['date'], data['headline'], data['desc'], self.groupUrl + '/' + MODULE_EVENTS_DETAIL + '/' + id )

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
  def __init__( self, title, date, headline, desc, link ) :
    self.title    = title
    self.date     = date
    self.subline  = _format_eventinfo_to_subline( headline )
    self.content  = desc
    self.link     = link
