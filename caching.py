"""Provides consistent rules and support for caching and retrieving data (written by Lana)"""

import datetime
import logging
import os
import pickle


class Cache:
    """deletes the cache if it exists, forcing a refresh the next time the cache is got"""

    def clear(self):
        """clears the cache"""
        if self.exists():
            os.remove(self.filename)

    def exists(self):
        """determines if the cache already exists"""
        return os.path.exists(self.filename)

    def get_modification_time(self):
        """gets the last modification time of the cache"""
        if not self.exists():
            self.logger.warning(
                "caching %s : %s",
                self.filename,
                "get_modification_time called on nonexistant cache",
            )
            return datetime.datetime.min
        return datetime.datetime.fromtimestamp(os.path.getmtime(self.filename))

    def get_time_since_modified(self):
        """gets a timedelta representing the time since last update"""
        return datetime.datetime.now() - self.get_modification_time()

    def get_modification_time_string(self):
        """gets a string representing the time since last update"""
        if not self.exists():
            return "Never"

        difftime = self.get_time_since_modified()

        if difftime.seconds < 60 or difftime.seconds > self.lifetime.seconds:
            return "Just now"
        return f"{difftime.seconds // 60} minutes ago"

    def get(self):
        """gets the cache data and updates the cache if it needs to"""
        if not self.exists():
            self.logger.info("caching %s : %s", self.filename, "creating new cache")
            return self.request_and_update()

        difftime = self.get_time_since_modified()
        if difftime > self.lifetime:
            return self.request_and_update()

        try:
            with self.open("rb") as f:
                data = pickle.load(f)
                if not self.valid(data):
                    self.logger.info(
                        "caching %s : %s",
                        self.filename,
                        "cache is invalid, rebuilding it",
                    )
                    return self.request_and_update()
                return data
        except (IOError, EOFError):
            self.logger.error(
                "caching %s : %s",
                self.filename,
                "error encountered while reading cache",
            )
            return self.request_and_update()

    def open(self, mode):
        """opens the cache file and returns the file handler"""
        # * mode - file mode to open in, should be binary
        return open(self.filename, mode)  # pylint: disable=unspecified-encoding

    def request_and_update(self):
        """requests the data and uses it to update the cache"""
        return self.update(self.request())

    def update(self, data):
        """update the cache with the given data"""
        # * data - the data to enter into the cache
        with self.open("wb") as f:
            pickle.dump(data, f)
            return data

    def __init__(self, filename, expires, requestfn, validatefn=lambda x: True):
        """initialize a new cache"""
        # * filename - filename of the cache, doesn't have to exist
        # * expires - time in seconds until this cache expires
        # * requestfn - function to call when requesting new data
        # * validatefn - (optional) takes the cache data and returns false if the
        # cache needs to be refreshed
        self.filename = filename
        self.lifetime = datetime.timedelta(seconds=expires)

        self.request = requestfn
        self.valid = validatefn

        self.logger = logging.getLogger("caching")
