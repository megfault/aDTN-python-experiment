from threading import Thread
from time import time, sleep
from subprocess import call
from random import gauss
import sched
from yaml import load
from argparse import ArgumentParser


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

class MessageGenerator:
    """
    Generate messages of the form dn_ct where dn is the name of the device creating the message and ct is a counter
    serving as a unique identifier for the messages created by the device.
    """
    def __init__(self, creation_rate, device_id):
        """
        Initialize the message generator. Generation is scheduled to happen on average every creation_rate seconds,
        following a gaussian distribution.
        :param creation_rate: average time between every two new generated messages
        :param device_id: identifier for the device running this
        """
        self.creation_rate = creation_rate
        self.device_id = device_id
        self.next_message = 0
        self.ms = DataStore()
        self.scheduler = sched.scheduler(time, sleep)
        self.run()

    def writing_interval(self):
        """
        Generate a time interval according to a gaussian distribution around the creation rate.
        :return: interval in seconds between generating two messages
        """
        return abs(gauss(self.creation_rate, self.creation_rate / 4))

    def write_message(self):
        """Add a new message to the message store and reschedule itself."""
        self.scheduler.enter(self.writing_interval(), 2, self.write_message)
        self.ms.add_object(self.device_id + '_' + str(self.next_message))
        self.next_message += 1

    def run(self):
        """ Initialize the scheduling of new message generation."""
        self.scheduler.enter(self.writing_interval(), 2, self.write_message)


class LocationManager:
    """
    Change the ESSID of this device according to a schedule in order to simulate a new set of neighbors.
    """
    def __init__(self, device_id):
        """
        Initialize the location manager.
        :param device_id: identifier for the device running this
        """
        try:
            config = open("scheduling/{}.yaml".format(device_id))
        except OSError:
            print("Invalid schedule.")
            raise
        self.schedule = load(config.read())
        self.scheduler = sched.scheduler(time, sleep)
        self.run()

    def schedule_joining(self, essid):
        """
        Join a wireless ad-hoc network with the given ESSID. Reschedule itself to happen in 24h.
        :param essid: name of the ad-hoc network
        """
        self.scheduler.enter(24 * 60 * 60, 2, self.schedule.joining, (essid,))  # repeat every 24h
        call("iw {} ibss join {} 2432".format(IFACE, essid))

    def schedule_leaving(self):
        """Leave a wireless ad-hoc network. Reschedule itself to happen in 24h."""
        self.scheduler.enter(24 * 60 * 60, 2, self.schedule.leaving)  # repeat every 24h
        call("iw {} ibss leave".format(IFACE))

    def run(self):
        """Schedule all network joinings and leavings for the current device."""
        # make sure the device is not in any ad-hoc network
        call(("iw", IFACE, "ibss", "leave"))
        for network in self.schedule:
            location = network['location']
            begin = network['begin'] * 3600
            end = network['end'] * 3600
            if end < begin:
                # the node is at this location already at "midnight", i.e. now
                # (per definition, it's midnight when the experiment begins)
                call(("iw", IFACE, "ibss",  "join",  location, "2432"))
            self.scheduler.enter(begin, 2, self.schedule_joining, (location,))
            self.scheduler.enter(end, 2 , self.schedule_leaving)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    args = parser.parse_args()

    device_id = args.device_id

    for bs in BATCH_SIZE:
        for sf in SENDING_FREQS:
            # Inform about current config.
            fn = "_".join([str(i) for i in [bs, sf, CREATION_RATE]])
            print("Now running: {}".format(fn))

            # Start aDTN
            t_adtn = Thread(target=aDTN, args =(bs, sf, CREATION_RATE, device_id, IFACE,), kwargs={"data_store": fn})
            t_adtn.start()

            # Start message generation
            t_generate_messages = Thread(target=MessageGenerator, args=(CREATION_RATE, device_id,))
            t_generate_messages.start()

            # Start location manager
            t_location_manager = Thread(target=LocationManager, args=(device_id,))
            t_location_manager.start()


            sleep(EXPERIMENT_DURATION)
            t_adtn._stop()
            t_generate_messages._stop()
            t_location_manager._stop()



