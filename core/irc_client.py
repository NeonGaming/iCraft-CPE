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

import datetime, traceback, logging
from reqs.twisted.words.protocols import irc
from reqs.twisted.words.protocols.irc import IRC
from reqs.twisted.internet import protocol
from constants import *
from globals import *
from core.plugins import protocol_plugins
from core.decorators import *

class ChatBot(irc.IRCClient):
    """An IRC-server chat integration bot."""
    
    ocommands = [ "help", "cmdlist", "banreason", "banned", "kick", "ban", "shutdown", "rank", "derank", "spec", "boot" ]
    ncommands = [ "who", "worlds", "staff", "credits", "help", "rules", "cmdlist", "about" ]

    def connectionMade(self):
        self.ops = []
        self.nickname = self.factory.main_factory.irc_nick
        self.password = self.factory.main_factory.irc_pass
        self.prefix = "none"
        irc.IRCClient.connectionMade(self)
        self.factory.instance = self
        self.factory, self.controller_factory = self.factory.main_factory, self.factory
        self.world = None
        self.sendLine('NAMES ' + self.factory.irc_channel)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        logging.log(logging.INFO,"IRC client disconnected. (%s)" % reason)

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        logging.log(logging.INFO,"IRC client connected.")
        self.msg("NickServ", "IDENTIFY %s" % self.password)
        self.msg("ChanServ", "INVITE %s" % self.factory.irc_channel)
        self.join(self.factory.irc_channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        logging.log(logging.INFO,"IRC client joined %s." % channel)

    def sendError(self, error):
        self.log("Sending error: %s" % error)
        self.sendPacked(TYPE_ERROR, error)
        reactor.callLater(0.2, self.transport.loseConnection)

    def lineReceived(self, line): # use instead of query
        line = irc.lowDequote(line)
        try:
            prefix, command, params = irc.parsemsg(line)
            if irc.numeric_to_symbolic.has_key(command):
                command = irc.numeric_to_symbolic[command]
            self.handleCommand(command, prefix, params)
        except irc.IRCBadMessage:
            self.badMessage(line, *sys.exc_info())
        try:
            if command == "RPL_NAMREPLY":
                names = params[3].split()
                for name in names:
                    if name.startswith("@"):
                        self.ops.append(name[1:])
        except:
            logging.log(logging.ERROR, traceback.format_exc())

    def AdminCommand(self, command):
        try:
            user = command[0]
            if user in self.ops:
                if len(command) > 1:
                    if command[1].startswith("#"):
                        if self.factory.staffchat:
                            # It's an staff-only message.
                            if len(command[1]) == 1:
                                self.msg(user, "07Please include a message to send.")
                            else:
                                try:
                                    text = " ".join(command[1:])[1:]
                                except ValueError:
                                    self.factory.queue.put((self, TASK_MESSAGE, (0, COLOUR_DARKGREEN, "Console", message)))
                                else:
                                    self.factory.queue.put((self, TASK_STAFFMESSAGE, (0, COLOUR_PURPLE, command[0],text,True)))
                                    self.adlog = open("logs/server.log", "a")
                                    self.adlog = open("logs/world.log", "a")
                                    self.adlog.write(datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")+" | #" + command[0] + ": "+text+"\n")
                                    self.adlog.flush()
                    elif command[1] in self.ocommands and len(command) > 1:
                        if command[1] == ("help"):
                            self.msg(user, "07Admin Help")
                            self.msg(user, "07Commands: Use 'cmdlist'")
                            if self.factory.staffchat:
                                self.msg(user, "07StaffChat: Use '#message'")
                        elif command[1] == ("cmdlist"):
                            self.msg(user, "07Here are your Admin Commands:")
                            self.msg(user, "07ban banned banreason boot derank kick rank shutdown spec")
                            self.msg(user, "07Use 'command arguments' to do it.")
                        elif command[1] == ("banreason"):
                            if len(command) == 3:
                                username = command[2]
                                if not self.factory.isBanned(username):
                                    self.msg(user,"07%s is not Banned." % username)
                                else:
                                    self.msg(user,"07Reason: %s" % self.factory.banReason(username))
                            else:
                                self.msg(user,"07You must provide a name.")
                        elif command[1] == ("banned"):
                            self.msg(user,  ", ".join(self.factory.banned))
                        elif command[1] == ("kick"):
                            user = command[2]
                            for client in self.factory.clients.values():
                                if client.username.lower() == user.lower():
                                    client.sendError("You were kicked!")
                                    self.msg(user, "07"+str(command[2])+" has been kicked from the server.")
                                    return
                            self.msg(user, "07"+str(command[2])+" is not online.")
                        elif command[1] == ("ban"):
                            if command > 3:
                                if self.factory.isBanned(command[2]):
                                    self.msg(user,"07%s is already Banned." % command[2])
                                else:
                                    self.factory.addBan(command[2], " ".join(command[3:]))
                                    if command[2] in self.factory.usernames:
                                        self.factory.usernames[command[2]].sendError("You got banned!")
                                    self.msg(user,"07%s has been Banned for %s." % (command[2]," ".join(command[3:])))
                            else:
                                self.msg(user,"07Please give a username and reason.")
                        elif command[1] == ("shutdown"):
                            world = str(command[2]).lower()
                            if world in self.factory.worlds:
                                self.factory.unloadWorld(world)
                                self.msg(user,"07World '"+world+"' shutdown.")
                            else:
                                self.msg(user,"07World '"+world+"' is not loaded.")
                        elif command[1] == ("rank"):
                            if not command > 2:
                                self.msg(user, "07You must provide a username.")
                            else:
                                self.msg(user,Rank(self, command[1:] + [user], False, True, self.factory))
                        elif command[1] == ("derank"):
                            if not command > 2:
                                self.msg(user, "07You must provide a username.")
                            else:
                                self.msg(user,DeRank(self, command[1:] + [user], False, True, self.factory))
                        elif command[1] == ("spec"):
                            if not command > 2:
                                self.msg(user, "07You must provide a username.")
                            else:
                                self.msg(user,Spec(self, command[1], False, True, self.factory))
                        elif command[1] == ("boot"):
                            world = str(command[2]).lower()
                            self.factory.loadWorld("worlds/"+world, world)
                            self.msg(user,"07World '"+world+"' booted.")
                        else:
                            self.msg(user, "07Sorry, "+command[1]+" is not a command!")
                    else:
                        self.msg( user, "07%s is not a command!" % command[1] )
                else:
                    self.msg( user,"07You must provide a valid command to use the IRC bot." )
            else:
                if command[1].startswith("#"):
                    if self.factory.staffchat:
                        self.msg(user, "07You must be an op to use StaffChat")
                elif command[1] in self.ocommands:
                    self.msg(user, "07You must be an op to use %s." %command[1])
                else:
                    self.msg( user, "07%s is not a command!" % command[1] )
            if not command[1].startswith("#"):
                logging.log(logging.INFO, "%s just used: %s" % (user, " ".join(command[1:])))
        except:
            logging.log(logging.ERROR, traceback.format_exc())
            self.msg(user, "Internal Server Error (See the Console for more details)")

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        try:
            user = user.split('!', 1)[0]
            msg = "".join([char for char in msg if ord(char) < 128 and char != "" or "0"])
            if channel == self.nickname:
                if not ( self.nickname == user or "Serv" in user ):
                    msg_command = msg.split()
                    self.AdminCommand([user] + msg_command)
            elif channel.lower() == self.factory.irc_channel.lower():
                if msg.lstrip(self.nickname).startswith("$"+self.nickname):
                    msg_command = msg.split()
                    if len(msg_command) > 1:
                        if msg_command[1] in self.ncommands and len(msg_command) > 1:
                            if msg_command[1] == ("who"):
                                self.msg(self.factory.irc_channel, "07Who's Online?")
                                none=True
                                for key in self.factory.worlds:
                                    users =  ", ".join(str(c.username) for c in self.factory.worlds[key].clients)
                                    if users:
                                        whois = ("07%s: %s" % (key, users))
                                        self.msg(self.factory.irc_channel, whois)
                                        users=None
                                        none=False
                                if none:
                                    self.msg(self.factory.irc_channel, "07No users are online.")
                            elif msg_command[1] == ("worlds"):
                                self.msg(self.factory.irc_channel, "07Worlds Booted")
                                worlds = ", ".join([id for id, world in self.factory.worlds.items()])
                                self.msg(self.factory.irc_channel, "07Online Worlds: "+worlds)
                            elif msg_command[1] == ("staff"):
                                self.msg(self.factory.irc_channel,"07Please see your PM for the Staff List.")
                                self.msg(user, "The Server Staff - Owner: "+self.factory.owner)
                                list = Staff(self, self.factory)
                                for each in list:
                                    self.msg(user," ".join(each))
                            elif msg_command[1] == ("credits"):
                                self.msg(self.factory.irc_channel,"07Please see your PM for the Credits.")
                                self.msg(user, "The Credits")
                                list = Credits(self, self.factory)
                                for each in list:
                                    self.msg(user,"".join(each))
                            elif msg_command[1] == ("help"):
                                self.msg(self.factory.irc_channel, "07Help Center")
                                self.msg(self.factory.irc_channel, "07Commands: Use '$"+self.nickname+" cmdlist'")
                                self.msg(self.factory.irc_channel, "07WorldChat: Use '!world message'")
                                self.msg(self.factory.irc_channel, "07IRCChat: Use '$message'")
                                self.msg(self.factory.irc_channel, "07About: Use '$"+self.nickname+" about'")
                                self.msg(self.factory.irc_channel, "07Credits: Use '$"+self.nickname+" credits'")
                            elif msg_command[1] == ("rules"):
                                self.msg(self.factory.irc_channel,"07Please see your PM for the Rules.")
                                self.msg(user, "The Rules")
                                try:
                                    r = open('config/rules.txt', 'r')
                                except:
                                    r = open('config/rules.example.txt', 'r')
                                for line in r:
                                    line = line.replace("\n", "")
                                    self.msg(user, line)
                            elif msg_command[1] == ("cmdlist"):
                                self.msg(self.factory.irc_channel, "07Command List")
                                self.msg(self.factory.irc_channel, "07about cmdlist credits help rules staff who worlds")
                                self.msg(self.factory.irc_channel, "07Use '$"+self.nickname+" command arguments' to do it.")
                                self.msg(self.factory.irc_channel, "07NOTE: Admin Commands are by PMing "+self.nickname+" - only for ops.")
                            elif msg_command[1] == ("about"):
                                self.msg(self.factory.irc_channel, "07About the Server, powered by iCraft; http://hlmc.net/ | Credits: Use '$%s credits'" % (self.nickname))
                                self.msg(self.factory.irc_channel, "07Name: "+self.factory.server_name+"; owned by "+self.factory.owner)
                                try:
                                    self.msg(self.factory.irc_channel, "07URL: "+self.factory.heartbeat.url)
                                except:
                                    self.msg(self.factory.irc_channel, "07URL: N/A (minecraft.net is offline)")
                                self.msg(self.factory.irc_channel, "07Site: "+self.factory.info_url)
                            else:
                                self.msg(self.factory.irc_channel, "07Sorry, "+msg_command[1]+" is not a command!")
                            logging.log(logging.INFO, "%s just used: %s" % (user, " ".join(msg_command[1:])))
                        elif msg_command[1] in self.ocommands and len(msg_command) > 1:
                            if user in self.ops:
                                self.msg(self.factory.irc_channel, "07Please do not use %s in the channel; use a query instead!" % msg_command[1])
                            else:
                                self.msg(self.factory.irc_channel, "07You must be an op to use %s." % msg_command[1]) 
                        else:
                            self.msg(self.factory.irc_channel,"07You must provide a valid command to use the IRC bot - try the help command.")
                    else:
                        self.msg(self.factory.irc_channel,"07You must provide a valid command to use the IRC bot - try the help command.")
                elif msg.startswith("$"):
                    logging.log(logging.INFO, "<$%s> %s" % (user, msg))
                elif msg.startswith("!"):
                    # It's a world message.
                    message = msg.split(" ")
                    if len(message) == 1:
                        self.msg(self.factory.irc_channel, "07Please include a message to send.")
                    else:
                        try:
                           world = message[0][1:len(message[0])]
                           out = "\n ".join(message[1:])
                           text = COLOUR_PURPLE+"IRC: "+COLOUR_WHITE+"<!"+user+">"+COLOUR_WHITE+out
                        except ValueError:
                            self.msg(self.factory.irc_channel, "07Please include a message to send.")
                        else:
                            if world in self.factory.worlds:
                                self.factory.queue.put ((self.factory.worlds[world], TASK_WORLDMESSAGE, (255, self.factory.worlds[world], text),))
                                logging.log(logging.INFO,"WORLD - "+user+" in "+str(self.factory.worlds[world].id)+": "+out)
                                self.wclog = open("logs/server.log", "a")
                                self.wclog.write(datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")+" | !"+user+" in "+str(self.factory.worlds[world].id)+": "+out+"\n")
                                self.wclog.flush()
                                self.wclog.close()
                            else:
                                self.msg(self.factory.irc_channel, "07That world does not exist. Try !world message")
                elif self.prefix == "none":
                    allowed = True
                    goodchars = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", " ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", " ", "!", "@", "#", "$", "%", "*", "(", ")", "-", "_", "+", "=", "{", "[", "}", "]", ":", ";", "\"", "\'", "<", ",", ">", ".", "?", "/", "\\", "|"]
                    for character in msg:
                        if not character.lower() in goodchars:
                            msg = msg.replace("&0", "&0")
                            msg = msg.replace("&1", "&1")
                            msg = msg.replace("&2", "&2")
                            msg = msg.replace("&3", "&3")
                            msg = msg.replace("&4", "&4")
                            msg = msg.replace("&5", "&5")
                            msg = msg.replace("&6", "&6")
                            msg = msg.replace("&7", "&7")
                            msg = msg.replace("&8", "&8")
                            msg = msg.replace("&9", "&9")
                            msg = msg.replace("&a", "&a")
                            msg = msg.replace("&b", "&b")
                            msg = msg.replace("&c", "&c")
                            msg = msg.replace("&d", "&d")
                            msg = msg.replace("&e", "&e")
                            msg = msg.replace("&f", "&f")
                            msg = msg.replace("0", "&f")
                            msg = msg.replace("00", "&f")
                            msg = msg.replace("1", "&0")
                            msg = msg.replace("01", "&0")
                            msg = msg.replace("2", "&1")
                            msg = msg.replace("02", "&1")
                            msg = msg.replace("3", "&2")
                            msg = msg.replace("03", "&2")
                            msg = msg.replace("4", "&c")
                            msg = msg.replace("04", "&c")
                            msg = msg.replace("5", "&4")
                            msg = msg.replace("05", "&4")
                            msg = msg.replace("6", "&5")
                            msg = msg.replace("06", "&5")
                            msg = msg.replace("7", "&6")
                            msg = msg.replace("07", "&6")
                            msg = msg.replace("8", "&e")
                            msg = msg.replace("08", "&e")
                            msg = msg.replace("9", "&a")
                            msg = msg.replace("09", "&a")
                            msg = msg.replace("10", "&3")
                            msg = msg.replace("11", "&b")
                            msg = msg.replace("12", "&9")
                            msg = msg.replace("13", "&d")
                            msg = msg.replace("14", "&8")
                            msg = msg.replace("15", "&7")
                            msg = msg.replace(character, "*")
                    msg = msg.replace("%0", "&0")
                    msg = msg.replace("%1", "&1")
                    msg = msg.replace("%2", "&2")
                    msg = msg.replace("%3", "&3")
                    msg = msg.replace("%4", "&4")
                    msg = msg.replace("%5", "&5")
                    msg = msg.replace("%6", "&6")
                    msg = msg.replace("%7", "&7")
                    msg = msg.replace("%8", "&8")
                    msg = msg.replace("%9", "&9")
                    msg = msg.replace("%a", "&a")
                    msg = msg.replace("%b", "&b")
                    msg = msg.replace("%c", "&c")
                    msg = msg.replace("%d", "&d")
                    msg = msg.replace("%e", "&e")
                    msg = msg.replace("%f", "&f")
                    msg = msg.replace("./", " /")
                    msg = msg.replace(".!", " !")
                    if msg[len(msg)-2] == "&":
                        self.msg(self.factory.irc_channel, "07You can not use a color at the end of a message")
                        return
                    if len(msg) > 51:
                        moddedmsg = msg[:51].replace(" ", "")
                        if moddedmsg[len(moddedmsg)-2] == "&":
                            msg = msg.replace("&", "*")
                    #self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, user, msg)))
                    for client in self.factory.clients.values():
                        client.sendNormalMessage(COLOUR_PURPLE+"IRC: "+COLOUR_WHITE+"<"+user+">")
                        client.sendNormalMessage(msg)
                    logging.log(logging.INFO, "<%s> %s" % (user, msg))
                    self.factory.chatlog.write("[%s] <*%s> %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M"), user, msg))
                    self.factory.chatlog.flush()
        except:
            logging.log(logging.ERROR, traceback.format_exc())
            self.msg(self.factory.irc_channel, "Internal Server Error (See the Console for more details)")

    def action(self, user, channel, msg):
        msg = msg.replace("./", " /")
        msg = msg.replace(".!", " !")
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        msg = "".join([char for char in msg if ord(char) < 128 and char != "" or "0"])
        #self.factory.queue.put((self, TASK_ACTION, (127, COLOUR_PURPLE, user, msg)))
        for client in self.factory.clients.values():
            client.sendNormalMessage(COLOUR_PURPLE+"IRC: "+COLOUR_YELLOW+"* "+COLOUR_WHITE+user)
            client.sendNormalMessage(msg)
        logging.log(logging.INFO, "* %s %s" % (user, msg))
        self.factory.chatlog.write("[%s] * %s %s\n" % (datetime.datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S"), user, msg))
        self.factory.chatlog.flush()

    def sendMessage(self, username, message):
        message = message.replace("&0", "01")
        message = message.replace("&1", "02")
        message = message.replace("&2", "03")
        message = message.replace("&3", "10")
        message = message.replace("&4", "05")
        message = message.replace("&5", "06")
        message = message.replace("&6", "07")
        message = message.replace("&7", "15")
        message = message.replace("&8", "14")
        message = message.replace("&9", "12")
        message = message.replace("&a", "09")
        message = message.replace("&b", "11")
        message = message.replace("&c", "04")
        message = message.replace("&d", "13")
        message = message.replace("&e", "08")
        message = message.replace("&f", "00")
        username = username.replace("&0", "")
        username = username.replace("&1", "")
        username = username.replace("&2", "")
        username = username.replace("&3", "")
        username = username.replace("&4", "")
        username = username.replace("&5", "")
        username = username.replace("&6", "")
        username = username.replace("&7", "")
        username = username.replace("&8", "")
        username = username.replace("&9", "")
        username = username.replace("&a", "")
        username = username.replace("&b", "")
        username = username.replace("&c", "")
        username = username.replace("&d", "")
        username = username.replace("&e", "")
        username = username.replace("&f", "")
        self.msg(self.factory.irc_channel, "%s: %s" % (username, message))

    def sendServerMessage(self, message,admin=False,user="",IRC=False):
        message = message.replace("./", " /")
        message = message.replace(".!", " !")
        message = message.replace("&0", "01")
        message = message.replace("&1", "02")
        message = message.replace("&2", "03")
        message = message.replace("&3", "10")
        message = message.replace("&4", "05")
        message = message.replace("&5", "06")
        message = message.replace("&6", "07")
        message = message.replace("&7", "15")
        message = message.replace("&8", "14")
        message = message.replace("&9", "12")
        message = message.replace("&a", "09")
        message = message.replace("&b", "11")
        message = message.replace("&c", "04")
        message = message.replace("&d", "13")
        message = message.replace("&e", "08")
        message = message.replace("&f", "00")
        if admin:
            for op in self.ops:
                if not op == user or not IRC:
                    self.msg(op, "%s" % message)
        else:
            self.msg(self.factory.irc_channel, "%s" % message)

    def sendAction(self, username, message):
        message = message.replace("&0", "01")
        message = message.replace("&1", "02")
        message = message.replace("&2", "03")
        message = message.replace("&3", "10")
        message = message.replace("&4", "05")
        message = message.replace("&5", "06")
        message = message.replace("&6", "07")
        message = message.replace("&7", "15")
        message = message.replace("&8", "14")
        message = message.replace("&9", "12")
        message = message.replace("&a", "09")
        message = message.replace("&b", "11")
        message = message.replace("&c", "04")
        message = message.replace("&d", "13")
        message = message.replace("&e", "08")
        message = message.replace("&f", "00")
        self.msg(self.factory.irc_channel, "* %s %s" % (username, message))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        "Called when an IRC user changes their nickname."
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        if old_nick in self.ops:
            self.ops.remove(old_nick)
            self.ops.append(new_nick)
        msg = "%s%s is now known as %s" % (COLOUR_YELLOW, old_nick, new_nick)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))


    def userKicked(self, kickee, channel, kicker, message):
        "Called when I observe someone else being kicked from a channel."
        if kickee in self.ops:
            self.ops.remove(kickee)
        msg = "%s%s was kicked from %s by %s" % (COLOUR_YELLOW, kickee, channel, kicker)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
        if not kickee == message:
            msg = "%sReason: %s" % (COLOUR_YELLOW, message)
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))


    def userLeft(self, user, channel):
        "Called when I see another user leaving a channel."
        if user in self.ops:
            self.ops.remove(user)
        msg = "%s%s has left %s" % (COLOUR_YELLOW, user.split("!")[0], channel)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))

    def userJoined(self, user, channel):
        "Called when I see another user joining a channel."
        if user in self.ops:
            self.ops.remove(user)
        msg = "%s%s has joined %s" % (COLOUR_YELLOW, user.split("!")[0], channel)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))

    def modeChanged(self, user, channel, set, modes, args):
        "Called when someone changes a mode."
        setUser = user.split("!")[0]
        arguments = []
        for element in args:
            if element:
                arguments.append(element.split("!")[0])
        if set and modes.startswith("o"):
            if len(arguments) < 2:
                msg = "%s%s was opped on %s by %s" % (COLOUR_YELLOW, arguments[0], channel, setUser)
            else:
                msg = "%sUsers opped on %s by %s: %s (%s)" % (COLOUR_YELLOW, channel, setUser, ", ".join(arguments), len(arguments))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            for name in args:
                if not name in self.ops:
                    self.ops.append(name)
        elif not set and modes.startswith("o"):
            done = []
            for name in args:
                done.append(name.split("!")[0])
            if len(arguments) < 2:
                msg = "%s%s was deopped on %s by %s" % (COLOUR_YELLOW, arguments[0], channel, setUser)
            else:
                msg = "%sUsers deopped on %s by %s: %s (%s)" % (COLOUR_YELLOW, channel, setUser, ", ".join(arguments), len(arguments))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            for name in args:
                if name in self.ops:
                    self.ops.remove(name)
        elif set and modes.startswith("v"):
            if len(arguments) < 2:
                msg = "%s%s was voiced on %s by %s" % (COLOUR_YELLOW, arguments[0], channel, setUser)
            else:
                msg = "%sUsers voiced on %s by %s: %s (%s)" % (COLOUR_YELLOW, channel, setUser, ", ".join(arguments), len(arguments))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            for name in args:
                if not name in self.ops:
                    self.ops.append(name)
        elif not set and modes.startswith("v"):
            done = []
            for name in args:
                done.append(name.split("!")[0])
            if len(arguments) < 2:
                msg = "%s%s was devoiced on %s by %s" % (COLOUR_YELLOW, arguments[0], channel, setUser)
            else:
                msg = "%sUsers devoiced on %s by %s: %s (%s)" % (COLOUR_YELLOW, channel, setUser, ", ".join(arguments), len(arguments))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            for name in args:
                if name in self.ops:
                    self.ops.remove(name)
        elif set and modes.startswith("b"):
            msg = "%sBan set in %s by %s" % (COLOUR_YELLOW, channel, setUser)
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            msg = "%s(%s)" % (COLOUR_YELLOW, " ".join(args))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
        elif not set and modes.startswith("b"):
            msg = "%sBan lifted in %s by %s" % (COLOUR_YELLOW, channel, setUser)
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
            msg = "%s(%s)" % (COLOUR_YELLOW, " ".join(args))
            self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))
    
    def irc_QUIT(self, user, params):
        userhost = user
        user = user.split('!')[0]
        quitMessage = params[0]
        if userhost in self.ops:
            self.ops.remove(userhost)
        msg = "%s%s has quit IRC." % (COLOUR_YELLOW, user)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))

        allowed = True
        goodchars = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", " ", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", " ", "!", "@", "#", "$", "%", "*", "(", ")", "-", "_", "+", "=", "{", "[", "}", "]", ":", ";", "\"", "\'", "<", ",", ">", ".", "?", "/", "\\", "|"]
        for character in msg:
            if not character.lower() in goodchars:
                msg = msg.replace("&0", "&0")
                msg = msg.replace("&1", "&1")
                msg = msg.replace("&2", "&2")
                msg = msg.replace("&3", "&3")
                msg = msg.replace("&4", "&4")
                msg = msg.replace("&5", "&5")
                msg = msg.replace("&6", "&6")
                msg = msg.replace("&7", "&7")
                msg = msg.replace("&8", "&8")
                msg = msg.replace("&9", "&9")
                msg = msg.replace("&a", "&a")
                msg = msg.replace("&b", "&b")
                msg = msg.replace("&c", "&c")
                msg = msg.replace("&d", "&d")
                msg = msg.replace("&e", "&e")
                msg = msg.replace("&f", "&f")
                msg = msg.replace("0", "&f")
                msg = msg.replace("00", "&f")
                msg = msg.replace("1", "&0")
                msg = msg.replace("01", "&0")
                msg = msg.replace("2", "&1")
                msg = msg.replace("02", "&1")
                msg = msg.replace("3", "&2")
                msg = msg.replace("03", "&2")
                msg = msg.replace("4", "&c")
                msg = msg.replace("04", "&c")
                msg = msg.replace("5", "&4")
                msg = msg.replace("05", "&4")
                msg = msg.replace("6", "&5")
                msg = msg.replace("06", "&5")
                msg = msg.replace("7", "&6")
                msg = msg.replace("07", "&6")
                msg = msg.replace("8", "&e")
                msg = msg.replace("08", "&e")
                msg = msg.replace("9", "&a")
                msg = msg.replace("09", "&a")
                msg = msg.replace("10", "&3")
                msg = msg.replace("11", "&b")
                msg = msg.replace("12", "&9")
                msg = msg.replace("13", "&d")
                msg = msg.replace("14", "&8")
                msg = msg.replace("15", "&7")
                msg = msg.replace(character, "*")
        msg = msg.replace("%0", "&0")
        msg = msg.replace("%1", "&1")
        msg = msg.replace("%2", "&2")
        msg = msg.replace("%3", "&3")
        msg = msg.replace("%4", "&4")
        msg = msg.replace("%5", "&5")
        msg = msg.replace("%6", "&6")
        msg = msg.replace("%7", "&7")
        msg = msg.replace("%8", "&8")
        msg = msg.replace("%9", "&9")
        msg = msg.replace("%a", "&a")
        msg = msg.replace("%b", "&b")
        msg = msg.replace("%c", "&c")
        msg = msg.replace("%d", "&d")
        msg = msg.replace("%e", "&e")
        msg = msg.replace("%f", "&f")
        msg = msg.replace("./", " /")
        msg = msg.replace(".!", " !")
        if msg[len(msg)-2] == "&":
            return
        if len(msg) > 51:
            moddedmsg = msg[:51].replace(" ", "")
            if moddedmsg[len(moddedmsg)-2] == "&":
                msg = msg.replace("&", "*")
        msg = "%s(%s%s)" % (COLOUR_YELLOW, quitMessage, COLOUR_YELLOW)
        self.factory.queue.put((self, TASK_IRCMESSAGE, (127, COLOUR_PURPLE, "IRC", msg)))

class ChatBotFactory(protocol.ClientFactory):
    # the class of the protocol to build when new connection is made
    protocol = ChatBot
    rebootFlag = 0

    def __init__(self, main_factory):
        self.main_factory = main_factory
        self.instance = None
        self.rebootFlag = 1
    
    def quit(self, msg):
        self.rebootFlag = 0
        self.instance.sendLine("QUIT :" + msg)

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        self.instance = None
        if(self.rebootFlag):
            connector.connect()

    def clientConnectionFailed(self, connector, reason):
        logging.log(logging.WARN,"IRC connection failed: %s" % reason)
        self.instance = None

    def sendMessage(self, username, message):
        if self.instance:
            message = message.replace("&0", "01")
            message = message.replace("&1", "02")
            message = message.replace("&2", "03")
            message = message.replace("&3", "10")
            message = message.replace("&4", "05")
            message = message.replace("&5", "06")
            message = message.replace("&6", "07")
            message = message.replace("&7", "15")
            message = message.replace("&8", "14")
            message = message.replace("&9", "12")
            message = message.replace("&a", "09")
            message = message.replace("&b", "11")
            message = message.replace("&c", "04")
            message = message.replace("&d", "13")
            message = message.replace("&e", "08")
            message = message.replace("&f", "00")
            message = message.replace("./", " /")
            message = message.replace(".!", " !")
            message = message.replace(".@", " @")
            message = message.replace(".#", " #")
            self.instance.sendMessage(username, message)

    def sendAction(self, username, message):
        if self.instance:
            message = message.replace("&0", "01")
            message = message.replace("&1", "02")
            message = message.replace("&2", "03")
            message = message.replace("&3", "10")
            message = message.replace("&4", "05")
            message = message.replace("&5", "06")
            message = message.replace("&6", "07")
            message = message.replace("&7", "15")
            message = message.replace("&8", "14")
            message = message.replace("&9", "12")
            message = message.replace("&a", "09")
            message = message.replace("&b", "11")
            message = message.replace("&c", "04")
            message = message.replace("&d", "13")
            message = message.replace("&e", "08")
            message = message.replace("&f", "00")
            message = message.replace("./", " /")
            message = message.replace(".!", " !")
            message = message.replace(".@", " @")
            message = message.replace(".#", " #")
            self.instance.sendAction(username, message)

    def sendServerMessage(self, message,admin=False,user="",IRC=False):
        if self.instance:
            message = message.replace("&0", "01")
            message = message.replace("&1", "02")
            message = message.replace("&2", "03")
            message = message.replace("&3", "10")
            message = message.replace("&4", "05")
            message = message.replace("&5", "06")
            message = message.replace("&6", "07")
            message = message.replace("&7", "15")
            message = message.replace("&8", "14")
            message = message.replace("&9", "12")
            message = message.replace("&a", "09")
            message = message.replace("&b", "11")
            message = message.replace("&c", "04")
            message = message.replace("&d", "13")
            message = message.replace("&e", "08")
            message = message.replace("&f", "00")
            message = message.replace("./", " /")
            message = message.replace(".!", " !")
            message = message.replace(".@", " @")
            message = message.replace(".#", " #")
            self.instance.sendServerMessage(message,admin,user,IRC)
