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
        self.currentIndex = 0
        
        # Stores a list of position - time points, where each position is the
        # sum of the x and z position of the player at that current time
        self.bestLapPoints = []
        self.currentLapPoints = []

        self.interval: float = None

    def insertPoint(self):
        """
        Inserts the current point into the currentLapPoints list.

        Currently this just appends it to the end of the list, as I want them ordered
        by time and this is usually the order the packets arrive in. Change this method
        if the order should be different eg. ordered by distance to another point.
        """
        self.currentLapPoints.append(self.currentPoint)
    
    def updateInterval(self):
        """
        Updates the current interval by comparing the current point to the closest
        point in bestLapPoints.

        How:
        Tracks the index of the previous closest point (self.currentIndex) and uses this
        as a starting point to find the next closest point. As these points are ordered by
        lap time instead of distance, this next point will always be 'to the right' of the last.
        Assuming the player isn't going backwards of course. In which case the interval is the
        least of their concerns.
        """

        if self.bestLap == None:
            return 0

        closestPoint = self.bestLapPoints[self.currentIndex]
        closestDifference = abs(self.currentPoint[0] - closestPoint[0])
        nextIndex = self.currentIndex + 1

        while nextIndex < len(self.bestLapPoints):
            if self.currentIndex == 230:
                logging.info("Reached 230")
            nextDifference = abs(self.currentPoint[0] - self.bestLapPoints[nextIndex][0])
            if nextDifference <= closestDifference:
                closestPoint = self.bestLapPoints[nextIndex]
                closestDifference = nextDifference
                self.currentIndex = nextIndex
                nextIndex += 1
            else:
                possIndex = nextIndex
                possPoint = None
                possDifference = None
                endIndex = possIndex + 100  # Checks next 6 packets
                # check the next couple of points just in case they're closer
                while possIndex < len(self.bestLapPoints) - 1 and possIndex <= endIndex:
                    possIndex += 1
                    possPoint = self.bestLapPoints[possIndex]
                    possDifference = abs(self.currentPoint[0] - possPoint[0])
                    if possDifference <= closestDifference:
                        closestPoint = self.bestLapPoints[possIndex]
                        closestDifference = possDifference
                        self.currentIndex = possIndex
                        nextIndex = possIndex + 1
                        if self.currentIndex == 230:
                            logging.info("Reached 230")
                break

                    
                    



        
        currentInterval = self.currentPoint[1] - closestPoint[1]  # Negative is faster
        self.interval = currentInterval

    def update(self, fdp: ForzaDataPacket):
        """Updates the Interval object with the latest packet"""
        playerLap = int(fdp.lap_no)
        self.currentPoint = (fdp.position_x + fdp.position_z, fdp.cur_lap_time)

        if playerLap == self.currentLap:
            # log another point to the currentLapPoints and calculate the current interval
            self.insertPoint()
            self.updateInterval()

        elif playerLap == self.currentLap + 1:
            # If the player stopped listening on the prev lap and started again on the next lap
            if fdp.cur_lap_time > 1:
                self.currentLap = -1
                self.currentLapPoints = []
                self.syncLap = playerLap + 1
                return

            # just began a new lap, update the lap counter and compare it to best lap
            if self.bestLap is None or fdp.last_lap_time < self.bestLap:  # If player just set a new best lap
                logging.info("Interval: Best Lap! {}".format(fdp.last_lap_time))
                self.bestLapPoints = self.currentLapPoints
                self.bestLap = fdp.last_lap_time
            else: # If player didn't set a best lap
                logging.info("Interval: New Lap. {}".format(fdp.last_lap_time))
                self.currentLapPoints = [self.currentPoint]
                self.currentLap += 1
            self.currentIndex = 0
            self.updateInterval()

        else:  # player lap is not consistent with self.currentLap (eg. started recording in the middle of a session)
            if playerLap == self.syncLap:
                logging.info("Interval: Synced Laps.")
                # player has reached new sync lap, update object and start recording
                self.currentLapPoints = [self.currentPoint]
                self.currentLap = self.syncLap
                self.updateInterval()
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
                    try:
                        logging.info('Interval: {:.2f}s. currentIndex: {}, dist: {:.2f}'.format(interval.getInterval(), interval.currentIndex, (interval.currentPoint - interval.bestLapPoints[interval.currentIndex][0])))
                    except:
                        logging.info('Interval: {:.2f}s. currentIndex: {}'.format(interval.getInterval(), interval.currentIndex))

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
    
