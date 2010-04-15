###
# Copyright (c) 2008-2010, Terence Simpson <tsimpson@ubuntu.com>
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
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
import supybot.ircutils as ircutils
import supybot.ircdb as ircdb
import supybot.conf as conf
import os
import re
import time
import packages
reload(packages)

def get_user(msg):
    try:
        user = ircdb.users.getUser(msg.prefix)
    except:
        return False
    return user

## Taken from Encyclopedia ##
# Repeat filtering message queue
msgcache = {}
def queue(irc, to, msg):
    now = time.time()
    for m in msgcache.keys():
        if msgcache[m] < now - 30:
            msgcache.pop(m)
    for m in msgcache:
        if m[0] == irc and m[1] == to:
            oldmsg = m[2]
            if msg == oldmsg or oldmsg.endswith(msg):
                break
            if msg.endswith(oldmsg):
                msg = msg[:-len(oldmsg)] + 'please see above'
    else:
        msgcache[(irc, to, msg)] = now
        irc.queueMsg(ircmsgs.privmsg(to, msg))

class PackageInfo(callbacks.Plugin):
    """Lookup package information via apt-cache/apt-file"""
    threaded = True
    space_re = re.compile(r'  *')

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
        defaultRelease = self.registryValue("defaultRelease", channel)
        if not defaultRelease:
            if doError:
                irc.error("'supybot.plugins.PackageInfo.defaultRelease' is not set")
            return (None, None)
        if not release:
            return (defaultRelease, None)
        (release, rest) = (release.split(' ', 1) + [None])[:2]
        if release[0] in ('|', '>'):
            return (defaultRelease, "%s %s" % (release, rest))
        return (release, rest)

    def __getChannel(self, channel):
        return ircutils.isChannel(channel) and channel or None

    def real_info(self, irc, msg, args, package, release):
        """<package> [<release>]

        Lookup information for <package>, optionally in <release>
        """
        channel = self.__getChannel(msg.args[0])
        reply_target = ircutils.replyTo(msg)
        (release, rest) = self.__getRelease(irc, release, channel)
        if not release:
            return
        reply = self.Apt.info(package, release)
        if rest:
            if rest[0] == '|':
                try:
                    target = rest.split()[1]
                    if target.lower() == "me":
                        target = msg.nick
                    queue(irc, reply_target, "%s: %s" % (target, reply))
                    return
                except Exception, e:
                    self.log.info("Info: Exception in pipe: %r" % e)
                    pass
            elif rest[0] == '>':
                try:
                    target = rest.split()[1]
                    if target.lower() == "me":
                        target = msg.nick
                    queue(irc, target, "<%s> wants you to know: %s" % (msg.nick, reply))
                    return
                except Exception, e:
                    self.log.info("Info: Exception in redirect: %r" % e)
                    pass

        queue(irc, reply_target, reply)

    info = wrap(real_info, ['anything', optional('text')])

    def real_find(self, irc, msg, args, package, release):
        """<package/filename> [<release>]

        Search for <package> or, of that fails, find <filename>'s package(s).
        Optionally in <release>
        """
        channel = self.__getChannel(msg.args[0])
        reply_target = ircutils.replyTo(msg)
        (release, rest) = self.__getRelease(irc, release, channel)
        if not release:
            return
        reply = self.Apt.find(package, release)
        if rest:
            if rest[0] == '|':
                try:
                    target = rest.split()[1]
                    if target.lower() == "me":
                        target = msg.nick
                    queue(irc, reply_target, "%s: %s" % (target, reply))
                    return
                except Exception, e:
                    self.log.info("Find: Exception in pipe: %r" % e)
                    pass
            elif rest[0] == '>':
                try:
                    target = rest.split()[1]
                    if target.lower() == "me":
                        target = msg.nick
                    queue(irc, target, "<%s> wants you to know: %s" % (msg.nick, reply))
                    return
                except Exception, e:
                    self.log.info("Find: Exception in redirect: %r" % e)
                    pass

        queue(irc, reply_target, reply)

    find = wrap(real_find, ['anything', optional('text')])

    def privmsg(self, irc, msg, user):
        channel = self.__getChannel(msg.args[0])
        text = self.space_re.subn(' ', msg.args[1].strip())[0]
        if text[0] == self.registryValue("prefixchar"):
            text = text[1:].strip()
        if user and text[0] in str(conf.supybot.reply.whenAddressedBy.get('chars')):
            return
        (cmd, rest) = (text.split(' ', 1) + [None])[:2]
        if cmd not in ("find", "info"):
            return
        if not rest:
            return
        (term, rest) = (rest.split(' ', 1) + [None])[:2]
        if cmd == "find":
            self.real_find(irc, msg, [], term, rest)
        else:
            self.real_info(irc, msg, [], term, rest)

    def chanmsg(self, irc, msg, user):
        channel = self.__getChannel(msg.args[0])
        text = self.space_re.subn(' ', msg.args[1].strip())[0]
        if text[0] != self.registryValue("prefixchar", channel):
            return
        text = text[1:]
        (cmd, rest) = (text.split(' ', 1) + [None])[:2]
        if cmd not in ("find", "info"):
            return
        if not rest:
            return
        (term, rest) = (rest.split(' ', 1) + [None])[:2]
        if cmd == "find":
            self.real_find(irc, msg, [], term, rest)
        else:
            self.real_info(irc, msg, [], term, rest)

    def doPrivmsg(self, irc, msg):
        if chr(1) in msg.args[1]: # CTCP
            return
        if not msg.args[1]:
            return
        channel = self.__getChannel(msg.args[0])
        if not self.registryValue("enabled", channel):
            return
        user = get_user(msg)
        if channel:
            self.chanmsg(irc, msg, user)
        else:
            if user:
                return
            self.privmsg(irc, msg, user)

    def inFilter(self, irc, msg):
        if msg.command != "PRIVMSG":
            return msg
        if not conf.supybot.defaultIgnore():
            return msg
        text = msg.args[1].strip()
        if len(text) < 6:
            return msg
        user = get_user(msg)
        if user:
            return msg
        channel = self.__getChannel(msg.args[0])
        if channel:
            if text[0] not in ('!', '@'):
                return msg
            if not text[1:5] in ("info", "find"):
                return msg
#            if not hasattr(irc, 'reply'):
#                irc = callbacks.ReplyIrcProxy(irc, msg)
#            self.doPrivmsg(irc, msg)
        else:
            if text[1] in ('!', '@'):
                if text[1:5] in ("info", "find"):
                    irc = callbacks.ReplyIrcProxy(irc, msg)
                    self.doPrivmsg(irc, msg)
            elif text[:4] in ("info", "find"):
                irc = callbacks.ReplyIrcProxy(irc, msg)
                self.doPrivmsg(irc, msg)
            else:
                return msg

        return msg

Class = PackageInfo


# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
