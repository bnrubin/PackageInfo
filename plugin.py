###
# Copyright (c) 2008, Terence Simpson
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircutils as ircutils
import supybot.conf as conf
import os
import packages
reload(packages)

class PackageInfo(callbacks.Plugin):
    """Lookup package information via apt-cache/apt-file"""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(PackageInfo, self)
        self.__parent.__init__(irc)
        self.Apt = packages.Apt(self)

    def callPrecedence(self, irc):
        before = []
        for cb in irc.callbacks:
            if cb.name() == 'IRCLogin':
                before.append(cb)
        return (before, [])

    def __getRelease(self, irc, release, channel, doError=True):
        if release:
            return release
        release = self.registryValue("defaultRelease", channel)
        if not release:
            if doError:
                irc.error("'supybot.plugins.PackageInfo.defaultRelease' is not set")
            return None
        return release

    def __getChannel(self, channel):
        return ircutils.isChannel(channel) and channel or None

    def info(self, irc, msg, args, package, release):
        """<package> [<release>]

        Lookup information for <package>, optionally in <release>
        """
        channel = self.__getChannel(msg.args[0])
        release = self.__getRelease(irc, release, channel)
        if not release:
            return
        irc.reply(self.Apt.info(package, release))

    info = wrap(info, ['text', optional('text')])

    def find(self, irc, msg, args, package, release):
        """<package/filename> [<release>]

        Search for <package> or, of that fails, find <filename>'s package(s).
        Optionally in <release>
        """
        channel = self.__getChannel(msg.args[0])
        release = self.__getRelease(irc, release, channel)
        if not release:
            return
        irc.reply(self.Apt.find(package, release))

    find = wrap(find, ['text', optional('text')])

    def addressed(self, irc, msg, channel):
        nick = irc.nick
        prefixChars=self.registryValue("prefixchar", channel)
        nicks=None
        prefixStrings=None
        whenAddressedByNick=None
        whenAddressedByNickAtEnd=None

        def get(group):
            if ircutils.isChannel(target):
                group = group.get(target)
            return group()
        def stripPrefixStrings(payload):
            for prefixString in prefixStrings:
                if payload.startswith(prefixString):
                    payload = payload[len(prefixString):].lstrip()
            return payload

        (target, payload) = msg.args
        if not payload:
            return ''
        if prefixChars is None:
            prefixChars = get(conf.supybot.reply.whenAddressedBy.chars)
        if whenAddressedByNick is None:
            whenAddressedByNick = get(conf.supybot.reply.whenAddressedBy.nick)
        if whenAddressedByNickAtEnd is None:
            r = conf.supybot.reply.whenAddressedBy.nick.atEnd
            whenAddressedByNickAtEnd = get(r)
        if prefixStrings is None:
            prefixStrings = get(conf.supybot.reply.whenAddressedBy.strings)
        for string in prefixStrings:
            if payload.startswith(string):
                return stripPrefixStrings(payload)
        if payload[0] in prefixChars:
            return payload[1:].strip()
        if nicks is None:
            nicks = get(conf.supybot.reply.whenAddressedBy.nicks)
            nicks = map(ircutils.toLower, nicks)
        else:
            nicks = list(nicks)
        nicks.insert(0, ircutils.toLower(nick))
        if ircutils.nickEqual(target, nick):
            payload = stripPrefixStrings(payload)
            while payload and payload[0] in prefixChars:
                payload = payload[1:].lstrip()
            return payload
        elif whenAddressedByNick:
            for nick in nicks:
                lowered = ircutils.toLower(payload)
                if lowered.startswith(nick):
                    try:
                        (maybeNick, rest) = payload.split(None, 1)
                        toContinue = False
                        while not ircutils.isNick(maybeNick, strictRfc=True):
                            if maybeNick[-1].isalnum():
                                toContinue = True
                                break
                            maybeNick = maybeNick[:-1]
                        if toContinue:
                            continue
                        if ircutils.nickEqual(maybeNick, nick):
                            return rest
                        else:
                            continue
                    except ValueError:
                        continue
                elif whenAddressedByNickAtEnd and lowered.endswith(nick):
                    rest = payload[:-len(nick)]
                    possiblePayload = rest.rstrip(' \t,;')
                    if possiblePayload != rest:
                        return possiblePayload
        if conf.supybot.reply.whenNotAddressed():
            return payload
        else:
            return ''

    def doPrivmsg(self, irc, msg):
        channel = self.__getChannel(msg.args[0])
        if not channel:
            return
        if not self.registryValue("enabled", channel):
            return
        release = self.__getRelease(irc, None, channel, False)
        if not release:
            return
        if chr(1) in msg.args[1]: # CTCP
            return

        text = self.addressed(irc, msg, channel)
        if not text:
            return
        if msg.args[1][0] in str(conf.supybot.reply.whenAddressedBy.get('chars')):
            return
        if text.lower()[:4] not in ("find", "info"):
            return

        if text.lower()[:4] == "find":
            irc.reply(self.Apt.find(text[4:].strip(), self.registryValue("defaultRelease", channel)))
        else:
            irc.reply(self.Apt.info(text[4:].strip(), self.registryValue("defaultRelease", channel)))

Class = PackageInfo


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
