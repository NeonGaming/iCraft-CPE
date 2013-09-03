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

def Rank(self, parts, byuser, overriderank,server=None):
    username = parts[2].lower()
    if server:
        factory = server
    else:
        factory = self.client.factory
    if parts[1] == "builder":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if not overriderank:
                if not (self.client.username.lower() in world.ops or self.client.isMod() or self.client.isWorldOwner()):
                    return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not ((parts[-1]) in world.ops) and not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        world.writers.add(username)
        if username in factory.usernames:
            user = factory.usernames[username]
            if user.world == world:
                user.sendBuilderUpdate()
        return ("%s is now a Builder" % username)
    elif parts[1] == "op":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if not overriderank:
                if self.client.isWorldOwner()==False:
                    return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        world.ops.add(username)
        return ("Opped %s" % username)
    elif parts[1] == "worldowner":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if self.client.isWorldOwner()==False and not overriderank:
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                return ("You are not high enough rank!")
        self.client.world.owner = (username)
        return ("%s is now a World Owner." % username)
    elif parts[1] == "member":
        if not server:
            if not self.client.isMod():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        factory.members.add(username)
        if username in factory.usernames:
            factory.usernames[username].sendMemberUpdate()
        return ("%s is now a Member." % username)
    elif parts[1] == "globalbuilder":
        if not server:
            if not self.client.isMod():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        factory.globalbuilders.add(username)
        if username in factory.usernames:
            factory.usernames[username].sendGlobalBuilderUpdate()
        return ("%s is now a Global Builder." % username)
    elif parts[1] == "mod":
        if not server:
            if not self.client.isDirector():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isDirector(parts[-1]):
                    return ("You are not high enough rank!")
        factory.mods.add(username)
        if username in factory.usernames:
            factory.usernames[username].sendModUpdate()
        return ("%s is now a Mod." % username)
    elif parts[1] == "admin":
        if not server:
            if not self.client.isDirector():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isDirector(parts[-1]):
                    return ("You are not high enough rank!")
        factory.admins.add(username)
        if username in factory.usernames:
            factory.usernames[username].sendAdminUpdate()
        return ("%s is now an admin." % username)
    elif parts[1] == "director":
        if not server:
            if not self.client.isOwner():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isOwner(parts[-1]):
                    return ("You are not high enough rank!")
        factory.directors.add(username)
        if username in factory.usernames:
            factory.usernames[username].sendDirectorUpdate()
        return ("%s is now an director." % username)
    else:
        return ("Unknown rank \"%s\""%parts[1])

