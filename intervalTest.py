#!/usr/env/python
# -*- coding: utf-8 -*-

# ----------------------------------------------
# Fix line 160 to show current points distance
# Find out why currentIndex stalls (might need to stop
# it being a greedy algorithm eg. just looking at next point)
# Maybe the algo is just bad and sorting is required
# Or I should just implement my own time tracking system
# instead of using forzas
# ----------------------------------------------

# -----------------
# Could try another method where each n metres in the lap, record the
# current lap time, and compare with the last lap at the same point
# ------------------

# ----------------------
# Or another, where the track is split into grid squares of size (n, m).
# Every time the car enters the square, time is logged and compared
# with the best lap. Difference is the interval, and granularity can
# be determined by the size of the grid squares.

# Note, square (0, 0) is not always in the centre of the track.
# ----------------------

# *************************
# - use dist_traveled (or lap_distance)
# dist_traveled is always parallel to the racing surface, meaning sectors
# calculated using this always bisect the track at roughly 90 degrees.
# So, each n metres (eg. 50 metres), find time delta to the same position
# in the last lap.

# Because dist_traveled keeps going up, use lap_distance which is the distance
# traveled during the current lap. This is just the current distance minus the
# total distance traveled at the start of a new lap.

# Put this distance into a dict (ie. metres : time), so each n metres will
# have a new entry in the dict and it can be quickly compared to another lap.

# Need to take only the first measurement, and ignore subsequent entries
# for the same n distance as forza may supply many subsequent packets that have
# the same distance.
#   - if the dict already has an entry in it, ignore the packet
# *************************


import logging
import socket
import datetime as dt
from fdp import ForzaDataPacket

port = 1337

