# -*- Encoding: utf-8 -*-
###
# Copyright (c) 2008-2010 Terence Simpson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
###

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    def makeSource(release):
        return """deb http://archive.ubuntu.com/ubuntu/ %s main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu/ %s main restricted universe multiverse
"""

    from supybot.questions import output, expect, anything, something, yn
    import os
    conf.registerPlugin('PackageInfo', True)

    enabled = yn("Enable this plugin in all channels?", default=True)

    if enabled and advanced:
        prefixchar = something("Which prefix character should be bot respond to?", default=PackageInfo.prefixchar._default)
        defaultRelease = something("What should be the default distrobution when not specified?", default=PackageInfo.defaultRelease._default)
        aptdir = something("Which directory should be used for the apt cache when looking up packages?", default=supybot.directories.data.dirize('aptdir'))

        # People tend to thing this should be /var/cache/apt
        while aptdir.beginswith('/var'):
            output("NO! Do not use your systems apt directory")
            aptdir = something("Which directory should be used for the apt cache when looking up packages?", default=supybot.directories.data.dirize('aptdir'))

    else:
        prefixchar = PackageInfo.prefixchar._default
        defaultRelease = PackageInfo.defaultRelease._default
        aptdir = supybot.directories.data.dirize('aptdir')


    PackageInfo.enabled.setValue(enabled)
    PackageInfo.aptdir.setValue(aptdir)
    PackageInfo.prefixchar.setValue(prefixchar)
    PackageInfo.defaultRelease.setValue(defaultRelease)

    default_dists = set(['hardy', 'jaunty', 'karmic', 'lucid', 'maveric'])
    pluginDir = os.path.abspath(os.path.dirname(__file__))
    update_apt = os.path.join(pluginDir, 'update_apt')
    update_apt_file = os.path.join(pluginDir, 'update_apt_file')

    default_dists.add(defaultRelease)

    for release in default_dist:
        filename = os.path.join(aptdir, "%s.list" % release)
        try:
            output("Creating %s" % filename)
            fd = fileutils.open(filename)
            fd.write("# Apt sources list for Ubuntu %s\n" % release)
            fd.write(makeSource(release))
            fd.write(makeSource(release + '-security'))
            fd.write(makeSource(release + '-updates'))
            fd.close()

            for sub in ('backports', 'proposed'):
                release = "%s-%s" % sub
                filename = os.path.join(aptdir, "%s.list" % release)
                output("Creating %s" % filename)
                fd = fileutils.open(filename)
                fd.write("# Apt sources list for Ubuntu %s\n" % release)
                fd.write(makeSource(release))
                fd.close()
        except Exception, e:
            output("Error writing to %r: %r (%s)" % (filename, str(e), type(e)))

    if yn("In order for the plugin to use these sources, you must run the 'update_apt' script, do you want to do this now?", default=True):
        os.environ['DIR'] = aptdir # the update_apt script checks if DIR is set and uses it if it is
        (e, o) = commands.getstatusoutput(update_apt)
        if e != 0:
            output("There was an error running update_apt, please run '%s -v' to get more information" % update_apt)

    (e, o) = commands.statusoutput('which apt-file')
    if e != 0:
        output("You need to install apt-file in order to use the !find command of this plugin")
    else:
        if yn("In order for the !find command to work, you must run the 'update_apt_file' script, do you want to do this now?", default=True):
            os.environ['DIR'] = aptdir # the update_apt_file script checks if DIR is set and uses it if it is
            (e, o) = commands.getstatusoutput(update_apt_file)
            if e != 0:
                output("There was an error running update_apt_file, please run '%s -v' to get more information" % update_apt_file)

PackageInfo = conf.registerPlugin('PackageInfo')
conf.registerChannelValue(PackageInfo, 'enabled',
    registry.Boolean(True, "Enable package lookup"))
conf.registerChannelValue(PackageInfo, 'prefixchar',
    conf.ValidPrefixChars('!', "Character the bot will respond to"))
conf.registerChannelValue(PackageInfo, 'defaultRelease',
    registry.String('lucid', "Default release to use when none is specified"))
conf.registerGlobalValue(PackageInfo, 'aptdir',
    conf.Directory(conf.supybot.directories.data.dirize('aptdir'), "Path to the apt directory", private=True))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:
