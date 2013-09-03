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

import random
from core.plugins import ProtocolPlugin
from core.decorators import *
from core.constants import *

class MessagingPlugin(ProtocolPlugin):
    
    commands = {
        "say": "commandSay",
        "msg": "commandSay",
        "me": "commandMe",
        "srb": "commandSRB",
        "srs": "commandSRS",
        "u": "commandUrgent",
        "urgent": "commandUrgent",
        "away": "commandAway",
        "afk": "commandAway",
        "brb": "commandAway",
        "back": "commandBack",
        "slap": "commandSlap",
        "kill": "commandKill",
    }

    @player_list
    def commandBack(self, parts, byuser, overriderank):
        "/back - Guest\nPrints out message of you coming back."
        if byuser:
            if len(parts) != 1:
                self.client.sendServerMessage("This command doesn't need arguments")
            else:
                if self.client.isSilenced():
                    self.client.sendServerMessage("Cat got your tongue?")
                else:
                    self.client.factory.queue.put((self.client, TASK_AWAYMESSAGE, self.client.username + " is now: Back."))
                self.client.gone = 0
                self.client.resetIdleTimer()
    
    @player_list
    def commandAway(self, parts, byuser, overriderank):
        "/away reason - Guest\nAliases: afk, brb\nPrints out message of you going away."
        if byuser:
            if len(parts) == 1:
                if self.client.isSilenced():
                    self.client.sendServerMessage("Cat got your tongue?")
                else:
                    self.client.factory.queue.put((self.client, TASK_AWAYMESSAGE, self.client.username + " has gone: Away."))
            else:
                if self.client.isSilenced():
                    self.client.sendServerMessage("Cat got your tongue?")
                else:
                    self.client.factory.queue.put((self.client, TASK_AWAYMESSAGE, self.client.username + " has gone: Away "+(" ".join(parts[1:]))))
            self.client.gone = 1
            self.client.resetIdleTimer()

    @player_list
    def commandMe(self, parts, byuser, overriderank):
        "/me action - Guest\nPrints 'username action'"
        if byuser:
            if len(parts) == 1:
                self.client.sendServerMessage("Please type an action.")
            else:
                if self.client.isSilenced():
                    self.client.sendServerMessage("Cat got your tongue?")
                else:
                    self.client.factory.queue.put((self.client, TASK_ACTION, (self.client.id, self.client.userColour(), self.client.username, " ".join(parts[1:]))))
    
    @mod_only
    def commandSay(self, parts, byuser, overriderank):
        "/say message - Mod\nAliases: msg\nPrints out message in the server color."
        if len(parts) == 1:
            self.client.sendServerMessage("Please type a message.")
        else:
            self.client.factory.queue.put((self.client, TASK_SERVERMESSAGE, ("[MSG] "+(" ".join(parts[1:])))))
    
    @director_only
    def commandSRB(self, parts, byuser, overriderank):
        "/srb [reason] - Director\nPrints out a reboot message."
        if len(parts) == 1:
            self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, ("[Server Reboot] Be back in a few.")))
        else:
            self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, ("[Server Reboot] Be back in a few: "+(" ".join(parts[1:])))))

    @director_only
    def commandSRS(self, parts, byuser, overriderank):
        "/srs [reason] - Director\nPrints out a shutdown message."
        if len(parts) == 1:
            self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, ("[Server Shutdown] See you later.")))
        else:
            self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, ("[Server Shutdown] See you later: "+(" ".join(parts[1:])))))

    @admin_only
    def commandUrgent(self, parts, byuser, overriderank):
        "/u message - Admin\nAliases: urgent\nPrints out message in the server color."
        if len(parts) == 1:
            self.client.sendServerMessage("Please type a message.")
        else:
            self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, "[Urgent] "+(" ".join(parts[1:]))))

    @player_list
    def commandSlap(self, parts, byuser, overriderank):
        "/slap username [with object] - Guest\nSlaps the user with a smelly trout."
        if len(parts) == 1:
            self.client.sendServerMessage("Enter the name for who you want to slap.")
            self.client.sendWorldMessage("* "+COLOUR_PURPLE+"%s slaps %s with a giant smelly trout!" % (self.client.username, parts[2]))
            if self.client.factory.irc_relay:
                self.client.factory.irc_relay.sendServerMessage("* %s slaps %s with a giant smelly trout!" % (self.client.username, parts[2]))

    @mod_only
    @only_username_command
    def commandKill(self, username, byuser, overriderank, params=[]):
        "/kill username [reason] - Mod\nKills the user for reason (optional)"        
        killer = self.client.username                           
        if username in INFO_VIPLIST:
           self.client.sendServerMessage("You can't kill awesome people, sorry.")
        else:
            if username in self.client.factory.usernames:
                if killer.lower() == username:
                    self.client.factory.usernames[username].sendServerMessage("You can't do suicide, sorry.")
                    return
                self.client.factory.usernames[username].teleportTo(self.client.factory.usernames[username].world.spawn[0], self.client.factory.usernames[username].world.spawn[1], self.client.factory.usernames[username].world.spawn[2], self.client.factory.usernames[username].world.spawn[3])
                self.client.factory.usernames[username].sendServerMessage("You have been killed by %s." % self.client.username)
                self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, username +" has been killed by " + killer))
                if params:
                    self.client.factory.queue.put((self.client, TASK_SERVERURGENTMESSAGE, "Reason: "+(" ".join(params))))
            else:
                self.client.sendServerMessage("%s is not on the server." % username)