class Interval:
    """
    Maintains all the data related to the interval.
    """

    def __init__(self):
        self.bestLap = None  # The best lap as recorded by this object, not by Forza
        self.currentLap = -1
        self.syncLap = 0  # The lap the player needs to reach to begin recording intervals
        self.currentPoint = None
        self.accuracy = 20  # Size of each mini sector in metres
        self.distanceFactor = 0  # The total distance traveled at the start of the current lap
        
        # Stores a list of lapDistance:int - lapTime:float points, where lapDistance
        # is the distance traveled during that lap in metres, and lapTime is the current
        # lap time recorded at that distance in seconds
        self.bestLapPoints = dict()
        self.currentLapPoints = dict()

        self.interval: float = None

    def insertPoint(self):
        """
        Inserts the current point into the currentLapPoints list.
        """

        # Ignores the point if the mini sector entry already has a value
        miniSector, remainder = divmod(int(self.currentPoint[0]), self.accuracy)
        #miniSector = int(self.currentPoint[0]) % self.accuracy
        if not self.currentLapPoints.get(miniSector):
            self.currentLapPoints[miniSector] = self.currentPoint[1]
    
    def updateInterval(self):
        """
        Updates the current interval by comparing the current point's lap time to
        the best lap's corresponding sector time
        """

        currentTime = self.currentPoint[1]  # In seconds
        miniSector, remainder = divmod(int(self.currentPoint[0]), self.accuracy)
        #miniSector = int(self.currentPoint[0]) % self.accuracy
        bestSectorTime = self.bestLapPoints.get(miniSector, 0)

        if bestSectorTime == 0:
            self.interval = 0
        else:
            self.interval = currentTime - bestSectorTime  # Negative is faster  

    def update(self, fdp: ForzaDataPacket):
        """
        Updates the Interval object with the latest packet
        
        To display an accurate interval, an entire uninterrupted lap needs to be
        recorded as a baseline. So if a player starts the dashboard in the middle of
        a lap, that lap is ignored, and the next lap is used as a baseline. This means
        the interval will appear on the 2nd lap.
        """
        
        playerLap = int(fdp.lap_no)
        currentLapTime = fdp.cur_lap_time
        currentDistance = fdp.dist_traveled
        lapDistance = currentDistance - self.distanceFactor
        self.currentPoint = (lapDistance, currentLapTime)

        if playerLap == self.currentLap:
            # Log the current point if the player is at the start of a new mini sector

            if int(lapDistance) % self.accuracy == 0:
                self.insertPoint()
                self.updateInterval()
                logging.info("Interval update: {:.2f} (Cur Lap)".format(self.interval))

        elif playerLap == self.currentLap + 1:
            
            # If the player stopped listening on the prev lap and started again on the next lap
            if currentLapTime > 1:
                self.currentLap = -1
                self.currentLapPoints = []
                self.syncLap = playerLap + 1
                return

            # just began a new lap, update the lap counter and compare it to best lap
            # Doesn't use the game's best lap - uses an internally tracked best lap which
            # can be a dirty lap. This is to allow the dashboard to be started mid race
            # and still display an interval, and also to allow a useful interval to be
            # displayed when using non-forza-clean limits (eg. some Tora races), but this
            # can be changed
            if self.bestLap is None or fdp.last_lap_time < self.bestLap:  # If player just set a new best lap
                logging.info("Interval: Best Lap! {}".format(fdp.last_lap_time))
                self.bestLapPoints = self.currentLapPoints.copy()
                self.bestLap = fdp.last_lap_time
            else: # If player didn't set a best lap
                logging.info("Interval: New Lap. {}".format(fdp.last_lap_time))
            self.currentLapPoints.clear()

            # update the distance factor and thus the current point's distance
            self.distanceFactor = fdp.dist_traveled
            lapDistance = currentDistance - self.distanceFactor
            self.currentPoint = (lapDistance, currentLapTime)

            self.insertPoint()
            self.currentLap += 1
            self.updateInterval()
            logging.info("Interval update: {:.2f} (New Lap)".format(self.interval))

        else:  # player lap is not consistent with self.currentLap (eg. started recording in the middle of a session)
            if playerLap == self.syncLap:
                logging.info("Interval: Synced Laps")
                # player has reached new sync lap, update object and start recording
                self.currentLapPoints.clear()

                # update the distance factor and thus the current point's distance
                self.distanceFactor = fdp.dist_traveled
                lapDistance = currentDistance - self.distanceFactor
                self.currentPoint = (lapDistance, currentLapTime)

                self.insertPoint()
                self.currentLap = self.syncLap
                self.updateInterval()
                logging.info("Interval update: {:.2f} (Sync)".format(self.interval))
            else:  # Keep ignoring the lap times until the player reaches a new lap
                self.syncLap = playerLap + 1
        
    def getInterval(self):
        """Returns the most up to date interval based on all collected data points.
        If there is not enough data to calculate an interval, return 0."""
        if self.interval:
            return self.interval
        else:
            return 0

def to_str(value):
    '''
    Returns a string representation of the given value, if it's a floating
    number, format it.

    :param value: the value to format
    '''
    if isinstance(value, float):
        return('{:f}'.format(value))

    return('{}'.format(value))

def dump_stream(port):

    interval = Interval()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind(('', port))

        logging.info('listening on port {}'.format(port))
        
        first_packet_received = False
        n_packets = 0
        
        while True:
            message, address = server_socket.recvfrom(1024)
            time_of_arrival = dt.datetime.now()
            fdp = ForzaDataPacket(message)

            if fdp.is_race_on:
                interval.update(fdp)

                if n_packets == 0:
                    logging.info('{}: in race, logging data'.format(dt.datetime.now()))

                n_packets += 1

                if n_packets % 30 == 0:
                    #logging.info('Interval: {:.2f}s. Lap Dist: {:.2f}'.format(interval.getInterval(), interval.currentPoint[0]))
                    pass

                if n_packets % 60 == 0:
                    #logging.info('{}: logged {} packets'.format(dt.datetime.now(), n_packets))
                    #logging.info('Interval: {}s. Lap: {}, '.format(interval.getInterval(), interval.currentLap))
                    pass

            else:
                if n_packets > 0:
                    logging.info('{}: out of race, stopped logging data'.format(dt.datetime.now()))
                n_packets = 0

def main():
    logging.basicConfig(level=logging.INFO)

    dump_stream(port)

    return()

if __name__ == "__main__":
    main()
    
