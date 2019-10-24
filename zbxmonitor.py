#!/usr/bin/env python
# -*- coding: utf-8 -*-
#!/usr/bin/python -W ignore

from socket import *
from pyzabbix import *
from subprocess import call
from daemon import Daemon
import time
import os
# import sys
# import getopt
import getpass
import gobject
import notify2
import syslog
import ConfigParser
import warnings
from dialog_nix import *


class Globals:
    def __init__(self, script_name):
        self.script_full_path = os.path.abspath(script_name)
        self.script_dir = os.path.dirname(self.script_full_path)
        self.script_name = os.path.basename(self.script_full_path)
        self.script_short_name = os.path.splitext(self.script_full_path)[0]

        self.config_file = self.script_short_name + ".config"
        self.config = ConfigParser.ConfigParser()

        self.config.read(self.config_file)
        self.zbxhost = self.config.get("zbxCredentials", "host")
        self.zbxuser = self.config.get("zbxCredentials", "user")
        try:
            self.zbxpasswd = self.config.get("zbxCredentials", "passwd")
        except:
            self.zbxpasswd = None
        try:
            self.zbxurl = self.config.get("zbxCredentials", "url")
        except:
            self.zbxurl = "https://" + self.zbxhost + "/zabbix"

        self.tmp_dir = self.script_dir + "/" + "tmp"
        try:
            os.mkdir(self.tmp_dir)
        except:
            pass
        self.zbxlog = self.tmp_dir + "/" + self.zbxhost + ".log"

        self.defaults = {
                        "icon": self.zbxhost,
                        "interval": 60 * 1000,
                        "notify": True,
                        "port": 10051,
                        "text_mode": True,
                        "wav": None,
                        "waw_player": "/usr/bin/mpv"
                        }
        # self.config.read(self.config_file)

        try:
            self.zbxicon = self.script_dir + "/icons/" + self.config.get("zbxOptions", "icon")
        except:
            self.zbxicon = self.script_dir + "/icons/" + self.defaults["icon"]
        try:
            self.zbxinterval = int(self.config.get("zbxOptions", "interval")) * 1000
        except:
            self.zbxinterval = self.defaults["interval"]
        try:
            self.zbxnotify = bool(self.config.get("zbxOptions", "notify"))
        except:
            self.zbxinterval = self.defaults["notify"]
        try:
            self.zbxport = int(self.config.get("zbxOptions", "port"))
        except:
            self.zbxport = self.defaults["port"]
        try:
            self.zbxtext_mode = bool(self.config.get("zbxOptions", "text_mode"))
        except:
            self.zbxtext_mode = self.defaults["text_mode"]
        try:
            self.zbxwav_player = self.config.get("zbxOptions", "wav_player")
        except:
            self.zbxwav_player = self.defaults["wav_player"]
        try:
            self.zbxwav = self.script_dir + "/sounds/" + self.config.get("zbxOptions", "wav")
        except:
            self.zbxwav = self.defaults["wav"]

        self.zbx_ver = ''
        self.zbx_ping = 'ok'
        self.zbx_connected = 'ok'  # ok, port_is_down, not_logged, err_getting_data_1, err_getting_data_2
        self.zbx_status = self.zbx_last_status = 'ok'  # ok, >>current stat<<

        if self.zbxpasswd is None:
            if self.zbxtext_mode:
                print "Zabbix URL:", self.zbxurl
                print "Zabbix user:", self.zbxuser
                self.zbxpasswd = getpass.getpass(prompt="password: ")
            else:
                md = MyDialog()
                mypass = [""]
                md.getPasswd(mypass, self.zbxurl)
                gtk.main()
                self.zbxpasswd = mypass[0]


class TrayTxt:
    def __init__(self, command):
        zbx.status()
        self.flog = open(globals.zbxlog, "a")
        self.flog.write("\n" + globals.script_name + ": ")
        self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())))
        self.flog.write(" on " + globals.zbxhost + " " + command + "\n\n")
        self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + " ")
        self.flog.write(globals.zbx_status + "\n")
        self.flog.flush()
        # globals.script_name + ":", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), "on", globals.zbxhost, command

    def check(self):
        zbx.status()
        syslog.syslog(globals.zbxhost + " status (txt): " + globals.zbx_status)
        if globals.zbx_status != globals.zbx_last_status:
            globals.zbx_last_status = globals.zbx_status
            self.flog.write(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())) + " ")
            self.flog.write(globals.zbx_status + "\n")
            self.flog.flush()
        return globals.zbx_status

    def tray(self):
        gobject.timeout_add(globals.zbxinterval, self.check)
        gobject.MainLoop().run()


