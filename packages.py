###
# Copyright (c) 2006-2007 Dennis Kaarsemaker
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
import exceptions
import warnings
warnings.filterwarnings("ignore", "apt API not stable yet", exceptions.FutureWarning)
import commands, os, apt, urllib
from email import FeedParser

def component(arg):
    if '/' in arg: return arg[:arg.find('/')]
    return 'main'

class Apt:
    def __init__(self, plugin):
        self.aptdir = plugin.registryValue('aptdir')
        self.distros = []
#        self.urls = {}
        self.plugin = plugin
        self.log = plugin.log
        os.environ["LANG"] = "C"
        if self.aptdir:
            self.distros = [x[:-5] for x in os.listdir(self.aptdir) if x.endswith('.list')]
#            urls = [x for x in os.listdir(self.aptdir) if x.endswith(".url")]
#            for urlf in urls:
#                self.readIrl(urlf)
            self.distros.sort()
            self.aptcommand = """apt-cache\\
                                 -o"Dir::State::Lists=%s/%%s"\\
                                 -o"Dir::etc::sourcelist=%s/%%s.list"\\
                                 -o"Dir::State::status=%s/%%s.status"\\
                                 -o"Dir::Cache=%s/cache"\\
                                 -o"APT::Architecture=i386"\\
                                 %%s %%s""" % tuple([self.aptdir]*4)
            self.aptfilecommand = """apt-file -s %s/%%s.list -c %s/apt-file/%%s -l search %%s""" % (self.aptdir, self.aptdir)

    def find(self, pkg, checkdists, filelookup=True):
        _pkg = ''.join([x for x in pkg.strip().split(None,1)[0] if x.isalnum() or x in '.-_+'])
        distro = checkdists
        if len(pkg.strip().split()) > 1:
            distro = ''.join([x for x in pkg.strip().split(None,2)[1] if x.isalnum() or x in '.-_+'])
        if distro not in self.distros:
            return "%s is not a valid distribution: %s" % (distro, ", ".join(self.distros))
        pkg = _pkg

        data = commands.getoutput(self.aptcommand % (distro, distro, distro, 'search -n', pkg))
        #self.log.info("command output: %r" % data)
        if not data:
            if filelookup:
                data = commands.getoutput(self.aptfilecommand % (distro, distro, pkg)).split()
                #self.log.info("command output: %r" % ' '.join(data))
                if data:
                    if data[0] == 'sh:': # apt-file isn't installed
                      self.log.error("apt-file is not installed")
                      return "Please use http://packages.ubuntu.com/ to search for files"
                    if data[0] == 'E:': # No files in the cache dir
                      self.log.error("Please run the 'update_apt_file' script")
                      return "Cache out of date, please contact the administrator"
                    if data[0] == "Use" and data[1] == "of":
                        url = "http://packages.ubuntu.com/search?searchon=contents&keywords=%s&mode=&suite=%s&arch=any" % (urllib.quote(pkg), distro)
                        return url
                    if len(data) > 5:
                        return "File %s found in %s (and %d others)" % (pkg, ', '.join(data[:5]), len(data)-5)
                    return "File %s found in %s" % (pkg, ', '.join(data))
                return 'Package/file %s does not exist in %s' % (pkg, distro)
            return "No packages matching '%s' could be found" % pkg
        pkgs = [x.split()[0] for x in data.split('\n')]
        if len(pkgs) > 5:
            return"Found: %s (and %d others)" % (', '.join(pkgs[:5]), len(pkgs) -5)
        else:
            return "Found: %s" % ', '.join(pkgs[:5])

    def info(self, pkg, checkdists):
        if not pkg.strip():
            return ''
        _pkg = ''.join([x for x in pkg.strip().split(None,1)[0] if x.isalnum() or x in '.-_+'])
        distro = checkdists
        if len(pkg.strip().split()) > 1:
            distro = ''.join([x for x in pkg.strip().split(None,2)[1] if x.isalnum() or x in '-._+'])
        if not distro:
            distro = checkdists
        if distro not in self.distros:
            return "%r is not a valid distribution: %s" % (distro, ", ".join(self.distros))

        checkdists = distro

        pkg = _pkg

        for distro in [checkdists]:
            data = commands.getoutput(self.aptcommand % (distro, distro, distro, 'show', pkg))
            data2 = commands.getoutput(self.aptcommand % (distro, distro, distro, 'showsrc', pkg))
            if not data or 'E: No packages found' in data:
                continue
            maxp = {'Version': '0'}
            packages = [x.strip() for x in data.split('\n\n')]
            for p in packages:
                if not p.strip():
                    continue
                parser = FeedParser.FeedParser()
                parser.feed(p)
                p = parser.close()
                if type(p) == type(""):
                    self.log.error("apt returned an error, do you have the deb-src URLs in %s.list?" % distro)
                    return "Package lookup faild"
                if not p.get("Version", None):
                    continue
                if apt.VersionCompare(maxp['Version'], p['Version']) < 0:
                    maxp = p
                del parser
            maxp2 = {'Version': '0'}
            packages2 = [x.strip() for x in data2.split('\n\n')]
            for p in packages2:
                if not p.strip():
                    continue
                parser = FeedParser.FeedParser()
                parser.feed(p)
                p = parser.close()
                if type(p) == type(""):
                    self.log.error("apt returned an error, do you have the deb-src URLs in %s.list?" % distro)
                    return "Package lookup faild"
                if not p['Version']:
                    continue
                if apt.VersionCompare(maxp2['Version'], p['Version']) < 0:
                    maxp2 = p
                del parser
            archs = ''
            if maxp2.has_key('Architecture'):
                if maxp2['Architecture'] not in ('all','any'):
                    archs = ' (Only available for %s)' % maxp2['Architecture']
            maxp["Distrobution"] = distro
            return("%s (source: %s): %s. In component %s, is %s. Version %s (%s), package size %s kB, installed size %s kB%s%s" %
                   (maxp['Package'], maxp['Source'] or maxp['Package'], maxp['Description'].split('\n')[0], component(maxp['Section']),
                    maxp['Priority'], maxp['Version'], distro, int(maxp['Size'])/1024, maxp['Installed-Size'], archs, self.getUrl(maxp)))
        return 'Package %s does not exist in %s' % (pkg, checkdists)
                       
    @staticmethod
    def readUrl(urlfile):
        distro = os.path.splitext(urlfile)[0]
        url = None
        try:
            assert distro in self.distros, '%s is not a valid distrobution (no .list file)' % distro
            f = open(os.path.join(self.aptdir, urlfile))
            lines = [i.strip() for i in f.readlines() if i.strip()]
            assert len(lines) == 1, 'Expected 1 line in "%s", read %d' % (urlfile, len(lines))
            self.urls[distro] = lines[0]
        except Exception, e:
            self.plugin.log.warning("%s (%s)" % (e.__class__, e))

    def getUrl(self, maxp):
        if not maxp["Distrobution"] in self.urls:
            return ""
        return " - see %s" % (self.urls[maxp["Distrobution"]] % maxp)

# Simple test
if __name__ == "__main__":
    import sys
    argv = sys.argv
    argc = len(argv)
    if argc == 1:
        print "Need at least one arg"
        sys.exit(1)
    if argc > 3:
        print "Only takes 2 args"
        sys.exit(1)
    class FakePlugin:
        class FakeLog:
            def error(*args, **kwargs):
                pass
        def __init__(self):
            self.log = self.FakeLog()
        def registryValue(self, *args, **kwargs):
            return "/home/jussi/bot/aptdir"

    command = argv[1].split(None, 1)[0]
    try:
        lookup = argv[1].split(None, 1)[1]
    except:
        print "Need something to lookup"
        sys.exit(1)
    dists = "hardy"
    if argc == 3:
        dists = argv[2]
    plugin = FakePlugin()
    aptlookup = Apt(plugin)
    if command == "find":
        print aptlookup.find(lookup, dists)
    else:
        print aptlookup.info(lookup, dists)

