from time import time, sleep
from subprocess import call
from argparse import ArgumentParser

from pyadtn.aDTN import aDTN

SENDING_FREQS = [5, 10, 30, 60]
BATCH_SIZE = [1, 10]
EXPERIMENT_DURATION = 10 * 3600  # 10 minutes in seconds
IFACE = "wlan0"
FREQ = str(2432)  # 802.11 channel 1

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    args = parser.parse_args()

    device_id = args.device_id

    call(("./network-setup.sh", IFACE))

    for bs in BATCH_SIZE:
        for sf in SENDING_FREQS:
            # Inform about current config.
            experiment_id = "throughput_" + "_".join(
                [str(i) for i in ["bs", bs, "sf", sf, "cr"]])
            print("Now running: {}".format(experiment_id))

            # Start aDTN
            adtn = aDTN(bs, sf, IFACE, experiment_id)
            adtn.start()

            sleep(EXPERIMENT_DURATION)

            adtn.stop()
