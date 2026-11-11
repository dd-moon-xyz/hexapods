---
type: Documentation
title: Start after reboot
---

# Start after reboot

Saving the PM2 process list does not install a boot service. To enable PM2 at boot:

```bash
export PATH="$HOME/.local/bin:$PATH"
pm2 startup systemd
```

Execute the privileged command PM2 prints, then run `make raspi-client-up` to save the process list. This requires sudo access. The desktop must also start automatically; PM2 does not launch Wayland. Boot startup is not enabled by the Makefile.

[Section index](index.md) · [Wiki index](../documentation/overview.md)
