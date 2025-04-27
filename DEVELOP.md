# Mahlkönig X54 Client

## Reverse Engineering

1. Power off Grinder

2. ```bash
   sudo dns-sd -P mahlkoenig-x54-grinder      \
                    _http._tcp                \
                    local                     \
                    80                        \
                    x54grinder-1777d6.local   \
                    10.10.0.13                \
                    sw-build-no=3             \
                    sw-version-no=03.06       \
                    sn=1777D6                 \
                    device=X54-Grinder        \
                    brand=Mahlkoenig          \
                    company=Hemro-Group
   ```

3. ```bash
   sudo dns-sd -P mahlkoenig-x54-grinder     \
                   _ws._tcp                  \
                   local                     \
                   9998                      \
                   x54grinder-1777d6.local   \
                   10.10.0.13                \
                   sw-build-no=3             \
                   sw-version-no=03.06       \
                   sn=1777D6                 \
                   device=X54-Grinder        \
                   brand=Mahlkoenig          \
                   company=Hemro-Group
   ```
4. ```bash
   uv run mitmproxy \
        --mode reverse:http://10.10.0.149:80@80    \ # ip of grinder
        --mode reverse:http://10.10.0.149:9998@9998 \ # ip of grinder
        --listen-host 0.0.0.0   \
        --set flow_detail=3 \
        --set validate_inbound_headers=false
   ```

5. Unlink grinder in app and restart app
6. App should autodiscover mDNS entries
7. Add the grinder
8. Power on grinder, so mDNS resolution happens before Grinder can overwrite entries
9. You should see flows in `mitmproxy`

Example communication:

```bash
websocat ws://10.10.0.149:9998

{ "MsgId": 1, "SessionId": 1, "Login": "REDACTED" }

{"ResponseStatus":{"SourceMessage":"Login","Success":true,"Reason":""},"MsgId":1,"SessionId":2053400890}

{ "MsgId": 2, "SessionId": 20534000890, "RequestType": "MachineInfo"}

{"MachineInfo":{"SerialNo":"1777D6","ProductNo":"HEM-E54-HMI-P02.115","SwVersion":"03.06","SwBuildNo":"3","DiscLifeTime":130027,"Hostname":"x54grinder-1777d6","ApMacAddress":"","CurrentApIpv4":"192.168.4.1","StaMacAddress":"c4:dd:57:c5:69:d4","CurrentStaIpv4":"10.10.0.149"},"MsgId":2,"SessionId":2053400890}
```
