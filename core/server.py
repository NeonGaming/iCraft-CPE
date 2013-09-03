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
#    Suite 300, San Francisco, California, 94105, USA

import urllib2, time, logging, os, re, sys, datetime, shutil, traceback, pickle, threading, socket, gc, hashlib, random
from urllib import urlencode
from core.console import StdinPlugin
from Queue import Queue, Empty
from reqs.twisted.internet.protocol import Factory
from reqs.twisted.internet import reactor
from ConfigParser import RawConfigParser as ConfigParser
from core.protocol import CoreServerProtocol
from core.world import World
from core.irc_client import ChatBotFactory
from core.constants import *
from core.plugins import *
from core.timer import ResettableTimer
import hashlib

class Heartbeat(object):
    """
Deals with registering with the Minecraft main server every so often.
The Salt is also used to help verify users' identities.
    """

    def __init__(self, factory):
        self.factory = factory
        self.turl()

    def turl(self):
        try:
            threading.Thread(target=self.get_url).start()
        except:
            logging.log(logging.ERROR, traceback.format_exc())
            reactor.callLater(1, self.turl)

    def get_url(self):
        host = 'www.classicube.net'
        path = '/server/heartbeat'
        proto = 'http'
        try:
            self.factory.last_heartbeat = time.time()
            fh = urllib2.urlopen("%s://%s%s?%s" % (proto,host,path,urlencode({
            "port": self.factory.config.getint("network", "port"),
            "users": len(self.factory.clients),
            "max": self.factory.max_clients,
            "name": self.factory.server_name,
            "public": self.factory.public,
            "version": 7,
            "salt": hashlib.md5("self.factory.salt").hexdigest(),
            })))
            self.url = fh.read().strip()
            logging.log(logging.INFO, "Heartbeat Sent. Your URL (saved to docs/SERVERURL): %s" % self.url)
            open('docs/SERVERURL', 'w').write(self.url)
            if not self.factory.console.is_alive():
                self.factory.console.run()
        except urllib2.URLError as r:
            logging.log(logging.ERROR, "%s seems to be offline: %s" % (host,r))
        except:
            logging.log(logging.ERROR, traceback.format_exc())
        finally:
            reactor.callLater(60, self.get_url)