class GtkMessages:
    def __init__(self):
        self.statusIcon = gtk.StatusIcon()
        self.statusIcon.connect('activate', self.show_current_stat)
        self.statusIcon.connect('popup-menu', self.on_right_click)
        zbx.status()
        if globals.zbx_status != "ok":
            self.set_icon(globals.zbxicon + "-err.png")
        else:
            self.set_icon(globals.zbxicon + "-ok.png")

    def set_icon(self, icon_file):
        self.statusIcon.set_from_file(icon_file)

    def message(self, data=None, type=gtk.BUTTONS_OK):
        msg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, type, data)
        rval = msg.run()
        msg.destroy()
        return rval

    def make_menu(self, event_button, event_time, data=None):
        menu = gtk.Menu()
        reconnect_item = gtk.MenuItem("Reconnect to " + globals.zbxhost)
        close_item = gtk.MenuItem("Close applet " + globals.zbxhost)

        if globals.zbx_connected != 'ok' and globals.zbx_ping == 'ok':
            menu.append(reconnect_item)
            # add callback
            reconnect_item.connect_object("activate", self.reconnect_to_zbxhost, "reconnect to zbx server")
            reconnect_item.show()

        menu.append(close_item)
        # add callback
        close_item.connect_object("activate", self.close_app, "Really close?")
        close_item.show()

        # Popup the menu
        menu.popup(None, None, None, event_button, event_time)

    def show_current_stat(self, event):
        zbx.status()
        if globals.zbx_status != "ok":
            self.set_icon(globals.zbxicon + "-err.png")
        else:
            self.set_icon(globals.zbxicon + "-ok.png")
        self.message(globals.zbxhost + " current status is:\n\n" + globals.zbx_status)

    def on_right_click(self, data, event_button, event_time):
        self.make_menu(event_button, event_time)

    def reconnect_to_zbxhost(self, data=None):
        zbx.login()
        self.message('Logging to ' + globals.zbxhost + ":\n" + globals.zbx_connected)

    def close_app(self, data=None):
        syslog.syslog(globals.zbxhost + ": disconnected.")
        gtk.main_quit()
        # if self.message(data, gtk.BUTTONS_OK_CANCEL) == gtk.RESPONSE_OK:
        #     gtk.main_quit()


class TrayIcon:
    def __init__(self):
        self.__gmsg = GtkMessages()
        notify2.init("zab_mon")

    def check(self):
        zbx.status()
        syslog.syslog(globals.zbxhost + " status (GUI): " + globals.zbx_status)
        if globals.zbx_status != globals.zbx_last_status:
            globals.zbx_last_status = globals.zbx_status
            if globals.zbxnotify:
                n = notify2.Notification("Zabbix: " + globals.zbxhost, globals.zbx_status)
                if globals.zbx_status == "ok":
                    n.set_urgency(1)
                else:
                    n.set_urgency(2)
                    n.timeout = -1
                n.show()
            # if globals.play_wav:
            if globals.zbxwav is not None:
                try:
                    f = open('/dev/null', 'w')
                    if globals.zbx_status == 'ok':
                        call([globals.zbxwav_player, globals.zbxwav + "-ok.wav"], stdout=f, stderr=f)
                    else:
                        call([globals.zbxwav_player, globals.zbxwav + "-err.wav"], stdout=f, stderr=f)
                except:
                    pass
        if globals.zbx_status == 'ok':
            self.__gmsg.set_icon(globals.zbxicon + "-ok.png")
        else:
            self.__gmsg.set_icon(globals.zbxicon + "-err.png")
        return True

    def tray(self):
        gobject.timeout_add(globals.zbxinterval, self.check)
        gtk.main()


