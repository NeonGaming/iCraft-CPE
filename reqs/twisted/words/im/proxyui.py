# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.

#

from reqs.twisted.words.protocols.irc import IRC
from reqs.twisted.python import log
from reqs.twisted.internet.protocol import Factory

class IRCUserInterface(IRC):
    def connectionLost(self):
        del self.factory.ircui

class IRCUIFactory(Factory):
    ircui = None
    def buildProtocol(self):
        if self.ircui:
            log.msg("already logged in")
            return None
        i = IRCUserInterface()
        i.factory = self
        self.ircui = i
        return i