def DeRank(self, parts, byuser, overriderank, server=None):
    username = parts[2].lower()
    if server:
        factory = server
    else:
        factory = self.client.factory
    if parts[1] == "builder":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if not ((self.client.username in world.ops) or self.client.isMod()) and overriderank:
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not ((parts[-1]) in world.ops) or factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        try:
            world.writers.remove(username)
        except KeyError:
                return ("%s is not a Builder." % username)
        if username in factory.usernames:
            user = factory.usernames[username]
            if user.world == world:
                user.sendBuilderUpdate()
        return ("Removed %s as Builder" % username)
    elif parts[1] == "op":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if not self.client.isWorldOwner() and world != self.client.world:
                return ("You are not an World Owner!")
        else:
            if not parts[-1] == "console":
                if not factory.isWorldOwner(parts[-1]):
                    return ("You are not high enough rank!")
        try:
            world.ops.remove(username)
        except KeyError:
            return ("%s is not an op." % username)
        if username in factory.usernames:
            user = factory.usernames[username]
            if user.world == world:
                user.sendOpUpdate()
        return ("Deopped %s" % username)
    elif parts[1] == "worldowner":
        if len(parts) > 3:
            try:
                world = factory.worlds[parts[3]]
            except KeyError:
                return ("Unknown world \"%s\"" %parts[3])
        else:
            if not server:
                world = self.client.world
            else:
                return "You must provide a world"
        if not server:
            if not self.client.isWorldOwner() and world != self.client.world:
                return ("You are not an World Owner!")
        else:
            if not parts[-1] == "console":
                if not factory.isWorldOwner(parts[-1]):
                    return ("You are not high enough rank!")
        try:
            self.client.world.owner = ("")
        except KeyError:
            return ("%s is not a world owner." % username)
        if username in factory.usernames:
            user = factory.usernames[username]
            if user.world == world:
                user.sendOpUpdate()
        return ("%s is no longer the World Owner." % username)
    elif parts[1] == "member":
        if not server:
            if not self.client.isMod():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        if username in factory.members:
            factory.members.remove(username)
        else:
            return ("No such member \"%s\"" % username.lower())
        if username in factory.usernames:
            factory.usernames[username].sendMemberUpdate()
        return ("%s is no longer a Member." % username.lower())
    elif parts[1] == "globalbuilder":
        if not server:
            if not self.client.isMod():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isMod(parts[-1]):
                    return ("You are not high enough rank!")
        if username in factory.globalbuilders:
            factory.globalbuilders.remove(username)
        else:
            return ("No such global builder \"%s\"" % username.lower())
        if username in factory.usernames:
            factory.usernames[username].sendGlobalBuilderUpdate()
        return ("%s is no longer a Member." % username.lower())
    elif parts[1] == "mod":
        if not server:
            if not self.client.isDirector():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isDirector(parts[-1]):
                    return ("You are not high enough rank!")
        if username in factory.mods:
            factory.mods.remove(username)
        else:
            return ("No such mod \"%s\"" % username.lower())
        if username in factory.usernames:
            factory.usernames[username].sendModUpdate()
        return ("%s is no longer a Mod." % username.lower())
    elif parts[1] == "admin":
        if not server:
            if not self.client.isDirector():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isDirector(parts[-1]):
                    return ("You are not high enough rank!")
        if username in factory.admins:
            factory.admins.remove(username)
            if username in factory.usernames:
                factory.usernames[username].sendAdminUpdate()
            return ("%s is no longer an admin." % username.lower())
        else:
            return ("No such admin \"%s\""% username.lower())
    elif parts[1] == "director":
        if not server:
            if not self.client.isOwner():
                return ("You are not high enough rank!")
        else:
            if not parts[-1] == "console":
                if not factory.isOwner(parts[-1]):
                    return ("You are not high enough rank!")
        if username in factory.directors:
            factory.directors.remove(username)
            if username in factory.usernames:
                factory.usernames[username].sendDirectorUpdate()
            return ("%s is no longer an director." % username.lower())
        else:
            return ("No such director \"%s\""% username.lower())
    else:
        return ("Unknown rank \"%s\""%parts[1])

def Spec(self, username, byuser, overriderank, server=None):
    if server:
        factory = server
    else:
        factory = self.client.factory
    if username in factory.mods:
        return ("You cannot make staff a spec!")
    factory.spectators.add(username)
    if username in factory.usernames:
        factory.usernames[username].sendSpectatorUpdate()
    return ("%s is now a spec." % username)

def Staff(self, server=None):
    Temp = []
    if server:
        factory = server
    else:
        factory = self.client.factory
    if len(factory.directors):
        Temp.append (["Directors:"] + list(factory.directors))
    if len(factory.admins):
        Temp.append (["Admins:"] + list(factory.admins))
    if len(factory.mods):
        Temp.append (["Mods:"] + list(factory.mods))
    return Temp

def Credits(self, server=None):
    Temp = []
    if server:
        factory = server
    else:
        factory = self.client.factory
    Temp.append ("Thanks to the following people for making iCraft possible...")
    Temp.append ("Mojang Specifications (Minecraft): Notch, dock, ez, ...")
    Temp.append ("Creators: aera aka AndrewGodwin (Myne and The Archives), iKJames aka KingJames, JamesKirslis (hlmc.net, iCraft)")
    Temp.append ("Devs: Adam01, AndrewPH, destroyerx1, Dwarfy, erronjason, eugo (Knossus), gdude2002 (arbot), goober, gothfox, NotMeh, ntfwc, PixelEater, revenant, Saanix, sk8rjwd, tehcid, Varriount, willempiee")
    Temp.append ("Others: 099, 2k10, Akai, Antoligy, Aquaskys, Bidoof_King, Bioniclegenius (Red_Link), blahblahbal, BlueProtoman, CDRom, fragmer, GLaDOS (Cortana), iMak, Kelraider, MAup, MystX, PyroPyro, Rils, Roadcrosser, Roujo, setveen, TkTech, Uninspired, and many more...")
    return Temp
