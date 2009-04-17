This plugin allows package lookup via apt-cache/apt-file

--Setup--
supybot.plugins.PackageInfo.aptdir:
Directory to use to store the apt cache (Global)
Default: ''

Create a new empty directory that will be used for the apt cache.
In this directory, you create sources.list files for every release you
want to search. The name of the file is important, since the filename (without
the .list suffix) is the name that is used to refer to the release.
The .list file should contain _both_ the deb and deb-src source lines.
Eg:
deb http://archive.ubuntu.com/ubuntu jaunty main restricted universe multiverse
deb-src http://archive.ubuntu.com/ubuntu jaunty main restricted universe multiverse

supybot.plugins.PackageInfo.defaultRelease:
Set this to the default release to use when none is specified. (Channel)
Default: ''

Whenever you create a new .list file, it is important to run the update_apt
and update_apt_file scripts that comes with this plugin. Before you run these,
you have to edit them to point to your apt dir. It's also useful to run them
periodically from cron (say, once per week for update_apt and once per moth for
update_apt_file). You also need to reload the plugin to make it pick up the new
releases.

supybot.plugins.PackageInfo.enabled:
Enable or disable package lookup snarfing. (Channel)
Default: True

supybot.plugins.PackageInfo.prefixchar:
Prefix character for the package lookup snarfer. (Channel)
Default: !

--Usage--
find <package/filename> [<release>]
Search for <package> or, of that fails, find <filename>'s package(s).
Optionally in <release>

info <package> [<release>]
Lookup information for <package>, optionally in <release>

if supybot.plugins.PackageInfo.enabled is True the bot will also reply to
the commands if prefixed with supybot.plugins.PackageInfo.prefixchar.
