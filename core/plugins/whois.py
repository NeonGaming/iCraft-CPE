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

import cPickle, logging, time
from core.plugins import ProtocolPlugin
from core.decorators import *
from core.constants import *
from core.globals import *

class PlayersPlugin(ProtocolPlugin):
    
    commands = {
        "who": "commandWho",
        "whois": "commandWho",
        "players": "commandWho",
        "pinfo": "commandWho",
        "locate": "commandLocate",
        "find": "commandLocate",
        "lastseen": "commandLastseen",
    }

    @only_username_command
    def commandLastseen(self, username, byuser, overriderank):
        "/lastseen username - Guest\nTells you when 'username' was last seen."
        if username not in self.client.factory.lastseen:
            self.client.sendServerMessage("There are no records of %s." % username)
        else:
            t = time.time() - self.client.factory.lastseen[username]
            days = t // 86400
            hours = (t % 86400) // 3600
            mins = (t % 3600) // 60
            desc = "%id, %ih, %im" % (days, hours, mins)
            self.client.sendServerMessage("%s was last seen %s ago." % (username, desc))

    @username_command
    def commandLocate(self, user, byuser, overriderank):
        "/locate username - Guest\nAliases: find\nTells you what world a user is in."
        self.client.sendServerMessage("%s is in %s" % (user.username, user.world.id))

    @player_list
    def commandWho(self, parts, byuser, overriderank):
        "/who [username] - Guest\nAliases: pinfo, users, whois\nOnline users, or user lookup."
        if len(parts) < 2:
            self.client.sendServerMessage("Do '/who username' for more info.")
            self.client.sendServerList(["Users:"] + list(self.client.factory.usernames))
        else:
            def loadBank():
                file = open('config/data/balances.dat', 'r')
                bank_dic = cPickle.load(file)
                file.close()
                return bank_dic
            def loadRank():
                file = open('config/data/titles.dat', 'r')
                rank_dic = cPickle.load(file)
                file.close()
                return rank_dic
            bank = loadBank()
            rank = loadRank()
            user = parts[1].lower()
            try:
                title = self.client.factory.usernames[user].title
            except:
                title = ""
            if parts[1].lower() in self.client.factory.usernames:
                # Parts is an array, always, so we get the first item.
                username = self.client.factory.usernames[parts[1].lower()]
                if self.client.isAdmin():
                    self.client.sendNormalMessage(self.client.factory.usernames[user].userColour()+("%s" % (title))+parts[1]+COLOUR_YELLOW+" "+username.world.id+" | "+str(username.transport.getPeer().host))
                else:
                    self.client.sendNormalMessage(self.client.factory.usernames[user].userColour()+("%s" % (title))+parts[1]+COLOUR_YELLOW+" "+username.world.id)
                if user in INFO_VIPLIST:
                    self.client.sendServerMessage("is an iCraft Developer")
                elif user in INFO_VIPLIST and username.gone == 1:
                    self.client.sendServerMessage("is an iCraft Developer; "+COLOUR_DARKPURPLE+"is currently Away")
                elif username.gone == 1:
                    self.client.sendNormalMessage(COLOUR_DARKPURPLE+"is currently Away")
                if user in bank:
                    self.client.sendServerMessage("Balance: M%d" % (bank[user]))
            else:
                # Parts is an array, always, so we get the first item.
                username = parts[1].lower()
                self.client.sendNormalMessage(self.client.userColour()+("%s" % (title))+parts[1]+COLOUR_DARKRED+" Offline")
                try:
                    t = time.time() - self.client.factory.lastseen[username]
                except:
                    return
                days = t // 86400
                hours = (t % 86400) // 3600
                mins = (t % 3600) // 60
                desc = "%id, %ih, %im" % (days, hours, mins)
                if username in self.client.factory.lastseen and user in bank:
                    self.client.sendServerMessage("Balance: M%s, on %s ago" % (bank[user], desc))
                elif username in self.client.factory.lastseen:
                    self.client.sendServerMessage("on %s ago" % (desc))
