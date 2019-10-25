# zbxmonitor

## Description
While monitoring a few hosts with Zabbix, it's easy to send alerts by e-mail or SMS. But when something goes wrong (SMTP server or GSM modem is down, etc.), you will not receive any error message.

ZbxMonitor resolves such problems by adding "second channel" from local desktop to Zabbix Server. ZbxMonitor periodically pulls data from Zabbix Server and shows its status in icon tray.

## Usage
If's recommended to not launch zbxmonitor.py directly, but to create symbolic link to this file (eg. `ln -s zbxmonitor.py myzabbix.example.com`)
