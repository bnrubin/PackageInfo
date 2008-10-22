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

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('PackageInfo', True)
    enabled = yn("Enable the pugin", default=True)
    if not enabled:
        PackageInfo.enabled.setValue(enabled)
        PackageInfo.aptdir.setValue('')
        PackageInfo.prefixchar.setValue('!')
        PackageInfo.defaultRelease.setValue("hardy")
        return
    aptdir = something("Where should the apt directory be? (<botdir>/data/apt for example)")
    output("This value should be different from the bots default reply character")
    prefixchar = something("What character should the bot respond to?", default='!')
    defaultRelease = expect("Default release to use when none is specified",
            possibilities=['dapper', 'feisty', 'gutsy', 'hardy', 'intrepid'],
            default='hardy')
    PackageInfo.enabled.setValue(enabled)
    PackageInfo.aptdir.setValue(aptdir)
    PackageInfo.prefixchar.setValue(prefixchar)
    PackageInfo.defaultRelease.setValue(defaultRelease)


PackageInfo = conf.registerPlugin('PackageInfo')
conf.registerChannelValue(PackageInfo, 'enabled',
    registry.Boolean(True, "Enable package lookup"))
conf.registerChannelValue(PackageInfo, 'prefixchar',
    conf.ValidPrefixChars('!', "Character the bot will respond to"))
conf.registerChannelValue(PackageInfo, 'defaultRelease',
    registry.String('', "Default release to use when none is specified"))
conf.registerGlobalValue(PackageInfo, 'aptdir',
    registry.String('', "Path to the apt directory", private=True))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
