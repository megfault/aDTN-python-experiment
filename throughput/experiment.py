from time import time, sleep
from subprocess import call
from argparse import ArgumentParser
from atexit import register

from pyadtn.aDTN import aDTN
from pyadtn.utils import info, debug

EXPERIMENT_DURATION = 5 * 60 + 10 # 5 minutes and 5 seconds (in seconds)
IFACE = "wlan0"
FREQ = str(2432)  # 802.11 channel 1

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    parser.add_argument('sending_freq', type=int, help='time between sending of a batch (in seconds)')
    parser.add_argument('batch_size', type=int, help='batch size (in number of packets)')
    args = parser.parse_args()

    device_id = args.device_id
    sf = args.sending_freq
    bs = args.batch_size

    call(("./network-setup.sh", IFACE))
    call(["iw", IFACE, "ibss", "join", "test", FREQ])


    # Inform about current config.
    experiment_id = "throughput_" + "_".join(
        [str(i) for i in ["bs", bs, "sf", sf, "cr"]])
    info("\nNow running: {}".format(experiment_id))

    # Start aDTN
    adtn = aDTN(bs, sf, IFACE, experiment_id)
    adtn.start()

    sleep(EXPERIMENT_DURATION)

    adtn.stop()
