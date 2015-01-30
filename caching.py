# caching.py
# Author:       Lancey
# Description:  Provides consistent rules and support for caching and retrieving data
# Last Update:  1/30/2015
import cPickle as pickle    # cPickle is faster and better than regular pickle
import datetime             # datetime used for checking cache expiration times
import logging              # log module for debugging purposes
import os                   # os extensions for confirming if a cache file exists

class Cache :
    # deletes the cache if it exists, forcing a refresh the next time the cache is gotten
    def clear( self ) :
      if self.exists( ) :
        os.remove( self.filename )

    # determines if the cache already exists
    def exists( self ) :
      return os.path.exists( self.filename )

    # gets the last modification time of the cache
    def get_modification_time( self ) :
      if not self.exists( ) :
        self.logger.warning( "caching %s : %s", self.filename, "get_modification_time called on nonexistant cache" )
        return datetime.datetime.min
      return datetime.datetime.fromtimestamp( os.path.getmtime( self.filename ) )

    # gets a timedelta representing the time since last update
    def get_time_since_modified( self ) :
      return datetime.datetime.now() - self.get_modification_time()

    # gets a string representing the time since last update
    def get_modification_time_string( self ) :
      if not self.exists( ) :
        return "Never"

      difftime = self.get_time_since_modified()

      if difftime.seconds < 60 or difftime > self.lifetime :
        return "Just now"
      return "{} minutes ago".format( difftime.seconds // 60 )

    # gets the cache data and updates the cache if it needs to
    def get( self ) :
      if not self.exists( ) :
        self.logger.info( "caching %s : %s", self.filename, "creating new cache" )
        return self.request_and_update( )

      difftime = self.get_time_since_modified( )
      if difftime > self.lifetime :
        return self.request_and_update( )

      else :
        try :
          with self.open( 'rb' ) as f :
            data = pickle.load( f )
            if not self.valid( data ) :
              self.logger.info( "caching %s : %s", self.filename, "cache is invalid, rebuilding it" )
              return self.request_and_update( )
            else :
              return data
        except (IOError, EOFError) :
          self.logger.error( "caching %s : %s", self.filename, "error encountered while reading cache" )
          return self.request_and_update( )

    # opens the cache file and returns the file handler
    # * mode - file mode to open in, should be binary
    def open( self, mode ) :
      return open( self.filename, mode )

    # requests the data and uses it to update the cache
    def request_and_update( self ) :
      return self.update( self.request( ) )

    # update the cache with the given data
    # * data - the data to enter into the cache
    def update( self, data ) :
      with self.open( 'wb' ) as f :
        pickle.dump( data, f )
        return data

    # initialize a new cache
    # * filename - filename of the cache, doesn't have to exist
    # * expires - time in seconds until this cache expires
    # * requestfn - function to call when requesting new data
    # * validatefn - (optional) takes the cache data and returns false if the cache needs to be refreshed
    def __init__( self, filename, expires, requestfn, validatefn=(lambda (x): True) ) :
      self.filename = filename
      self.lifetime = datetime.timedelta( seconds=expires )

      self.request  = requestfn
      self.valid    = validatefn

      self.logger   = logging.getLogger( 'caching' )
