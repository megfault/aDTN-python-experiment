#!/bin/sh

DEVICE="$1"

set  -ex 

ip l s $DEVICE down
rmmod ath9k 
modprobe ath9k 
sleep 1
ip l s $DEVICE down
iw dev $DEVICE set type ibss
sleep 1
ip l s $DEVICE up
