# -*- test-case-name: twisted.test.test_memcache -*-
# Copyright (c) 2007-2009 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Memcache client protocol. Memcached is a caching server, storing data in the
form of pairs key/value, and memcache is the protocol to talk with it.

To connect to a server, create a factory for L{MemCacheProtocol}::

    from reqs.twisted.internet import reactor, protocol
    from reqs.twisted.protocols.memcache import MemCacheProtocol, DEFAULT_PORT
    d = protocol.ClientCreator(reactor, MemCacheProtocol
        ).connectTCP("localhost", DEFAULT_PORT)
    def doSomething(proto):
        # Here you call the memcache operations
        return proto.set("mykey", "a lot of data")
    d.addCallback(doSomething)
    reactor.run()

All the operations of the memcache protocol are present, but
L{MemCacheProtocol.set} and L{MemCacheProtocol.get} are the more important.

See U{http://code.sixapart.com/svn/memcached/trunk/server/doc/protocol.txt} for
more information about the protocol.
"""

try:
    from collections import deque
except ImportError:
    class deque(list):
        def popleft(self):
            return self.pop(0)


from reqs.twisted.protocols.basic import LineReceiver
from reqs.twisted.protocols.policies import TimeoutMixin
from reqs.twisted.internet.defer import Deferred, fail, TimeoutError
from reqs.twisted.python import log



DEFAULT_PORT = 11211



class NoSuchCommand(Exception):
    """
    Exception raised when a non existent command is called.
    """



class ClientError(Exception):
    """
    Error caused by an invalid client call.
    """



class ServerError(Exception):
    """
    Problem happening on the server.
    """



class Command(object):
    """
    Wrap a client action into an object, that holds the values used in the
    protocol.

    @ivar _deferred: the L{Deferred} object that will be fired when the result
        arrives.
    @type _deferred: L{Deferred}

    @ivar command: name of the command sent to the server.
    @type command: C{str}
    """

    def __init__(self, command, **kwargs):
        """
        Create a command.

        @param command: the name of the command.
        @type command: C{str}

        @param kwargs: this values will be stored as attributes of the object
            for future use
        """
        self.command = command
        self._deferred = Deferred()
        for k, v in kwargs.items():
            setattr(self, k, v)


    def success(self, value):
        """
        Shortcut method to fire the underlying deferred.
        """
        self._deferred.callback(value)


    def fail(self, error):
        """
        Make the underlying deferred fails.
        """
        self._deferred.errback(error)



class MemCacheProtocol(LineReceiver, TimeoutMixin):
    """
    MemCache protocol: connect to a memcached server to store/retrieve values.

    @ivar persistentTimeOut: the timeout period used to wait for a response.
    @type persistentTimeOut: C{int}

    @ivar _current: current list of requests waiting for an answer from the
        server.
    @type _current: C{deque} of L{Command}

    @ivar _lenExpected: amount of data expected in raw mode, when reading for
        a value.
    @type _lenExpected: C{int}

    @ivar _getBuffer: current buffer of data, used to store temporary data
        when reading in raw mode.
    @type _getBuffer: C{list}

    @ivar _bufferLength: the total amount of bytes in C{_getBuffer}.
    @type _bufferLength: C{int}

    @ivar _disconnected: indicate if the connectionLost has been called or not.
    @type _disconnected: C{bool}
    """
    MAX_KEY_LENGTH = 250
    _disconnected = False

    def __init__(self, timeOut=60):
        """
        Create the protocol.

        @param timeOut: the timeout to wait before detecting that the
            connection is dead and close it. It's expressed in seconds.
        @type timeOut: C{int}
        """
        self._current = deque()
        self._lenExpected = None
        self._getBuffer = None
        self._bufferLength = None
        self.persistentTimeOut = self.timeOut = timeOut


    def _cancelCommands(self, reason):
        """
        Cancel all the outstanding commands, making them fail with C{reason}.
        """
        while self._current:
            cmd = self._current.popleft()
            cmd.fail(reason)


    def timeoutConnection(self):
        """
        Close the connection in case of timeout.
        """
        self._cancelCommands(TimeoutError("Connection timeout"))
        self.transport.loseConnection()


    def connectionLost(self, reason):
        """
        Cause any outstanding commands to fail.
        """
        self._disconnected = True
        self._cancelCommands(reason)
        LineReceiver.connectionLost(self, reason)


    def sendLine(self, line):
        """
        Override sendLine to add a timeout to response.
        """
        if not self._current:
            self.setTimeout(self.persistentTimeOut)
        LineReceiver.sendLine(self, line)


    def rawDataReceived(self, data):
        """
        Collect data for a get.
        """
        self.resetTimeout()
        self._getBuffer.append(data)
        self._bufferLength += len(data)
        if self._bufferLength >= self._lenExpected + 2:
            data = "".join(self._getBuffer)
            buf = data[:self._lenExpected]
            rem = data[self._lenExpected + 2:]
            val = buf
            self._lenExpected = None
            self._getBuffer = None
            self._bufferLength = None
            cmd = self._current[0]
            if cmd.multiple:
                flags, cas = cmd.values[cmd.currentKey]
                cmd.values[cmd.currentKey] = (flags, cas, val)
            else:
                cmd.value = val
            self.setLineMode(rem)


    def cmd_STORED(self):
        """
        Manage a success response to a set operation.
        """
        self._current.popleft().success(True)


    def cmd_NOT_STORED(self):
        """
        Manage a specific 'not stored' response to a set operation: this is not
        an error, but some condition wasn't met.
        """
        self._current.popleft().success(False)


    def cmd_END(self):
        """
        This the end token to a get or a stat operation.
        """
        cmd = self._current.popleft()
        if cmd.command == "get":
            if cmd.multiple:
                values = dict([(key, val[::2]) for key, val in
                               cmd.values.iteritems()])
                cmd.success(values)
            else:
                cmd.success((cmd.flags, cmd.value))
        elif cmd.command == "gets":
            if cmd.multiple:
                cmd.success(cmd.values)
            else:
                cmd.success((cmd.flags, cmd.cas, cmd.value))
        elif cmd.command == "stats":
            cmd.success(cmd.values)


    def cmd_NOT_FOUND(self):
        """
        Manage error response for incr/decr/delete.
        """
        self._current.popleft().success(False)


    def cmd_VALUE(self, line):
        """
        Prepare the reading a value after a get.
        """
        cmd = self._current[0]
        if cmd.command == "get":
            key, flags, length = line.split()
            cas = ""
        else:
            key, flags, length, cas = line.split()
        self._lenExpected = int(length)
        self._getBuffer = []
        self._bufferLength = 0
        if cmd.multiple:
            if key not in cmd.keys:
                raise RuntimeError("Unexpected commands answer.")
            cmd.currentKey = key
            cmd.values[key] = [int(flags), cas]
        else:
            if cmd.key != key:
                raise RuntimeError("Unexpected commands answer.")
            cmd.flags = int(flags)
            cmd.cas = cas
        self.setRawMode()


    def cmd_STAT(self, line):
        """
        Reception of one stat line.
        """
        cmd = self._current[0]
        key, val = line.split(" ", 1)
        cmd.values[key] = val


    def cmd_VERSION(self, versionData):
        """
        Read version token.
        """
        self._current.popleft().success(versionData)


    def cmd_ERROR(self):
        """
        An non-existent command has been sent.
        """
        log.err("Non-existent command sent.")
        cmd = self._current.popleft()
        cmd.fail(NoSuchCommand())


    def cmd_CLIENT_ERROR(self, errText):
        """
        An invalid input as been sent.
        """
        log.err("Invalid input: %s" % (errText,))
        cmd = self._current.popleft()
        cmd.fail(ClientError(errText))


    def cmd_SERVER_ERROR(self, errText):
        """
        An error has happened server-side.
        """
        log.err("Server error: %s" % (errText,))
        cmd = self._current.popleft()
        cmd.fail(ServerError(errText))


    def cmd_DELETED(self):
        """
        A delete command has completed successfully.
        """
        self._current.popleft().success(True)


    def cmd_OK(self):
        """
        The last command has been completed.
        """
        self._current.popleft().success(True)


    def cmd_EXISTS(self):
        """
        A C{checkAndSet} update has failed.
        """
        self._current.popleft().success(False)


    def lineReceived(self, line):
        """
        Receive line commands from the server.
        """
        self.resetTimeout()
        token = line.split(" ", 1)[0]
        # First manage standard commands without space
        cmd = getattr(self, "cmd_%s" % (token,), None)
        if cmd is not None:
            args = line.split(" ", 1)[1:]
            if args:
                cmd(args[0])
            else:
                cmd()
        else:
            # Then manage commands with space in it
            line = line.replace(" ", "_")
            cmd = getattr(self, "cmd_%s" % (line,), None)
            if cmd is not None:
                cmd()
            else:
                # Increment/Decrement response
                cmd = self._current.popleft()
                val = int(line)
                cmd.success(val)
        if not self._current:
            # No pending request, remove timeout
            self.setTimeout(None)


    def increment(self, key, val=1):
        """
        Increment the value of C{key} by given value (default to 1).
        C{key} must be consistent with an int. Return the new value.

        @param key: the key to modify.
        @type key: C{str}

        @param val: the value to increment.
        @type val: C{int}

        @return: a deferred with will be called back with the new value
            associated with the key (after the increment).
        @rtype: L{Deferred}
        """
        return self._incrdecr("incr", key, val)


    def decrement(self, key, val=1):
        """
        Decrement the value of C{key} by given value (default to 1).
        C{key} must be consistent with an int. Return the new value, coerced to
        0 if negative.

        @param key: the key to modify.
        @type key: C{str}

        @param val: the value to decrement.
        @type val: C{int}

        @return: a deferred with will be called back with the new value
            associated with the key (after the decrement).
        @rtype: L{Deferred}
        """
        return self._incrdecr("decr", key, val)


    def _incrdecr(self, cmd, key, val):
        """
        Internal wrapper for incr/decr.
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        if not isinstance(key, str):
            return fail(ClientError(
                "Invalid type for key: %s, expecting a string" % (type(key),)))
        if len(key) > self.MAX_KEY_LENGTH:
            return fail(ClientError("Key too long"))
        fullcmd = "%s %s %d" % (cmd, key, int(val))
        self.sendLine(fullcmd)
        cmdObj = Command(cmd, key=key)
        self._current.append(cmdObj)
        return cmdObj._deferred


    def replace(self, key, val, flags=0, expireTime=0):
        """
        Replace the given C{key}. It must already exist in the server.

        @param key: the key to replace.
        @type key: C{str}

        @param val: the new value associated with the key.
        @type val: C{str}

        @param flags: the flags to store with the key.
        @type flags: C{int}

        @param expireTime: if different from 0, the relative time in seconds
            when the key will be deleted from the store.
        @type expireTime: C{int}

        @return: a deferred that will fire with C{True} if the operation has
            succeeded, and C{False} with the key didn't previously exist.
        @rtype: L{Deferred}
        """
        return self._set("replace", key, val, flags, expireTime, "")


    def add(self, key, val, flags=0, expireTime=0):
        """
        Add the given C{key}. It must not exist in the server.

        @param key: the key to add.
        @type key: C{str}

        @param val: the value associated with the key.
        @type val: C{str}

        @param flags: the flags to store with the key.
        @type flags: C{int}

        @param expireTime: if different from 0, the relative time in seconds
            when the key will be deleted from the store.
        @type expireTime: C{int}

        @return: a deferred that will fire with C{True} if the operation has
            succeeded, and C{False} with the key already exists.
        @rtype: L{Deferred}
        """
        return self._set("add", key, val, flags, expireTime, "")


    def set(self, key, val, flags=0, expireTime=0):
        """
        Set the given C{key}.

        @param key: the key to set.
        @type key: C{str}

        @param val: the value associated with the key.
        @type val: C{str}

        @param flags: the flags to store with the key.
        @type flags: C{int}

        @param expireTime: if different from 0, the relative time in seconds
            when the key will be deleted from the store.
        @type expireTime: C{int}

        @return: a deferred that will fire with C{True} if the operation has
            succeeded.
        @rtype: L{Deferred}
        """
        return self._set("set", key, val, flags, expireTime, "")


    def checkAndSet(self, key, val, cas, flags=0, expireTime=0):
        """
        Change the content of C{key} only if the C{cas} value matches the
        current one associated with the key. Use this to store a value which
        hasn't been modified since last time you fetched it.

        @param key: The key to set.
        @type key: C{str}

        @param val: The value associated with the key.
        @type val: C{str}

        @param cas: Unique 64-bit value returned by previous call of C{get}.
        @type cas: C{str}

        @param flags: The flags to store with the key.
        @type flags: C{int}

        @param expireTime: If different from 0, the relative time in seconds
            when the key will be deleted from the store.
        @type expireTime: C{int}

        @return: A deferred that will fire with C{True} if the operation has
            succeeded, C{False} otherwise.
        @rtype: L{Deferred}
        """
        return self._set("cas", key, val, flags, expireTime, cas)


    def _set(self, cmd, key, val, flags, expireTime, cas):
        """
        Internal wrapper for setting values.
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        if not isinstance(key, str):
            return fail(ClientError(
                "Invalid type for key: %s, expecting a string" % (type(key),)))
        if len(key) > self.MAX_KEY_LENGTH:
            return fail(ClientError("Key too long"))
        if not isinstance(val, str):
            return fail(ClientError(
                "Invalid type for value: %s, expecting a string" %
                (type(val),)))
        if cas:
            cas = " " + cas
        length = len(val)
        fullcmd = "%s %s %d %d %d%s" % (
            cmd, key, flags, expireTime, length, cas)
        self.sendLine(fullcmd)
        self.sendLine(val)
        cmdObj = Command(cmd, key=key, flags=flags, length=length)
        self._current.append(cmdObj)
        return cmdObj._deferred


    def append(self, key, val):
        """
        Append given data to the value of an existing key.

        @param key: The key to modify.
        @type key: C{str}

        @param val: The value to append to the current value associated with
            the key.
        @type val: C{str}

        @return: A deferred that will fire with C{True} if the operation has
            succeeded, C{False} otherwise.
        @rtype: L{Deferred}
        """
        # Even if flags and expTime values are ignored, we have to pass them
        return self._set("append", key, val, 0, 0, "")


    def prepend(self, key, val):
        """
        Prepend given data to the value of an existing key.

        @param key: The key to modify.
        @type key: C{str}

        @param val: The value to prepend to the current value associated with
            the key.
        @type val: C{str}

        @return: A deferred that will fire with C{True} if the operation has
            succeeded, C{False} otherwise.
        @rtype: L{Deferred}
        """
        # Even if flags and expTime values are ignored, we have to pass them
        return self._set("prepend", key, val, 0, 0, "")


    def get(self, key, withIdentifier=False):
        """
        Get the given C{key}. It doesn't support multiple keys. If
        C{withIdentifier} is set to C{True}, the command issued is a C{gets},
        that will return the current identifier associated with the value. This
        identifier has to be used when issuing C{checkAndSet} update later,
        using the corresponding method.

        @param key: The key to retrieve.
        @type key: C{str}

        @param withIdentifier: If set to C{True}, retrieve the current
            identifier along with the value and the flags.
        @type withIdentifier: C{bool}

        @return: A deferred that will fire with the tuple (flags, value) if
            C{withIdentifier} is C{False}, or (flags, cas identifier, value)
            if C{True}.  If the server indicates there is no value
            associated with C{key}, the returned value will be C{None} and
            the returned flags will be C{0}.
        @rtype: L{Deferred}
        """
        return self._get([key], withIdentifier, False)


    def getMultiple(self, keys, withIdentifier=False):
        """
        Get the given list of C{keys}.  If C{withIdentifier} is set to C{True},
        the command issued is a C{gets}, that will return the identifiers
        associated with each values. This identifier has to be used when
        issuing C{checkAndSet} update later, using the corresponding method.

        @param keys: The keys to retrieve.
        @type keys: C{list} of C{str}

        @param withIdentifier: If set to C{True}, retrieve the identifiers
            along with the values and the flags.
        @type withIdentifier: C{bool}

        @return: A deferred that will fire with a dictionary with the elements
            of C{keys} as keys and the tuples (flags, value) as values if
            C{withIdentifier} is C{False}, or (flags, cas identifier, value) if
            C{True}.  If the server indicates there is no value associated with
            C{key}, the returned values will be C{None} and the returned flags
            will be C{0}.
        @rtype: L{Deferred}

        @since: 9.0
        """
        return self._get(keys, withIdentifier, True)

    def _get(self, keys, withIdentifier, multiple):
        """
        Helper method for C{get} and C{getMultiple}.
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        for key in keys:
            if not isinstance(key, str):
                return fail(ClientError(
                    "Invalid type for key: %s, expecting a string" % (type(key),)))
            if len(key) > self.MAX_KEY_LENGTH:
                return fail(ClientError("Key too long"))
        if withIdentifier:
            cmd = "gets"
        else:
            cmd = "get"
        fullcmd = "%s %s" % (cmd, " ".join(keys))
        self.sendLine(fullcmd)
        if multiple:
            values = dict([(key, (0, "", None)) for key in keys])
            cmdObj = Command(cmd, keys=keys, values=values, multiple=True)
        else:
            cmdObj = Command(cmd, key=keys[0], value=None, flags=0, cas="",
                             multiple=False)
        self._current.append(cmdObj)
        return cmdObj._deferred

    def stats(self, arg=None):
        """
        Get some stats from the server. It will be available as a dict.

        @param arg: An optional additional string which will be sent along
            with the I{stats} command.  The interpretation of this value by
            the server is left undefined by the memcache protocol
            specification.
        @type arg: L{NoneType} or L{str}

        @return: a deferred that will fire with a C{dict} of the available
            statistics.
        @rtype: L{Deferred}
        """
        if arg:
            cmd = "stats " + arg
        else:
            cmd = "stats"
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        self.sendLine(cmd)
        cmdObj = Command("stats", values={})
        self._current.append(cmdObj)
        return cmdObj._deferred


    def version(self):
        """
        Get the version of the server.

        @return: a deferred that will fire with the string value of the
            version.
        @rtype: L{Deferred}
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        self.sendLine("version")
        cmdObj = Command("version")
        self._current.append(cmdObj)
        return cmdObj._deferred


    def delete(self, key):
        """
        Delete an existing C{key}.

        @param key: the key to delete.
        @type key: C{str}

        @return: a deferred that will be called back with C{True} if the key
            was successfully deleted, or C{False} if not.
        @rtype: L{Deferred}
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        if not isinstance(key, str):
            return fail(ClientError(
                "Invalid type for key: %s, expecting a string" % (type(key),)))
        self.sendLine("delete %s" % key)
        cmdObj = Command("delete", key=key)
        self._current.append(cmdObj)
        return cmdObj._deferred


    def flushAll(self):
        """
        Flush all cached values.

        @return: a deferred that will be called back with C{True} when the
            operation has succeeded.
        @rtype: L{Deferred}
        """
        if self._disconnected:
            return fail(RuntimeError("not connected"))
        self.sendLine("flush_all")
        cmdObj = Command("flush_all")
        self._current.append(cmdObj)
        return cmdObj._deferred



__all__ = ["MemCacheProtocol", "DEFAULT_PORT", "NoSuchCommand", "ClientError",
           "ServerError"]
