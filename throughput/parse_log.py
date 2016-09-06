from argparse import ArgumentParser

def parse(fn, st, et):
    snd_ct = 0
    rcv_ct = 0
    sf = None
    bs = None
    with open("network_events.log") as events_file:
        for line in events_file:
            items = line[:-1].split(" ")
            if items[1][:5] == "start":
                t, bs, sf = items[1].split("-")
            else:
                time = items[0][1:-1]
                if st <= time <= et:
                    event = items[1]
                    if event == "snt":
                        snd_ct += int(items[2])
                    elif event == "rcv":
                        rcv_ct += 1
    print("sf: {}, bs: {}, snd_ct: {}, rcv_ct: {}".format(sf, bs, snd_ct, rcv_ct))

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('filename', type=str, help='log file name')
    parser.add_argument('start_time', type=float, help='start time for counting stats')
    parser.add_argument('end_time', type=float, help='end time for counting stats')
    args = parser.parse_args()

    parse(args.filename, args.start_time, args.end_time)