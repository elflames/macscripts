#!/usr/bin/env python

import urllib2
from tempfile import mkstemp
from shutil import move, rmtree
from os import remove, close, path, rename, umask, symlink, unlink, walk, makedirs
import subprocess
import math
import time
import argparse
import re

parser = argparse.ArgumentParser(description='Installs and configures Puppet on OS X')
parser.add_argument('--server', help='The URL of the Puppet Server. Defaults to puppet.grahamgilbert.dev')
parser.add_argument('--certname', help='The certname of the client. Defaults to client.grahamgilbert.dev')
parser.add_argument('--serial', action='store_true', help='Use the Mac\'s serial number as the certname')
parser.add_argument('--clean_serial', action='store_true', help='Use the Mac\'s serial number as the certname, with aaa prepended to it if the first character is a digit.')
parser.add_argument('--appendhosts', action='store_true', help='If using with the Vagrant-based Puppet Master, appends the hosts file with the default IP address')
args = vars(parser.parse_args())

if args['server']:
    puppetserver = args['server']
else:
    puppetserver = 'puppet.grahamgilbert.dev'
def downloadChunks(url):
    """Helper to download large files
        the only arg is a url
       this file will go to a temp directory
       the file will also be downloaded
       in chunks and print out how much remains
    """

    baseFile = path.basename(url)

    #move the file to a more uniq path
    umask(0002)

    try:
        temp_path='/tmp'
        file = path.join(temp_path,baseFile)

        req = urllib2.urlopen(url)
        total_size = int(req.info().getheader('Content-Length').strip())
        downloaded = 0
        CHUNK = 256 * 10240
        with open(file, 'wb') as fp:
            while True:
                chunk = req.read(CHUNK)
                downloaded += len(chunk)
                print math.floor( (downloaded / total_size) * 100 )
                if not chunk: break
                fp.write(chunk)
    except urllib2.HTTPError, e:
        print "HTTP Error:",e.code , url
        return False
    except urllib2.URLError, e:
        print "URL Error:",e.reason , url
        return False

    return file

def internet_on():
    try:
        response=urllib2.urlopen(puppetserver,timeout=1)
        return True
    except urllib2.URLError as err: pass
    return False

def chown_r(path):
    makedirs(path)
    the_command = "chown -R root:wheel "+path
    serial = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
    the_command = "chmod -R 777 "+path
    serial = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

if internet_on:
    if args['certname']:
        certname = args['certname']
    else:
        certname = 'client.grahamgilbert.dev'

    if args['serial']:
        the_command = "ioreg -c \"IOPlatformExpertDevice\" | awk -F '\"' '/IOPlatformSerialNumber/ {print $4}'"
        serial = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
        serial = re.sub(r'\s', '', serial)
        # remove the silly characters that VMware likes to put in occasionally
        serial = serial.replace("+", "")
        serial = serial.replace("/", "")
        certname = serial.lower()

    if args['clean_serial']:
        the_command = "ioreg -c \"IOPlatformExpertDevice\" | awk -F '\"' '/IOPlatformSerialNumber/ {print $4}'"
        serial = subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]
        serial = re.sub(r'\s', '', serial)
        # remove the silly characters that VMware likes to put in occasionally
        serial = serial.replace("+", "")
        serial = serial.replace("/", "")
        if serial[0].isdigit():
            serial = "aaa"+serial
        certname = serial.lower()

    if args['appendhosts']:
        with open("/etc/hosts", "a") as myfile:
            myfile.write("192.168.33.10 puppet.grahamgilbert.dev")


    # import errno
    #
    # def force_symlink(file1, file2):
    #     try:
    #         symlink(file1, file2)
    #     except OSError, e:
    #         if e.errno == errno.EEXIST:
    #             # is it a directory? If not, remove the symlink
    #             if path.islink(file2):
    #                 unlink(file2)
    #             else:
    #                 rmtree(file2)
    #             symlink(file1, file2)
    # see if we're running 10.9
    import platform
    v, _, _ = platform.mac_ver()
    v = float('.'.join(v.split('.')[:2]))
    # if we are, check if the java dir is symlinked
    print v
    if v == 10.8:
        print 'Installing json_pure gem'
        the_command = '/usr/bin/gem install json_pure'
        p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.wait()

    if path.isdir('/var/lib/puppet'):
        print "Binning old Puppet installation"
        rmtree('/var/lib/puppet')
    if path.isdir('/etc/puppet'):
        rmtree('/etc/puppet')
    print "Downloading Hiera"
    the_dmg = downloadChunks("http://downloads.puppetlabs.com/mac/hiera-1.2.1.dmg")
    print "Mounting Hiera DMG"
    the_command = "/usr/bin/hdiutil attach "+the_dmg
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(10)
    #install it
    print "Installing Hiera"
    the_command = "/usr/sbin/installer -pkg /Volumes/hiera-1.2.1/hiera-1.2.1.pkg -target /"
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(20)
    print "Downloading Facter"
    the_dmg = downloadChunks("http://downloads.puppetlabs.com/mac/facter-1.7.5.dmg")
    print "Mounting Facter DMG"
    the_command = "/usr/bin/hdiutil attach "+the_dmg
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(10)
    #install it
    print "Installing Facter"
    the_command = "/usr/sbin/installer -pkg /Volumes/facter-1.7.5/facter-1.7.5.pkg -target /"
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(20)
    print "Downloading Puppet"
    the_dmg = downloadChunks("http://downloads.puppetlabs.com/mac/puppet-3.4.2.dmg")
    ##mount the dmg
    print "Mounting Puppet DMG"
    the_command = "/usr/bin/hdiutil attach "+the_dmg
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(10)
    print "Installing Puppet"
    the_command = "/usr/sbin/installer -pkg /Volumes/puppet-3.4.2/puppet-3.4.2.pkg -target /"
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p.wait()
    time.sleep(20)
    print "Ejecting Puppet"
    the_command = "hdiutil eject /Volumes/puppet-3.4.2"
    subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    print "Ejecting Facter"
    the_command = "hdiutil eject /Volumes/facter-1.7.5"
    subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    print "Ejecting Hiera"
    the_command = "hdiutil eject /Volumes/hiera-1.2.1"
    subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    data = "[main]\npluginsync=true\nssldir=/var/lib/puppet/ssl\n\n[master]\n# These are needed when the puppetmaster is run by passenger\n# and can safely be removed if webrick is used.\nssl_client_header = SSL_CLIENT_S_DN \nssl_client_verify_header = SSL_CLIENT_VERIFY\npluginsync=true\n\n[agent]\nserver="+puppetserver+"\ncertname="+certname+"\nreport=true\npluginsync=true"
    the_command = "/usr/bin/touch /etc/puppet/puppet.conf"
    p=subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    print "writing the puppet configuration"
    file = open("/etc/puppet/puppet.conf", "w")
    file.write(data)
    file.close()

    # print "Setting Permissions"
    # chown_r("/var/lib/puppet")
    # chown_r("/var/lib/facter")

    # print 'Correcting the permissions Facter messes up'
    # the_command = "chown root:wheel /var/lib"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    # print 'Repairing permissions'
    # the_command = "mkdir /var/lib/puppet"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    # the_command = "chmod 777 /var/lib/puppet"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    # the_command = "chmod 777 /etc/puppet"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    # the_command = "puppet resource group puppet ensure=present"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]

    # the_command = "puppet resource file /etc/puppet/ssl ensure=present mode=0775"
    # subprocess.Popen(the_command,shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate()[0]    
    print "All done!"
