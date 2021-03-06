from time import sleep
from subprocess import call
from argparse import ArgumentParser

from pyadtn.aDTN import aDTN

IFACE = "wlan0"
FREQ = str(2432)  # 802.11 channel 5

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('device_id', type=str, help='the hostname of this device')
    parser.add_argument('sending_freq', type=float, help='time between sending of a batch (in seconds)')
    parser.add_argument('batch_size', type=int, help='batch size (in number of packets)')
    parser.add_argument('duration', type=int, help='experiment duration (in seconds)')
    args = parser.parse_args()

    device_id = args.device_id
    sf = args.sending_freq
    bs = args.batch_size
    experiment_duration = args.duration

    call(("./network-setup.sh", IFACE))
    call(["iw", IFACE, "ibss", "join", "test", FREQ])
    sleep(5)

    # Inform about current config.
    experiment_id = "throughput_" + "_".join(
        [str(i) for i in ["bs", bs, "sf", sf, "cr"]])

    # Start aDTN
    adtn = aDTN(bs, sf, IFACE, experiment_id)
    adtn.start()

    sleep(experiment_duration)

    adtn.stop()
