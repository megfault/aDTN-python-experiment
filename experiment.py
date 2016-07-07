from threading import Thread
from time import time, sleep
from subprocess import call
from random import gauss
import sched
from yaml import load
from argparse import ArgumentParser
from atexit import register

from pyadtn.message_store import DataStore
from pyadtn.aDTN import aDTN

# According to http://www.internetlivestats.com/twitter-statistics/ there was an avg of 350,000 tweets/minute in 2015.
# According to http://www.statista.com/statistics/282087/number-of-monthly-active-twitter-users/ Twitter had
# 350,000,000 users in 2015. That makes 0.07 tweets per hour per user, on average - i.e. 1 tweet every 14.28 hours.
CREATION_RATE = 14.28 * 3600  # 14.28 hours in seconds
SENDING_FREQS = [5, 10, 30, 60]
BATCH_SIZE = [1,10]
EXPERIMENT_DURATION = 5 * 24 * 3600 # 5 days in seconds
IFACE = "wlan0"
FREQ = str(2432) # 802.11 channel 1


class MessageGenerator:
    """
    Generate messages of the form dn_ct where dn is the name of the device creating the message and ct is a counter
    serving as a unique identifier for the messages created by the device.
    """
    def __init__(self, creation_rate, device_id, data_store):
        """
        Initialize the message generator. Generation is scheduled to happen on average every creation_rate seconds,
        following a gaussian distribution.
        :param creation_rate: average time between every two new generated messages
        :param device_id: identifier for the device running this
        :param data_store: name of the file where to store the messages
        """
        self.__creation_rate = creation_rate
        self.__device_id = device_id
        self.__next_message = 0
        self.__ms = DataStore(data_store)
        self.__scheduler = sched.scheduler(time, sleep)
        self.__running = None

    def __writing_interval(self):
        """
        Generate a time interval according to a gaussian distribution around the creation rate.
        :return: interval in seconds between generating two messages
        """
        return abs(gauss(self.__creation_rate, self.__creation_rate / 4))

    def __generate_message(self):
        """Add a new message to the message store and reschedule itself if the MessageGenerator has not been instructed
        to stop."""
        if self.__running is True:
            self.__scheduler.enter(self.__writing_interval(), 2, self.__generate_message)
            self.__ms.add_object(self.__device_id + '_' + str(self.__next_message))
            self.__next_message += 1

    def start(self):
        """ Initialize the scheduling of message generation."""
        self.__running = True
        self.__scheduler.enter(self.__writing_interval(), 2, self.__generate_message)
        self.__thread_generate = Thread(target=self.__scheduler.run, kwargs={"blocking": True})
        self.__thread_generate.start()

    def stop(self):
        """ Stop the scheduling of message generation."""
        self.__running = False
        try:
            while not self.__scheduler.empty():
                event = self.__scheduler.queue.pop()
                self.__scheduler.cancel(event)
        except ValueError: # In case the popped event started running in the meantime...
            self.stop() # ...call the stop function once more.
        # By now the scheduler has run empty and so the generating thread has stopped.
        print("Terminated message generator.")

class LocationManager:
    """
    Change the ESSID of this device according to a schedule in order to simulate a new set of neighbors.
    """
    def __init__(self, device_id, adtn_instance):
        """
        Initialize the location manager.
        :param device_id: identifier for the device running this
        """
        try:
            config = open("scheduling/{}.yaml".format(device_id))
        except OSError:
            print("Invalid schedule file.")
            raise
        self.__schedule = load(config.read())
        self.__scheduler = sched.scheduler(time, sleep)
        self.__running = None
        self.__thread_manage_location = None
        self.__adtn_instance = adtn_instance

    def __leave(self):
        print("stopping adtn")
        self.__adtn_instance.stop()
        call(["iw", IFACE, "ibss", "leave"])

    def __join(self, essid):
        call(["iw", IFACE, "ibss", "join", essid, FREQ])
        print("starting adtn")
        self.__adtn_instance.start()

    def __schedule_joining(self, essid):
        """
        Join a wireless ad-hoc network with the given ESSID. Reschedule itself to happen in 24h.
        :param essid: name of the ad-hoc network
        """
        if self.__running is True:
            self.__scheduler.enter(24 * 60 * 60, 2, self.__schedule.joining, (essid,))  # repeat every 24h
            self.__join(essid)

    def __schedule_leaving(self):
        """Leave a wireless ad-hoc network. Reschedule itself to happen in 24h."""
        if self.__running is True:
            self.__scheduler.enter(24 * 60 * 60, 2, self.__schedule.leaving)  # repeat every 24h
            self.__leave()

    def start(self):
        """Schedule all network joinings and leavings for the current device."""
        self.__running = True
        for network in self.__schedule:
            location = network['location']
            begin = network['begin'] * 3600
            end = network['end'] * 3600
            if end < begin:
                # the node is at this location already at "midnight", i.e. now
                # (per definition, it's midnight when the experiment begins)
                self.__join(location)
            self.__scheduler.enter(begin, 2, self.__schedule_joining, (location,))
            self.__scheduler.enter(end, 1, self.__schedule_leaving)
        self.__thread_manage_location = Thread(target=self.__scheduler.run, kwargs={"blocking": True})
        self.__thread_manage_location.start()

    def stop(self):
        self.__running = False
        try:
            while not self.__scheduler.empty():
                event = self.__scheduler.queue.pop()
                self.__scheduler.cancel(event)
        except ValueError:  # In case the popped event started running in the meantime...
            self.stop()  # ...call the stop function once more.
            # By now the scheduler has run empty and so the sending thread has stopped.
        # Now let's just leave any ibss network we might be in:
        self.__leave()
        print("Terminated location manager")

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    args = parser.parse_args()

    device_id = args.device_id
    
    call(("./network-setup.sh", IFACE))

    for bs in BATCH_SIZE:
        for sf in SENDING_FREQS:
            # Inform about current config.
            experiment_id = "message_dissemination_" + "_".join([str(i) for i in ["bs", bs, "sf", sf, "cr", CREATION_RATE]])
            print("Now running: {}".format(experiment_id))

            # Start aDTN
            adtn = aDTN(bs, sf, IFACE, experiment_id)
            register(aDTN.stop, adtn)

            # Start message generation
            mg = MessageGenerator(CREATION_RATE, device_id,experiment_id)
            register(MessageGenerator.stop, mg)
            mg.start()

            # Start location manager
            lm = LocationManager(device_id, adtn)
            register(LocationManager.stop, lm)
            lm.start()

            sleep(EXPERIMENT_DURATION)
            # Experiment is over, stop all threads:
            # "At normal program termination (for instance, if sys.exit() is called or the main module’s execution
            # completes), all functions registered are called in last in, first out order." - atexit's register docs
            # So the following explicit calls are not needed anymore:
            # lm.stop()
            # mg.stop()
            # adtn.stop()