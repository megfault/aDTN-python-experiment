from time import time, sleep
from subprocess import call
from argparse import ArgumentParser
from atexit import register

from pyadtn.aDTN import aDTN
from pyadtn.utils import info, debug

SENDING_FREQS = [10]
BATCH_SIZE = [10]
EXPERIMENT_DURATION = 1 * 60  # 1 minute in seconds
IFACE = "wlan0"
FREQ = str(2432)  # 802.11 channel 1

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    args = parser.parse_args()

    device_id = args.device_id

    call(("./network-setup.sh", IFACE))
    call(["iw", IFACE, "ibss", "join", "test", FREQ])

    for bs in BATCH_SIZE:
        for sf in SENDING_FREQS:
            # Inform about current config.
            experiment_id = "throughput_" + "_".join(
                [str(i) for i in ["bs", bs, "sf", sf, "cr"]])
            info("\nNow running: {}".format(experiment_id))

            # Start aDTN
            adtn = aDTN(bs, sf, IFACE, experiment_id)
            register(aDTN.stop, adtn)
            adtn.start()

            sleep(EXPERIMENT_DURATION)

            adtn.stop()