class MyZbx:
    def __init__(self):
        self.zapi = ZabbixAPI(globals.zbxurl, timeout=5)
        self.zapi.session.verify = False
        warnings.filterwarnings("ignore")
        self.login()

    def pingit(self):
        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((globals.zbxhost, globals.zbxport))
            globals.zbx_ping = 'ok'
        except:
            globals.zbx_ping = 'port is down'
        finally:
            sock.close()

    def login(self):
        self.pingit()
        if globals.zbx_ping == 'ok':
            try:
                self.zapi.login(globals.zbxuser, globals.zbxpasswd)
                globals.zbx_connected = 'ok'
                globals.zbx_ver = self.zapi.api_version().split('.')[0]
            except:
                globals.zbx_connected = 'not logged in'
            finally:
                print "Connect: " + globals.zbx_connected

    def status(self):
        self.pingit()
        if globals.zbx_ping != 'ok':
            globals.zbx_status = globals.zbx_ping
            return globals.zbx_status
        if globals.zbx_connected == 'not logged in':
            globals.zbx_status = globals.zbx_connected
            return globals.zbx_status
        globals.zbx_status = self.get_triggers(globals.zbx_ver)
        return globals.zbx_status

    def get_triggers(self, zbx_ver):
        try:
            if zbx_ver == "2":
                # Get a list of all issues (AKA tripped triggers)
                triggers = self.zapi.trigger.get(only_true=1,
                                             skipDependent=1,
                                             monitored=1,
                                             active=1,
                                             output='extend',
                                             expandDescription=1,
                                             expandData='host',
                                             )
                # Do another query to find out which issues are Unacknowledged
                unack_triggers = self.zapi.trigger.get(only_true=1,
                                                   skipDependent=1,
                                                   monitored=1,
                                                   active=1,
                                                   output='extend',
                                                   expandDescription=1,
                                                   expandData='host',
                                                   withLastEventUnacknowledged=1,
                                                   )
            elif zbx_ver == "3" or zbx_ver == "4":
                # Get a list of all issues (AKA tripped triggers)
                triggers = self.zapi.trigger.get(only_true=1,
                                             skipDependent=1,
                                             monitored=1,
                                             active=1,
                                             output='extend',
                                             expandDescription=1,
                                             selectHosts=['host'],
                                             )

                # Do another query to find out which issues are Unacknowledged
                unack_triggers = self.zapi.trigger.get(only_true=1,
                                                   skipDependent=1,
                                                   monitored=1,
                                                   active=1,
                                                   output='extend',
                                                   expandDescription=1,
                                                   selectHosts=['host'],
                                                   withLastEventUnacknowledged=1,
                                                   )
            else:
                return "Unknown ZBX ver. (" + zbx_ver + ")"
            globals.zbx_connected = 'ok'
        except:
            globals.zbx_connected = "Fetch data error."
            return globals.zbx_connected

        unack_trigger_ids = [t['triggerid'] for t in unack_triggers]
        for t in triggers:
            t['unacknowledged'] = True if t['triggerid'] in unack_trigger_ids \
                else False

        # Print a list containing only "tripped" triggers
        triggers.sort()
        rval = ''
        if zbx_ver == "2":
            for t in triggers:
                if int(t['value']) == 1 and t['unacknowledged']:
                    rval += ("{0} - {1} {2}".format(t['host'],
                                                t['description'],
                                                '(Unack)' if t['unacknowledged'] else '') + "\n\n"
                         )
        elif zbx_ver == "3" or zbx_ver == "4":
            for t in triggers:
                if int(t['value']) == 1 and t['unacknowledged']:
                    rval += ("{0} - {1} {2}".format(t['hosts'][0]['host'],
                                                    t['description'],
                                                    '(Unack)' if t['unacknowledged'] else '') + "\n\n"
                             )
        else:
            rval = "Unknown ZBX ver. (" + zbx_ver + ")"
        if rval == '':
            return 'ok'
        else:
            return rval


class myDaemon(Daemon):
    def run(self):
        syslog.openlog(globals.script_name, syslog.LOG_PID | syslog.LOG_NDELAY, syslog.LOG_DAEMON)
        tc.tray()


def main(argv):
    global globals, zbx, tc
    # command - argv[1] (start if no args)

    if len(argv) == 1:
        command = "start"
    else:
        command = argv[1]

    if command in ("start", "stop"):
        pass
    else:
        print "Unknown command"
        sys.exit(2)

    globals = Globals(argv[0])
    print globals.script_name + ":", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())), "on", globals.zbxhost, command

    zbx = MyZbx()
    if (globals.zbxtext_mode):
        tc = TrayTxt(command)
    else:
        tc = TrayIcon()

    f = globals.tmp_dir + "/" + globals.script_name + "." + globals.zbxhost
    pidfile = f + ".pid"
    # stdoutfile = f  + ".out"
    # stderrfile = f + ".log"
    # daemon = myDaemon(pidfile, stderr=stderrfile, stdout=stdoutfile)
    daemon = myDaemon(pidfile)
    if 'start' == command:
        daemon.start(globals.script_name, globals.zbxhost)
    elif 'stop' == command:
        daemon.stop(globals.zbxhost)
    else:
        print "Unknown command"
        sys.exit(2)
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)
