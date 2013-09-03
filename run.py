#    iCraft is Copyright 2010-2011 both
#
#    The Archives team:
#                   <Adam Guy> adam@adam-guy.com AKA "Adam01"
#                   <Andrew Godwin> andrew@aeracode.org AKA "Aera"
#                   <Dylan Lukes> lukes.dylan@gmail.com AKA "revenant"
#                   <Gareth Coles> colesgareth2@hotmail.com AKA "gdude2002"
#
#    And,
#
#    The iCraft team:
#                   <Andrew Caluzzi> tehcid@gmail.com AKA "tehcid"
#                   <Andrew Dolgov> fox@bah.org.ru AKA "gothfox"
#                   <Andrew Horn> Andrew@GJOCommunity.com AKA "AndrewPH"
#                   <Brad Reardon> brad@bradness.co.cc AKA "PixelEater"
#                   <Clay Sweetser> CDBKJmom@aol.com AKA "Varriount"
#                   <James Kirslis> james@helplarge.com AKA "iKJames"
#                   <Jason Sayre> admin@erronjason.com AKA "erronjason"
#                   <Jonathon Dunford> sk8rjwd@yahoo.com AKA "sk8rjwd"
#                   <Joseph Connor> destroyerx100@gmail.com AKA "destroyerx1"
#                   <Kamyla Silva> supdawgyo@hotmail.com AKA "NotMeh"
#                   <Kristjan Gunnarsson> kristjang@ffsn.is AKA "eugo"
#                   <Nathan Coulombe> NathanCoulombe@hotmail.com AKA "Saanix"
#                   <Nick Tolrud> ntolrud@yahoo.com AKA "ntfwc"
#                   <Noel Benzinger> ronnygmod@gmail.com AKA "Dwarfy"
#                   <Randy Lyne> qcksilverdragon@gmail.com AKA "goober"
#                   <Willem van der Ploeg> willempieeploeg@live.nl AKA "willempiee"
#
#    Disclaimer: Parts of this code may have been contributed by the end-users.
#
#    iCraft is licensed under the Creative Commons
#    Attribution-NonCommercial-ShareAlike 3.0 Unported License. 
#    To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
#    Or, send a letter to Creative Commons, 171 2nd Street,
#    Suite 300, San Francisco, California, 94105, USA.

#!/usr/bin/python

import os, sys, time, logging, shutil
from reqs.twisted.internet import reactor
from logging.handlers import SMTPHandler
from core.constants import *
from core.server import CoreFactory
from core.controller import ControllerFactory
from ConfigParser import RawConfigParser as ConfigParser

print ("Now starting up iCraft.. Make sure to check and update often. [ helplarge.com/icraft | irc.esper.net #icraft ]")

useConsoleLog = True
# Disable file logging if using nohup.out
if os.name == "posix" and os.path.exists("nohup.out"):
    if "_" in os.environ.keys():
        if os.environ["_"] == "/usr/bin/nohup":
            useConsoleLog = False

if not os.path.exists("logs/"):
    os.mkdir("logs/")
if useConsoleLog and not os.path.exists("logs/console/"):
    os.mkdir("logs/console/")
if useConsoleLog and not os.path.exists("logs/console/console.log"):
    file = open("logs/console/console.log", "w")
    file.write("")
    file.close()

def LogTimestamp():
    if os.path.exists("logs/console/console.log"):
        shutil.copy("logs/console/console.log", "logs/console/console."+time.strftime("%m-%d-%Y_%H",time.localtime(time.time()))+".log")
        f=open("logs/console/console.log",'w')
        f.close()
    reactor.callLater(6*60*60, LogTimestamp) # 24hours*60minutes*60seconds

if useConsoleLog:            
    logging.basicConfig(
        format="%(asctime)s - %(levelname)7s - %(message)s",
        level=("--debug" in sys.argv) and logging.DEBUG or logging.INFO,
        datefmt="%m/%d/%Y (%H:%M:%S)", filename="logs/console/console.log",
    )
    # define a Handler which writes DEBUG messages or higher to the sys.stderr
    console = logging.StreamHandler()
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(asctime)s - %(levelname)7s - %(message)s")
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    LogTimestamp()
else:
    logging.basicConfig(
        format="%(asctime)s - %(levelname)7s - %(message)s",
        level=("--debug" in sys.argv) and logging.DEBUG or logging.INFO,
        datefmt="%m/%d/%Y (%H:%M:%S)",
    )
    logging.log(logging.INFO, "Console Logs aren't being used in favor of nohup.out")

factory = CoreFactory()
factory.makefile("logs/chat.log")
factory.makefile("logs/server.log")
factory.makefile("logs/staff.log")
factory.makefile("logs/whisper.log")
factory.makefile("logs/world.log")
factory.makefile("config/data/")
factory.makefile("core/isoimage/images/")
factory.makefile("core/archives/")
factory.makedatfile("config/data/balances.dat")
factory.makedatfile("config/data/inbox.dat")
factory.makedatfile("config/data/jail.dat")
factory.makedatfile("config/data/titles.dat")
controller = ControllerFactory(factory)
try:
    reactor.listenTCP(factory.config.getint("network", "port"), factory)
except:
    logging.log(logging.ERROR, "Something is already running on Port %s" % (factory.config.getint("network", "port")))
    sys.exit(1)
try:
    reactor.listenTCP(factory.config.getint("network", "controller_port"), controller)
except:
    logging.log(logging.ERROR, "Something is already running on Port %s" % (factory.config.getint("network", "controller_port")))
    sys.exit(1)
money_logger = logging.getLogger('TransactionLogger')
fh = logging.FileHandler('logs/server.log')
formatter = logging.Formatter("%(asctime)s: %(message)s")
fh.setFormatter(formatter)
# Add the handler
money_logger.addHandler(fh)

try:
    reactor.run()
finally:
    # Make sure worlds are flushed
    logging.log(logging.INFO, "Saving server metas...")
    factory.saveMeta()
    logging.log(logging.INFO, "Flushing worlds to disk...")
    for world in factory.worlds.values():
        logging.log(logging.INFO, "Saving: %s" % world.basename);
        world.stop()
        world.save_meta()
    sys.exit(1);