class CoreFactory(Factory):
    """
    Factory that deals with the general world actions and cross-user comms.
    """
    protocol = CoreServerProtocol
    
    def reloadIrcBot(self):
        if(self.irc_relay):
            try:
                self.irc_relay.quit("Reloading the IRC Bot...")
                global ChatBotFactory
                del ChatBotFactory
                from core.irc_client import ChatBotFactory
                if self.ircbot and self.use_irc:
                    self.irc_nick = self.irc_config.get("irc", "nick")
                    self.irc_pass = self.irc_config.get("irc", "password")
                    self.irc_channel = self.irc_config.get("irc", "channel")
                    self.irc_cmdlogs = self.irc_config.getboolean("irc", "cmdlogs")
                    self.ircbot = self.irc_config.getboolean("irc", "ircbot")
                    self.staffchat = self.irc_config.getboolean("irc", "staffchat")
                    self.irc_relay = ChatBotFactory(self)
                    if self.ircbot and not (self.irc_channel == "#icraft" or self.irc_channel == "#channel") and not self.irc_nick == "botname":
                        reactor.connectTCP(self.irc_config.get("irc", "server"), self.irc_config.getint("irc", "port"), self.irc_relay)
                    else:
                        logging.log(logging.ERROR, "IRC Bot failed to connect, you could modify, rename or remove irc.conf")
                        logging.log(logging.ERROR, "You need to change your 'botname' and 'channel' fields to fix this error or turn the bot off by disabling 'ircbot'")
                    return True
            except:
                return False
        return False

    def reloadConfig(self):
        try:
            # TODO: Figure out which of these would work dynamically, otherwise delete them from this area.
            self.owner = self.config.get("main", "owner").lower()
            self.duplicate_logins = self.options_config.getboolean("options", "duplicate_logins")
            self.info_url = self.options_config.get("options", "info_url")
            self.away_kick = self.options_config.getboolean("options", "away_kick")
            self.away_time = self.options_config.getint("options", "away_time")
            self.colors = self.options_config.getboolean("options", "colors")
            self.physics_limit = self.options_config.getint("worlds", "physics_limit")
            self.default_backup = self.options_config.get("worlds", "default_backup")
            self.asd_delay = self.options_config.getint("worlds", "asd_delay")
            self.gchat = self.options_config.getboolean("worlds", "gchat")
            self.grief_blocks = self.ploptions_config.getint("antigrief", "blocks")
            self.grief_time = self.ploptions_config.getint("antigrief", "time")
            self.backup_freq = self.ploptions_config.getint("backups", "backup_freq")
            self.backup_default = self.ploptions_config.getboolean("backups", "backup_default")
            self.backup_max = self.ploptions_config.getint("backups", "backup_max")
            self.backup_auto = self.ploptions_config.getboolean("backups", "backup_auto")
            self.enable_archives = self.ploptions_config.getboolean("archiver", "enable_archiver")
            self.currency = self.ploptions_config.get("bank", "currency")
            self.build_director = self.ploptions_config.get("build", "director")
            self.build_admin = self.ploptions_config.get("build", "admin")
            self.build_mod = self.ploptions_config.get("build", "mod")
            self.build_op = self.ploptions_config.get("build", "op")
            self.build_other = self.ploptions_config.get("build", "other")
            if self.backup_auto:
                reactor.callLater(float(self.backup_freq * 60),self.AutoBackup)
        except:
            return False

    def __init__(self):
        self.ServerVars = dict()
        self.specs = ConfigParser()
        self.last_heartbeat = time.time()
        self.lastseen = ConfigParser()
        self.config = ConfigParser()
        self.options_config = ConfigParser()
        self.ploptions_config = ConfigParser()
        self.wordfilter = ConfigParser()
        self.save_count = 1
        try:
            self.config.read("config/main.conf")
        except:
            logging.log(logging.ERROR, "Something is messed up with your main.conf file. (Did you edit it in Notepad?)")
            sys.exit(1)
        try:
            self.options_config.read("config/options.conf")
        except:
            logging.log(logging.ERROR, "Something is messed up with your options.conf file. (Did you edit it in Notepad?)")
            sys.exit(1)
        try:
            self.ploptions_config.read("config/ploptions.conf")
        except:
            logging.log(logging.ERROR, "Something is messed up with your ploptions.conf file. (Did you edit it in Notepad?)")
            sys.exit(1)
        self.use_irc = False
        if  (os.path.exists("config/irc.conf")):
            self.use_irc = True
            self.irc_config = ConfigParser()
            try:
                self.irc_config.read("config/irc.conf")
            except:
                logging.log(logging.ERROR, "Something is messed up with your irc.conf file. (Did you edit it in Notepad?)")
                sys.exit(1)
        self.saving = False
        try:
            self.max_clients = self.config.getint("main", "max_clients")
            self.server_message = self.config.get("main", "description")
            self.public = self.config.getboolean("main", "public")
            self.controller_port = self.config.get("network", "controller_port")
            self.controller_password = self.config.get("network", "controller_password")
            self.server_name = self.config.get("main", "name")
            if self.server_name == "iCraft Server":
                logging.log(logging.ERROR, "You forgot to give your server a name.")
            self.owner = self.config.get("main", "owner").lower()
            if self.owner == "yournamehere":
                logging.log(logging.ERROR, "You forgot to make yourself the server owner.")
        except:
            logging.log(logging.ERROR, "You don't have a main.conf file! You need to rename main.example.conf to main.conf")
            sys.exit(1)
        try:
            self.duplicate_logins = self.options_config.getboolean("options", "duplicate_logins")
            self.info_url = self.options_config.get("options", "info_url")
            self.away_kick = self.options_config.getboolean("options", "away_kick")
            self.away_time = self.options_config.getint("options", "away_time")
            self.colors = self.options_config.getboolean("options", "colors")
            self.physics_limit = self.options_config.getint("worlds", "physics_limit")
            self.default_name = self.options_config.get("worlds", "default_name")
            self.default_backup = self.options_config.get("worlds", "default_backup")
            self.asd_delay = self.options_config.getint("worlds", "asd_delay")
            self.gchat = self.options_config.getboolean("worlds", "gchat")
        except:
            logging.log(logging.ERROR, "You don't have a options.conf file! You need to rename options.example.conf to options.conf")
            sys.exit(1)
        try:
            self.grief_blocks = self.ploptions_config.getint("antigrief", "blocks")
            self.grief_time = self.ploptions_config.getint("antigrief", "time")
            self.backup_freq = self.ploptions_config.getint("backups", "backup_freq")
            self.backup_default = self.ploptions_config.getboolean("backups", "backup_default")
            self.backup_max = self.ploptions_config.getint("backups", "backup_max")
            self.backup_auto = self.ploptions_config.getboolean("backups", "backup_auto")
            self.enable_archives = self.ploptions_config.getboolean("archiver", "enable_archiver")
            self.currency = self.ploptions_config.get("bank", "currency")
            self.build_director = self.ploptions_config.get("build", "director")
            self.build_admin = self.ploptions_config.get("build", "admin")
            self.build_mod = self.ploptions_config.get("build", "mod")
            self.build_op = self.ploptions_config.get("build", "op")
            self.build_other = self.ploptions_config.get("build", "other")
            if self.backup_auto:
                reactor.callLater(float(self.backup_freq * 60),self.AutoBackup)
        except:
            logging.log(logging.ERROR, "You don't have a ploptions.conf file! You need to rename ploptions.example.conf to ploptions.conf")
            sys.exit(1)
        #if not os.path.exists("config/greeting.txt"):
        #    logging.log(logging.ERROR, "You don't have a greeting.txt file! You need to rename greeting.example.txt to greeting.txt (If this error persists, you may have used Notepad.)")
        #    sys.exit(1)
        #if not os.path.exists("config/rules.txt"):
        #    logging.log(logging.ERROR, "You don't have a rules.txt file! You need to rename rules.example.txt to rules.txt (If this error persists, you may have used Notepad.)")
        #    sys.exit(1)
        if self.use_irc:
            self.irc_nick = self.irc_config.get("irc", "nick")
            self.irc_pass = self.irc_config.get("irc", "password")
            self.irc_channel = self.irc_config.get("irc", "channel")
            self.irc_cmdlogs = self.irc_config.getboolean("irc", "cmdlogs")
            self.ircbot = self.irc_config.getboolean("irc", "ircbot")
            self.staffchat = self.irc_config.getboolean("irc", "staffchat")
            self.irc_relay = ChatBotFactory(self)
            if self.ircbot and not (self.irc_channel == "#icraft" or self.irc_channel == "#channel") and not self.irc_nick == "botname":
                reactor.connectTCP(self.irc_config.get("irc", "server"), self.irc_config.getint("irc", "port"), self.irc_relay)
            else:
                logging.log(logging.ERROR, "IRC Bot failed to connect, you could modify, rename or remove irc.conf")
                logging.log(logging.ERROR, "You need to change your 'botname' and 'channel' fields to fix this error or turn the bot off by disabling 'ircbot'")
        else:
            self.irc_relay = None
        self.default_loaded = False
        # Word Filter
        try:
            self.wordfilter.read("config/wordfilter.conf")
        except:
            logging.log(logging.ERROR, "Something is messed up with your wordfilter.conf file. (Did you edit it in Notepad?)")
            sys.exit(1)
        self.filter = []
        try:
            number = int(self.wordfilter.get("filter","count"))
        except:
            logging.log(logging.ERROR, "You need to rename wordfilter.example.conf to wordfilter.conf")
            sys.exit(1);
        for x in range(number):
            self.filter = self.filter + [[self.wordfilter.get("filter","s"+str(x)),self.wordfilter.get("filter","r"+str(x))]]
        # Salt, for the heartbeat server/verify-names
        self.salt = hashlib.md5(hashlib.md5(str(random.getrandbits(128))).digest()).hexdigest()[-32:].strip("0")
        # Load up the plugins specified
        self.plugins_config = ConfigParser()
        try:
            self.plugins_config.read("config/plugins.conf")
        except:
            logging.log(logging.ERROR, "Something is messed up with your irc.conf file. (Did you edit it in Notepad?)")
            sys.exit(1)
        try:
            plugins = self.plugins_config.options("plugins")
        except:
            print ("NOTICE: You need to rename plugins.example.conf to plugins.conf")
            sys.exit(1);
        logging.log(logging.INFO, "Loading plugins...")
        load_plugins(plugins)
        # Open the chat log, ready for appending
        self.chatlog = open("logs/server.log", "a")
        self.chatlog = open("logs/chat.log", "a")
        # Create a default world, if there isn't one.
        if not os.path.isdir("worlds/%s" % self.default_name):
            logging.log(logging.INFO, "Generating %s world..." % self.default_name)
            sx, sy, sz = 64, 64, 64
            grass_to = (sy // 2)
            world = World.create(
                "worlds/%s" % self.default_name,
                sx, sy, sz, # Size
                sx//2,grass_to+2, sz//2, 0, # Spawn
                ([BLOCK_DIRT]*(grass_to-1) + [BLOCK_GRASS] + [BLOCK_AIR]*(sy-grass_to)) # Levels
            )
            logging.log(logging.INFO, "Generated.")
        # Initialise internal datastructures
        self.worlds = {}
        self.directors = set()
        self.admins = set()
        self.mods = set()
        self.globalbuilders = set()
        self.members = set()
        self.spectators = set()
        self.silenced = set()
        self.banned = {}
        self.ipbanned = {}
        self.lastseen = {}
        # Load up the contents of those.
        self.loadMeta()
        # Set up a few more things.
        self.queue = Queue()
        self.clients = {}
        self.usernames = {}
        self.console = StdinPlugin(self)
        self.console.start()
        self.heartbeat = Heartbeat(self)
        # Boot worlds that got loaded
        for world in self.worlds:
            self.loadWorld("worlds/%s" % world, world)
        # Set up tasks to run during execution
        reactor.callLater(0.1, self.sendMessages)
        reactor.callLater(1, self.printInfo)
        # Initial startup is instant, but it updates every 10 minutes.
        self.world_save_stack = []
        reactor.callLater(60, self.saveWorlds)
        if self.enable_archives:
            self.loadPlugin('archives')
            reactor.callLater(1, self.loadArchives)
        gc.disable()
        self.cleanGarbage()

    def cleanGarbage(self):
        count = gc.collect()
        logging.log(logging.INFO, "%i garbage objects collected, %i were uncollected." % ( count, len(gc.garbage)))
        reactor.callLater(60*15, self.cleanGarbage)

    def loadMeta(self):
        "Loads the 'meta' - variables that change with the server (worlds, admins, etc.)"
        config = ConfigParser()
        config.read("config/data/ranks.meta")
        specs = ConfigParser()
        specs.read("config/data/spectators.meta")
        lastseen = ConfigParser()
        lastseen.read("config/data/lastseen.meta")
        bans = ConfigParser()
        bans.read("config/data/bans.meta")
        worlds = ConfigParser()
        worlds.read("config/data/worlds.meta")
        # Read in the admins
        if config.has_section("admins"):
            for name in config.options("admins"):
                self.admins.add(name)
        # Read in the mods
        if config.has_section("mods"):
            for name in config.options("mods"):
                self.mods.add(name)
        if config.has_section("globalbuilders"):
            for name in config.options("globalbuilders"):
                self.globalbuilders.add(name)
        if config.has_section("members"):
            for name in config.options("members"):
                self.members.add(name)
        # Read in the directors
        if config.has_section("directors"):
            for name in config.options("directors"):
                self.directors.add(name)
        if config.has_section("silenced"):
            for name in config.options("silenced"):
                self.silenced.add(name)
        # Read in the spectators (experimental)
        if specs.has_section("spectators"):
            for name in specs.options("spectators"):
                self.spectators.add(name)
        bans = ConfigParser()
        bans.read("config/data/bans.meta")
        # Read in the bans
        if bans.has_section("banned"):
            for name in bans.options("banned"):
                self.banned[name] = bans.get("banned", name)
        # Read in the ipbans
        if bans.has_section("ipbanned"):
            for ip in bans.options("ipbanned"):
                self.ipbanned[ip] = bans.get("ipbanned", ip)
        # Read in the lastseen
        if lastseen.has_section("lastseen"):
            for username in lastseen.options("lastseen"):
                self.lastseen[username] = lastseen.getfloat("lastseen", username)
        # Read in the worlds
        if worlds.has_section("worlds"):
            for name in worlds.options("worlds"):
                if name is self.default_name:
                    self.default_loaded = True
        else:
            self.worlds[self.default_name] = None
        if not self.default_loaded:
            self.worlds[self.default_name] = None

    def saveMeta(self):
        "Saves the server's meta back to a file."
        config = ConfigParser()
        specs = ConfigParser()
        lastseen = ConfigParser()
        bans = ConfigParser()
        worlds = ConfigParser()
        # Make the sections
        config.add_section("directors")
        config.add_section("admins")
        config.add_section("mods")
        config.add_section("globalbuilders")
        config.add_section("members")
        config.add_section("silenced")
        bans.add_section("banned")
        bans.add_section("ipbanned")
        specs.add_section("spectators")
        lastseen.add_section("lastseen")
        # Write out things
        for director in self.directors:
            config.set("directors", director, "true")
        for admin in self.admins:
            config.set("admins", admin, "true")
        for mod in self.mods:
            config.set("mods", mod, "true")
        for globalbuilder in self.globalbuilders:
            config.set("globalbuilders", globalbuilder, "true")
        for member in self.members:
            config.set("members", member, "true")
        for ban, reason in self.banned.items():
            bans.set("banned", ban, reason)
        for spectator in self.spectators:
            specs.set("spectators", spectator, "true")
        for silence in self.silenced:
            config.set("silenced", silence, "true")
        for ipban, reason in self.ipbanned.items():
            bans.set("ipbanned", ipban, reason)
        for username, ls in self.lastseen.items():
            lastseen.set("lastseen", username, str(ls))
        fp = open("config/data/ranks.meta", "w")
        config.write(fp)
        fp.close()
        fp = open("config/data/spectators.meta", "w")
        specs.write(fp)
        fp.close()
        fp = open("config/data/lastseen.meta", "w")
        lastseen.write(fp)
        fp.close()
        fp = open("config/data/bans.meta", "w")
        bans.write(fp)
        fp.close()
        fp = open("config/data/worlds.meta", "w")
        worlds.write(fp)
        fp.close()

    def printInfo(self):
        logging.log(logging.INFO, "There are %s users on the server" % len(self.clients))
        for key in self.worlds:
            logging.log(logging.INFO, "%s: %s" % (key, ", ".join(str(c.username) for c in self.worlds[key].clients)))
        if (time.time() - self.last_heartbeat) > 180:
            self.heartbeat = None
            self.heartbeat = Heartbeat(self)
        reactor.callLater(60, self.printInfo)

    def loadArchive(self, filename):
        "Boots an archive given a filename. Returns the new world ID."
        # Get an unused world name
        i = 1
        while self.world_exists("a-%i" % i):
            i += 1
        world_id = "a-%i" % i
        # Copy and boot
        self.newWorld(world_id, "../core/archives/%s" % filename)
        self.loadWorld("worlds/%s" % world_id, world_id)
        world = self.worlds[world_id]
        world.is_archive = True
        return world_id

    def saveWorlds(self):
        "Saves the worlds, one at a time, with a 1 second delay."
        if not self.saving:
            if not self.world_save_stack:
                self.world_save_stack = list(self.worlds)
            key = self.world_save_stack.pop()
            self.saveWorld(key)
            if not self.world_save_stack:
                reactor.callLater(60, self.saveWorlds)
                self.saveMeta()
            else:
                reactor.callLater(1, self.saveWorlds)

    def saveWorld(self, world_id,shutdown = False):
        try:
            world = self.worlds[world_id]
            world.save_meta()
            world.flush()
            logging.log(logging.INFO, "World '%s' has been saved." % world_id)
            if self.save_count == 5:
                for client in list(list(self.worlds[world_id].clients))[:]:
                    client.sendServerMessage("[%s] World '%s' has been saved." % (datetime.datetime.utcnow().strftime("%H:%M"), world_id))
                self.save_count = 1
            else:
                self.save_count += 1
            if shutdown: del self.worlds[world_id]
        except:
            logging.log(logging.INFO, "Error saving %s" % world_id)

    def claimId(self, client):
        for i in range(1, self.max_clients+1):
            if i not in self.clients:
                self.clients[i] = client
                return i
        raise ServerFull

    def releaseId(self, id):
        del self.clients[id]

    def joinWorld(self, worldid, user):
        "Makes the user join the given World."
        new_world = self.worlds[worldid]
        try:
            logging.log(logging.INFO, "%s is joining world %s" %(user.username,new_world.basename))
        except:
            logging.log(logging.INFO, "%s is joining world %s" %(user.transport.getPeer().host,new_world.basename))
        if hasattr(user, "world") and user.world:
            self.leaveWorld(user.world, user)
        user.world = new_world
        new_world.clients.add(user)
        if not worldid == self.default_name and not new_world.ASD == None:
            new_world.ASD.kill()
            new_world.ASD = None
        return new_world

    def leaveWorld(self, world, user):
        world.clients.remove(user)
        if world.autoshutdown and len(world.clients)<1:
            if world.basename == ("worlds/" + self.default_name):
                return
            else:
                if not self.asd_delay == 0:
                    world.ASD = ResettableTimer(self.asd_delay*60,1,world.unload)
                else:
                    world.ASD = ResettableTimer(30,1,world.unload)
                world.ASD.start()

    def loadWorld(self, filename, world_id):
        """
        Loads the given world file under the given world ID, or a random one.
        Returns the ID of the new world.
        """
        world = self.worlds[world_id] =  World(filename)
        world.source = filename
        world.clients = set()
        world.id = world_id
        world.factory = self
        world.start()
        logging.log(logging.INFO, "World '%s' Booted." % world_id)
        return world_id

    def unloadWorld(self, world_id,ASD=False):
        """
        Unloads the given world ID.
        """
        try:
            if ASD and len(self.worlds[world_id].clients)>0:
                self.worlds[world_id].ASD.kill()
                self.worlds[world_id].ASD = None
                return
        except KeyError:
            return
        try:
            assert world_id != self.default_name
        except:
            self.client.sendServerMessage("You can't shutdown "+self.default_name+".")
        if not self.worlds[world_id].ASD == None:
            self.worlds[world_id].ASD.kill()
            self.worlds[world_id].ASD = None
        for client in list(list(self.worlds[world_id].clients))[:]:
            client.changeToWorld(self.default_name)
            client.sendServerMessage("World '%s' has been Shutdown." % world_id)
        self.worlds[world_id].stop()
        self.saveWorld(world_id,True)
        logging.log(logging.INFO, "World '%s' Shutdown." % world_id)

    def rebootWorld(self, world_id):
        """
        Reboots a world in a crash case
        """
        for client in list(list(self.worlds[world_id].clients))[:]:
            if world_id == self.default_name:
                client.loadWorld("worlds/%s" % world_id, world_id)
                client.changeToWorld(self.default_backup)
            else:
                client.changeToWorld(self.default_name)
            client.sendServerMessage("%s has been Rebooted" % world_id)
        self.worlds[world_id].stop()
        self.worlds[world_id].flush()
        self.worlds[world_id].save_meta()
        del self.worlds[world_id]
        world = self.worlds[world_id] =  World("worlds/%s" % world_id, world_id)
        world.source = "worlds/" + world_id
        world.clients = set()
        world.id = world_id
        world.factory = self
        world.start()
        logging.log(logging.INFO, "Rebooted %s" % world_id)

    def publicWorlds(self):
        """
        Returns the IDs of all public worlds
        """
        for world_id, world in self.worlds.items():
            if not world.private:
                yield world_id

    def recordPresence(self, username):
        """
        Records a sighting of 'username' in the lastseen dict.
        """
        self.lastseen[username.lower()] = time.time()

    def unloadPlugin(self, plugin_name):
        "Reloads the plugin with the given module name."
        # Unload the plugin from everywhere
        for plugin in plugins_by_module_name(plugin_name):
            if issubclass(plugin, ProtocolPlugin):
                for client in self.clients.values():
                    client.unloadPlugin(plugin)
        # Unload it
        unload_plugin(plugin_name)

    def loadPlugin(self, plugin_name):
        # Load it
        load_plugin(plugin_name)
        # Load it back into clients etc.
        for plugin in plugins_by_module_name(plugin_name):
            if issubclass(plugin, ProtocolPlugin):
                for client in self.clients.values():
                    client.loadPlugin(plugin)

    def sendMessages(self):
        "Sends all queued messages, and lets worlds recieve theirs."
        try:
            while True:
                # Get the next task
                source_client, task, data = self.queue.get_nowait()
                try:
                    if isinstance(source_client, World):
                        world = source_client
                    elif str(source_client).startswith("<StdinPlugin"):
                        world = self.worlds[self.default_name]
                    else:
                        try:
                            world = source_client.world
                        except AttributeError:
                            logging.log(logging.WARN, "Source client for message has no world. Ignoring.")
                            continue
                    # Someone built/deleted a block
                    if task is TASK_BLOCKSET:
                        # Only run it for clients who weren't the source.
                        for client in world.clients:
                            if client is not source_client:
                                client.sendBlock(*data)
                    # Someone moved
                    elif task is TASK_PLAYERPOS:
                        # Only run it for clients who weren't the source.
                        for client in world.clients:
                            if client != source_client:
                                client.sendPlayerPos(*data)
                    # Someone moved only their direction
                    elif task is TASK_PLAYERDIR:
                        # Only run it for clients who weren't the source.
                        for client in world.clients:
                            if client != source_client:
                                client.sendPlayerDir(*data)
                    # Someone spoke!
                    elif task is TASK_MESSAGE:
                        # More Word Filter
                        id, colour, username, text = data
                        text = self.messagestrip(text)
                        data = (id,colour,username,text)
                        for client in self.clients.values():
                            client.sendMessage(*data)
                        id, colour, username, text = data
                        logging.log(logging.INFO, "%s: %s" % (username, text))
                        self.chatlog.write("[%s] %s: %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"), username, text))
                        self.chatlog.flush()
                        if self.irc_relay and world:
                            self.irc_relay.sendMessage(username, text)
                    # Someone spoke!
                    elif task is TASK_IRCMESSAGE:
                        for client in self.clients.values():
                            client.sendMessage(*data)
                        id, colour, username, text = data
                        logging.log(logging.INFO, "<%s> %s" % (username, text))
                        self.chatlog.write("[%s] <%s> %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"), username, text))
                        self.chatlog.flush()
                        if self.irc_relay and world:
                            self.irc_relay.sendMessage(username, text)
                    # Someone actioned!
                    elif task is TASK_ACTION:
                        # More Word Filter
                        id, colour, username, text = data
                        text = self.messagestrip(text)
                        data = (id,colour,username,text)
                        for client in self.clients.values():
                            client.sendAction(*data)
                        id, colour, username, text = data
                        logging.log(logging.INFO, "* %s %s" % (username, text))
                        self.chatlog.write("[%s] * %s %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"), username, text))
                        self.chatlog.flush()
                        if self.irc_relay and world:
                            self.irc_relay.sendAction(username, text)
                    # Someone connected to the server
                    elif task is TASK_PLAYERCONNECT:
                        for client in self.usernames:
                            self.usernames[client].sendNewPlayer(*data)
                            if self.username.lower() in INFO_VIPLIST and not self.isMod():
                                self.usernames[client].sendNormalMessage(COLOUR_DARKRED+"iCraft Developer spotted;")
                            self.usernames[client].sendServerMessage("%s has come online." % source_client.username)
                        if self.irc_relay and world:
                            if self.username.lower() in INFO_VIPLIST and not self.isMod():
                                self.irc_relay.sendServerMessage("04iCraft Developer spotted;")
                            self.irc_relay.sendServerMessage("07%s has come online." % source_client.username)
                    # Someone joined a world!
                    elif task is TASK_NEWPLAYER:
                        for client in world.clients:
                            if client != source_client:
                                client.sendNewPlayer(*data)
                            client.sendServerMessage("%s has joined the world." % source_client.username)
                    # Someone left!
                    elif task is TASK_PLAYERLEAVE:
                        # Only run it for clients who weren't the source.
                        for client in self.clients.values():
                            client.sendPlayerLeave(*data)
                            if not source_client.username is None:
                                client.sendServerMessage("%s has gone offline." % source_client.username)
                            else:
                                source_client.log("Pinged the server.")
                        if not source_client.username is None:
                            if self.irc_relay and world:
                                self.irc_relay.sendServerMessage("07%s has gone offline." % source_client.username)
                    # Someone changed worlds!
                    elif task is TASK_WORLDCHANGE:
                        # Only run it for clients who weren't the source.
                        for client in data[1].clients:
                            client.sendPlayerLeave(data[0])
                            client.sendServerMessage("%s joined '%s'" % (source_client.username, world.id))
                        if self.irc_relay and world:
                            self.irc_relay.sendServerMessage("07%s joined '%s'" % (source_client.username, world.id))
                        logging.log(logging.INFO, "%s has now joined '%s'" % (source_client.username, world.id))
                    elif task == TASK_STAFFMESSAGE:
                        # Give all staff the message :D
                        id, colour, username, text, IRC = data
                        message = self.messagestrip(text);
                        for user, client in self.usernames.items():
                            if self.isMod(user):
                                client.sendMessage(100, COLOUR_YELLOW+"#"+colour, username, message, False, False)
                        if self.staffchat and self.irc_relay and len(data)>3:
                            self.irc_relay.sendServerMessage("#"+username+": "+text,True,username,IRC)
                        logging.log(logging.INFO, "#"+username+": "+text)
                        self.adlog = open("logs/server.log", "a")
                        self.adlog.write("["+datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")+"] #"+username+": "+text+"\n")
                        self.adlog.flush()
                    elif task == TASK_GLOBALMESSAGE:
                        # Give all world people the message
                        id, world, message = data
                        message = self.messagestrip(message);
                        for client in world.clients:
                            client.sendNormalMessage(message)
                    elif task == TASK_WORLDMESSAGE:
                        # Give all world people the message
                        id, world, message = data
                        for client in world.clients:
                            client.sendNormalMessage(message)
                    elif task == TASK_SERVERMESSAGE:
                        # Give all people the message
                        message = data
                        message = self.messagestrip(message);
                        for client in self.clients.values():
                            client.sendNormalMessage(COLOUR_DARKBLUE + message)
                        logging.log(logging.INFO,message)
                        if self.irc_relay and world:
                            self.irc_relay.sendServerMessage(message)
                    elif task == TASK_ONMESSAGE:
                        # Give all people the message
                        message = data
                        message = self.messagestrip(message);
                        for client in self.clients.values():
                            client.sendNormalMessage(COLOUR_YELLOW + message)
                        if self.irc_relay and world:
                            self.irc_relay.sendServerMessage(message)
                    elif task == TASK_PLAYERRESPAWN:
                        # We need to immediately respawn the user to update their nick.
                        for client in world.clients:
                            if client != source_client:
                                id, username, x, y, z, h, p = data
                                client.sendPlayerLeave(id)
                                client.sendNewPlayer(id, username, x, y, z, h, p)
                    elif task == TASK_SERVERURGENTMESSAGE:
                        # Give all people the message
                        message = data
                        for client in self.clients.values():
                            client.sendNormalMessage(COLOUR_DARKRED + message)
                        logging.log(logging.INFO,message)
                        if self.irc_relay and world:
                            self.irc_relay.sendServerMessage(message)
                    elif task == TASK_AWAYMESSAGE:
                        # Give all world people the message
                        message = data
                        for client in self.clients.values():
                            client.sendNormalMessage(COLOUR_DARKPURPLE + message)
                        logging.log(logging.INFO, "AWAY - %s" %message)
                        self.chatlog.write("[%s] %s %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"), "", message))
                        self.chatlog.flush()
                        if self.irc_relay and world:
                            self.irc_relay.sendAction("", message)
                except Exception, e:
                    logging.log(logging.ERROR, traceback.format_exc())
        except Empty:
            pass
        # OK, now, for every world, let them read their queues
        for world in self.worlds.values():
            world.read_queue()
        # Come back soon!
        reactor.callLater(0.1, self.sendMessages)

    def newWorld(self, new_name, template="default"):
        "Creates a new world from some template."
        # Make the directory
        try:
            os.mkdir("worlds/%s" % new_name)
        except:
            client.sendServerMessage("Sorry, that world already exists!")
        # Find the template files, copy them to the new location
        for filename in ["blocks.gz", "world.meta"]:
            try:
                shutil.copyfile("core/templates/%s/%s" % (template, filename), "worlds/%s/%s" % (new_name, filename))
            except:
                self.client.sendServerMessage("That template doesn't exist.")

    def renameWorld(self, old_worldid, new_worldid):
        "Renames a world."
        assert old_worldid not in self.worlds
        assert self.world_exists(old_worldid)
        assert not self.world_exists(new_worldid)
        os.rename("worlds/%s" % (old_worldid), "worlds/%s" % (new_worldid))

    def numberWithPhysics(self):
        "Returns the number of worlds with physics enabled."
        return len([world for world in self.worlds.values() if world.physics])

    def isSilenced(self, username):
        return username.lower() in self.silenced

    def isOwner(self, username):
        return username.lower()==self.owner

    def isDirector(self, username):
        return username.lower() in self.directors or self.isOwner(username)

    def isAdmin(self, username):
        return username.lower() in self.admins or self.isDirector(username)

    def isMod(self, username):
        return username.lower() in self.mods or self.isAdmin(username)

    def isMember(self, username):
        #TODO: Needs to check for builder/op level also.
        return username.lower() in self.members or self.isMod(username)

    def isSpectator(self, username):
        return username.lower() in self.spectators

    def isBanned(self, username):
        return username.lower() in self.banned

    def isIpBanned(self, ip):
        return ip in self.ipbanned

    def addBan(self, username, reason):
        self.banned[username.lower()] = reason

    def removeBan(self, username):
        del self.banned[username.lower()]

    def banReason(self, username):
        return self.banned[username.lower()]

    def addIpBan(self, ip, reason):
        self.ipbanned[ip] = reason

    def removeIpBan(self, ip):
        del self.ipbanned[ip]

    def ipBanReason(self, ip):
        return self.ipbanned[ip]

    def world_exists(self, world_id):
        "Says if the world exists (even if unbooted)"
        return os.path.isdir("worlds/%s/" % world_id)

    def AutoBackup(self):
        for world in self.worlds:
            self.Backup(world)
        if self.backup_auto:
            reactor.callLater(float(self.backup_freq * 60),self.AutoBackup)

    def Backup(self, world_id):
            world_dir = ("worlds/%s/" % world_id)
            if world_id == self.default_name and not self.backup_default:
                return
            if not os.path.exists(world_dir):
                logging.log(logging.INFO, "World %s does not exist." % (world.id))
            else:
                if not os.path.exists(world_dir+"backup/"):
                    os.mkdir(world_dir+"backup/")
                folders = os.listdir(world_dir+"backup/")
                backups = list([])
                for x in folders:
                    if x.isdigit():
                        backups.append(x)
                backups.sort(lambda x, y: int(x) - int(y))
                path = os.path.join(world_dir+"backup/", "0")
                if backups:
                    path = os.path.join(world_dir+"backup/", str(int(backups[-1])+1))
                os.mkdir(path)
                shutil.copy(world_dir + "blocks.gz", path)
                shutil.copy(world_dir + "world.meta", path)
                try:
                    logging.log(logging.INFO, "%s's backup %s is saved." % (world_id, str(int(backups[-1])+1)))
                except:
                    logging.log(logging.INFO, "%s's backup 0 is saved." % (world_id))
                if len(backups)+1 > self.backup_max:
                    for i in range(0,((len(backups)+1)-self.backup_max)):
                        shutil.rmtree(os.path.join(world_dir+"backup/", str(int(backups[i]))))

    def messagestrip(factory,message):
        strippedmessage = ""
        for x in message:
            if ord(str(x)) < 128:
                strippedmessage = strippedmessage + str(x)
        message = strippedmessage
        for x in factory.filter:
            rep = re.compile(x[0], re.IGNORECASE)
            message = rep.sub(x[1], message)
        return message   
    
    def loadArchives(self):
        self.archives = {}
        for name in os.listdir("core/archives/"):
            if os.path.isdir(os.path.join("core/archives", name)):
                for subfilename in os.listdir(os.path.join("core/archives", name)):
                    match = re.match(r'^(\d\d\d\d\-\d\d\-\d\d_\d?\d\_\d\d)$', subfilename)
                    if match:
                        when = match.groups()[0]
                        try:
                            when = datetime.datetime.strptime(when, "%Y/%m/%d %H:%M:%S")
                        except ValueError, e:
                            logging.log(logging.WARN, "Bad archive filename %s" % subfilename)
                            continue
                        if name not in self.archives:
                            self.archives[name] = {}
                        self.archives[name][when] = "%s/%s" % (name, subfilename)
        logging.log(logging.INFO, "Loaded %s discrete archives." % len(self.archives))
        reactor.callLater(300, self.loadArchives)

    def makefile(self, filename):
        if not os.path.exists(filename):
            logging.log(logging.DEBUG, "Making "+filename)
            try:
                file = open(filename, "w")
                file.write("")
                file.close()
            except:
                os.mkdir(filename)

    def makedatfile(self, filename):
        if not os.path.exists(filename):
            logging.log(logging.DEBUG, "Making "+filename)
            file = open(filename, "w")
            file.write("(dp1\n.")
            file.close()

    def checkos(self):
        try:
            if (os.uname()[0] == "Darwin"):
                os = "Mac"
            else:
                os = "Linux"
        except:
            os = "Windows"
        return os
