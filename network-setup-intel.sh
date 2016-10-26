#!/bin/sh
set  -ex 

sudo ip l s wlp4s0 down
sudo rmmod iwlmvm iwlwifi 
sudo modprobe iwlwifi
sleep 1
sudo rfkill unblock wifi
sudo ip l s wlp4s0 down
sudo iw dev wlp4s0 set type ibss
sleep 1
sudo ip l s wlp4s0 up
