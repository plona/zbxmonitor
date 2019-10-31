#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import platform
# if platform.system() == "Linux":
#     import gtk
# elif platform.system() == "Windows":
#     import gi
#     gi.require_version("Gtk", "3.0")
#     from gi.repository import Gtk as gtk
# else:
#     raise ValueError("Unknown OS")
import gtk
import sys


class MyDialog:

    def getPasswd(self, passwd, host):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(350, 60)
        window.set_position(gtk.WIN_POS_CENTER)
        window.set_title(host + " - ZBX password:")
        window.connect("delete_event", lambda w, e: gtk.main_quit())
        window.connect('key_press_event', self.escape)

        vbox = gtk.VBox(False, 0)
        window.add(vbox)
        vbox.show()

        entry = gtk.Entry()
        entry.set_max_length(50)
        entry.set_invisible_char("*")
        entry.set_visibility(False)
        entry.connect("activate", self.myCallback, entry, window, passwd)
        vbox.pack_start(entry, True, True, 0)
        entry.show()

        hbox = gtk.HBox(False, 0)
        vbox.add(hbox)
        hbox.show()

        button = gtk.Button(stock=gtk.STOCK_CANCEL)
        button.connect("clicked", lambda w: sys.exit(2))
        hbox.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        button = gtk.Button(stock=gtk.STOCK_OK)
        button.connect("clicked", self.myCallback, entry, window, passwd)
        hbox.pack_start(button, True, True, 0)
        button.set_flags(gtk.CAN_DEFAULT)
        button.grab_default()
        button.show()

        window.show()

    def escape(self, widget, event):
        if gtk.gdk.keyval_name(event.keyval) == "Escape":
            #gtk.main_quit()
            #return False
            sys.exit(2)

    def myCallback(self, widget, entry, window, passwd):
        passwd[0] = entry.get_text()
        window.destroy()
        gtk.main_quit()

