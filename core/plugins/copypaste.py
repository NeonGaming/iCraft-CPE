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

import sys
from reqs.twisted.internet import reactor
from core.plugins import ProtocolPlugin
from core.decorators import *
from core.constants import *

class BsavePlugin(ProtocolPlugin):
    
    commands = {
        "copy": "commandSave",
        "paste": "commandLoad",
        "pasta": "commandLoad",
        "rotate": "commandRotate",
        "xzrotate": "commandRotatexz",
        "xyrotate": "commandRotatexy",
        "yzrotate": "commandRotateyz",
    }
    
    @build_list
    @builder_only
    def commandLoad(self, parts, byuser, overriderank):
        "/paste [x y z] - Builder\nAliases: pasta\nRestore blocks saved earlier using /copy"
        if len(parts) < 4 and len(parts) != 1:
            self.client.sendServerMessage("Please enter coordinates.")
        else:
            if len(parts) == 1:
                try:
                    x, y, z = self.client.last_block_changes[0]
                except IndexError:
                    self.client.sendServerMessage("You have not placed a marker yet.")
                    return
            else:
                try:
                    x = int(parts[1])
                    y = int(parts[2])
                    z = int(parts[3])
                except ValueError:
                    self.client.sendServerMessage("All parameters must be integers")
                    return
            # Check whether we have anything saved
            try:
                num_saved = len(self.client.bsaved_blocks)
                if byuser:
                    self.client.sendServerMessage("Loading %d blocks..." % num_saved)
            except AttributeError:
                self.client.sendServerMessage("Please /copy something first.")
                return
            # Draw all the blocks on, I guess
            # We use a generator so we can slowly release the blocks
            # We also keep world as a local so they can't change worlds and affect the new one
            world = self.client.world
            def generate_changes():
                for i, j, k, block in self.client.bsaved_blocks:
                    if not self.client.AllowedToBuild(i, j, k) and overriderank==False:
                        return
                    rx = x + i
                    ry = y + j
                    rz = z + k
                    try:
                        world[rx, ry, rz] = block
                        self.client.queueTask(TASK_BLOCKSET, (rx, ry, rz, block), world=world)
                        self.client.sendBlock(rx, ry, rz, block)
                    except AssertionError:
                        self.client.sendServerMessage("Out of bounds paste error.")
                        return
                    yield
            # Now, set up a loop delayed by the reactor
            block_iter = iter(generate_changes())
            def do_step():
                # Do 10 blocks
                try:
                    for x in range(10):
                        block_iter.next()
                    reactor.callLater(0.01, do_step)
                except StopIteration:
                    if byuser:
                        self.client.sendServerMessage("Your paste just completed.")
                    pass
            do_step()

    @build_list
    @builder_only
    def commandSave(self, parts, byuser, overriderank):
        "/copy [x y z x2 y2 z2] - Builder\nCopy blocks using specified offsets."
        if len(parts) < 7 and len(parts) != 1:
            self.client.sendServerMessage("Please enter coordinates.")
        else:
            if len(parts) == 1:
                try:
                    x, y, z = self.client.last_block_changes[0]
                    x2, y2, z2 = self.client.last_block_changes[1]
                except IndexError:
                    self.client.sendServerMessage("You have not clicked two corners yet.")
                    return
            else:
                try:
                    x = int(parts[1])
                    y = int(parts[2])
                    z = int(parts[3])
                    x2 = int(parts[4])
                    y2 = int(parts[5])
                    z2 = int(parts[6])
                except ValueError:
                    self.client.sendServerMessage("All parameters must be integers")
                    return
            if x > x2:
                x, x2 = x2, x
            if y > y2:
                y, y2 = y2, y
            if z > z2:
                z, z2 = z2, z
            if self.client.isDirector() or overriderank:
                limit = self.client.factory.build_director
            elif self.client.isAdmin():
                limit = self.client.factory.build_admin
            elif self.client.isMod():
                limit = self.client.factory.build_mod
            elif self.client.isOp():
                limit = self.client.factory.build_op
            else:
                limit = self.client.factory.build_other
            # Stop them doing silly things
            if (x2 - x) * (y2 - y) * (z2 - z) > limit:
                self.client.sendServerMessage("Sorry, that area is too big for you to copy.")
                return
            self.client.bsaved_blocks = set()
            world = self.client.world
            def generate_changes():
                for i in range(x, x2+1):
                    for j in range(y, y2+1):
                        for k in range(z, z2+1):
                            if not self.client.AllowedToBuild(i, j, k) and overriderank==False:
                                return
                            try:
                                check_offset = world.blockstore.get_offset(i, j, k)
                                block = world.blockstore.raw_blocks[check_offset]
                                self.client.bsaved_blocks.add((i -x, j - y, k -z, block))
                            except AssertionError:
                                self.client.sendServerMessage("Out of bounds copy error.")
                                return
                            yield
            # Now, set up a loop delayed by the reactor
            block_iter = iter(generate_changes())
            def do_step():
                # Do 10 blocks
                try:
                    for x in range(10):
                        block_iter.next()
                    reactor.callLater(0.01, do_step)
                except StopIteration:
                    if byuser:
                        self.client.sendServerMessage("Your copy just completed.")
                    pass
            do_step()

    @build_list
    @builder_only
    def commandRotate(self, parts, byuser, overriderank):
        "/rotate angle - Builder\nAllows you to rotate what you copied."
        if len(parts)<2:
            self.client.sendServerMessage("You must give an angle to rotate!")
            return
        try:
            angle = int(parts[1])
        except ValueError:
            self.client.sendServerMessage("Angle must be an integer!")
            return
        if angle % 90 != 0:
            self.client.sendServerMessage("Angle must be divisible by 90!")
            return
        rotations = angle/90
        self.client.sendServerMessage("Rotating %s degrees..." %angle)
        for rotation in range(rotations):
            tempblocks = set()
            xmax=zmax=0
            try:
                for x, y, z, block in self.client.bsaved_blocks:
                    if x > xmax:
                        xmax=x
                    if z > zmax:
                        zmax=z
            except:
                self.client.sendServerMessage("You haven't used /copy yet.")
                return
            for x, y, z, block in self.client.bsaved_blocks:
                tempx = x
                tempz = z
                x = zmax-tempz
                z = tempx
                tempblocks.add((x,y,z,block))
            self.client.bsaved_blocks = tempblocks
        if byuser:
            self.client.sendServerMessage("Your rotate just completed.")

    @build_list
    @builder_only
    def commandRotatexz(self, parts, byuser, overriderank):
        "/xzrotate angle - Builder\nAllows you to rotate what you copied\nalong the X/Z axis."
        if len(parts)<2:
            self.client.sendServerMessage("You must give an angle to rotate!")
            return
        try:
            angle = int(parts[1])
        except ValueError:
            self.client.sendServerMessage("Angle must be an integer!")
            return
        if angle % 90 != 0:
            self.client.sendServerMessage("Angle must be divisible by 90!")
            return
        rotations = angle/90
        self.client.sendServerMessage("Rotating %s degrees..." %angle)
        for rotation in range(rotations):
            tempblocks = set()
            xmax=zmax=0
            try:
                for x, y, z, block in self.client.bsaved_blocks:
                    if x > xmax:
                        xmax=x
                    if z > zmax:
                        zmax=z
            except:
                self.client.sendServerMessage("You haven't used /copy yet.")
                return
            for x, y, z, block in self.client.bsaved_blocks:
                tempx = x
                tempz = z
                x = zmax-tempz
                z = tempx
                tempblocks.add((x,y,z,block))
            self.client.bsaved_blocks = tempblocks
        if byuser:
            self.client.sendServerMessage("Your rotate just completed.")

    @build_list
    @builder_only
    def commandRotatexy(self, parts, byuser, overriderank):
        "/xyrotate angle - Builder\nAllows you to rotate what you copied\nalong the X/Y axis."
        if len(parts)<2:
            self.client.sendServerMessage("You must give an angle to rotate!")
            return
        try:
            angle = int(parts[1])
        except ValueError:
            self.client.sendServerMessage("Angle must be an integer!")
            return
        if angle % 90 != 0:
            self.client.sendServerMessage("Angle must be divisible by 90!")
            return
        rotations = angle/90
        self.client.sendServerMessage("Rotating %s degrees..." %angle)
        for rotation in range(rotations):
            tempblocks = set()
            xmax=ymax=0
            try:
                for x, y, z, block in self.client.bsaved_blocks:
                    if x > xmax:
                        xmax=x
                    if y > ymax:
                        ymax=y
            except:
                self.client.sendServerMessage("You haven't used /copy yet.")
                return
            for x, y, z, block in self.client.bsaved_blocks:
                tempx = x
                tempy = y
                x = ymax-tempy
                y = tempx
                tempblocks.add((x,y,z,block))
            self.client.bsaved_blocks = tempblocks
        if byuser:
            self.client.sendServerMessage("Your rotate just completed.")

    @build_list
    @builder_only
    def commandRotateyz(self, parts, byuser, overriderank):
        "/yzrotate angle - Builder\nAllows you to rotate what you copied\nalong the Y/Z axis."
        if len(parts)<2:
            self.client.sendServerMessage("You must give an angle to rotate!")
            return
        try:
            angle = int(parts[1])
        except ValueError:
            self.client.sendServerMessage("Angle must be an integer!")
            return
        if angle % 90 != 0:
            self.client.sendServerMessage("Angle must be divisible by 90!")
            return
        rotations = angle/90
        self.client.sendServerMessage("Rotating %s degrees..." %angle)
        for rotation in range(rotations):
            tempblocks = set()
            ymax=zmax=0
            try:
                for x, y, z, block in self.client.bsaved_blocks:
                    if y > ymax:
                        ymax=y
                    if z > zmax:
                        zmax=z
            except:
                self.client.sendServerMessage("You haven't used /copy yet.")
                return
            for x, y, z, block in self.client.bsaved_blocks:
                tempy = y
                tempz = z
                y = zmax-tempz
                z = tempy
                tempblocks.add((x,y,z,block))
            self.client.bsaved_blocks = tempblocks
        if byuser:
            self.client.sendServerMessage("Your rotate just completed.")
