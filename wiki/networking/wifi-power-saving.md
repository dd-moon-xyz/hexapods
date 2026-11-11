---
type: Documentation
title: Wi-Fi power saving
---

# Wi-Fi power saving

For live streaming, disable Wi-Fi power saving to test whether it contributes to intermittent frame delivery delays. Save the setting in the active NetworkManager connection and apply it immediately without reconnecting:

```bash
wifi_profile="$(nmcli -g GENERAL.CONNECTION device show wlan0)"
sudo nmcli connection modify "$wifi_profile" 802-11-wireless.powersave 2
sudo /usr/sbin/iw dev wlan0 set power_save off
```

NetworkManager value `2` disables power saving for future activations of this profile. The `iw` command disables it for the current connection. Repeat the profile change if you switch Wi-Fi networks.

Verify both settings:

```bash
nmcli -g 802-11-wireless.powersave connection show "$wifi_profile"
/usr/sbin/iw dev wlan0 get power_save
```

Expect `2 (disable)` from NetworkManager and `Power save: off` from `iw`. This setting does not establish Wi-Fi as the cause of streaming delays; compare frame timing before and after the change.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
