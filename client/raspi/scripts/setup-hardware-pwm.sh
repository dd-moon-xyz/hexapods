#!/bin/sh
# Run with sudo on the Raspberry Pi 5; enable only the LED's PWM0 controller.
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo "Run: sudo sh scripts/setup-hardware-pwm.sh" >&2
    exit 1
fi
case "$(tr -d '\000' < /proc/device-tree/model)" in
    *"Raspberry Pi 5"*) ;;
    *) echo "This configuration is for Raspberry Pi 5 only." >&2; exit 1 ;;
esac
config=/boot/firmware/config.txt
overlay='dtoverlay=pwm,pin=18,func=2'
# Apply now without a reboot, unless PWM0 is already enabled.
if [ ! -d /sys/bus/platform/devices/1f00098000.pwm/pwm ]; then
    /usr/bin/dtoverlay pwm pin=18 func=2
fi
if [ ! -d /sys/bus/platform/devices/1f00098000.pwm/pwm ]; then
    echo 'PWM0 did not become available; boot configuration was not changed.' >&2
    exit 1
fi
if ! grep -Fqx "$overlay" "$config"; then
    cp -p "$config" "$config.lenia-led-backup-$(date +%Y%m%d-%H%M%S)"
    printf '\n[all]\n# Lenia client LED: GPIO18 / physical pin 12\n%s\n' "$overlay" >> "$config"
fi
echo 'PWM0 enabled now and configured for reboot. Run: make restart'
