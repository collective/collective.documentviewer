`CentOS*/RHEL 6.x Plone 4.x & Documentviewer DR - VM Setup, Author/Eric Tyrer Assoc. Director - Web Systems Group York College - City University of New York`

Prepare Cold Virtual Machine
****************************
1. launch VMSphere
2. create new VM
3. select CPU's, NIC's, storage space & strategy.
4. connect RHEL 6 iso to VM
5. start virtual machine

RHEL 6.2 Install Using GUI: Basics
----------------------------------
1. select install/upgrade system in graphical mode
2. skip media test (this is a disk image)
3. select English as Language
4. select US English as keyboard layout

Storage Method, Password, TZ, and Initialize Drive(s)
-----------------------------------------------------
1. select Basic Storage Device
2. clean disk **must be initialized**
3. select re-initialize all
4. give VM/Server a hostname
5. set timezone/location
6. create root password & verify
7. confirm installation type by selecting `use all space`
8. confirm formatting by answering affirmative within the dialog box to commit storage configuration to disk

RHEL Software Selection & Setup
-------------------------------
**under base system select:**

- base
- console internet tools
- debugging tools
- hardware monitoring utilities
- java platform
- network tools
- perl support
- ruby support
- security tools

**under servers select:**

- server platform
- system administration tools

**under system management select**

- snmp support:

**under desktops select:**

- fonts

**under development select:**

- development tools
- server platform development

**install vmware tools**
*must be initiated from within vmware center*

1. select Inventory, Guest, Install Upgrade/Install VMware Tools
2. mount disk within virtual machine
3. mount /dev/cdrom /media
4. cp /mnt/VMwareTools-* to /tmp
5. cd /tmp
6. tar zxf VMwareTools-*
7. ./vmware-tools/vmware-install.pl
8. answer all prompts to complete

**setup networking**

1. vi /etc/sysconfig/network-scripts/ifcfg-eth0
2. enter insert mode (i)
3. modify parameter ONBOOT=no to ONBOOT=yes
4. escape then :wq to write changes to disk (this vi command will quit vi for you)
5. enter setup at #prompt
6. select Network Configuration, Device Configuration, eth0 - VMware VMXNET3 Ethernet Controller
7. enter static IP assigned by network administrator
8. enter netmask 255.255.255.0
9. enter default gateway (dependent on vlan)
10. enter primary DNS 172.16.139.11 as well as secondary 172.16.139.12
11. exit setup, **saving changes** 

**register system with redhat network**

1. type setup at #prompt
2. select RHN Register
3. confirm yes or hit enter to connect to RHN
4. confirm next and then enter RHN credentials
5. select system updates (usually all apply)
6. exit when finished

**update core system software**

1. yum update -y
2. accept RHEL network keys
3. wait/go to the bathroom/lunch

**protect our repositories using yum-plugin-priorities**

The priorities plugin can be used to enforce ordered protection of repositories, by associating priorities to repositories. Packages from repositories with a lower priority will never be used to upgrade packages that were installed from a repository with a higher priority. We're going to use EPEL, REMI, and RPMForge Repos, which have the potential to screw up things. 

1. yum instal yum-plugin-priorities
2. edit the /etc/yum/pluginconf.d/priorities.conf file, ensure it contains:
    [main]
    enabled=1
3. With the plugin enabled, you may add priorities to repositories by adding the line:
    priority=N
4. for more info refer to http://wiki.centos.org/PackageManagement/Yum/Priorities

**complete install of development libraries**

1. install EPEL repository for software.
2. rpm --import https://fedoraproject.org/static/0608B895.txt
3. wget http://linux.mirrors.es.net/fedora-epel/6/i386/epel-release-6-7.noarch.rpm
4. rpm -i epel-release-6-7.noarch.rpm
5. install RPMforge (AKA RepoForge) 
6. wget http://pkgs.repoforge.org/rpmforge-release/rpmforge-release-0.5.2-2.el6.rf.x86_64.rpm
7. rpm -i rpmforge-release-0.5.2-2.el6.rf.x86_64.rpm
8. yum install -y autoconf automake libtool libpng-devel libjpeg-devel libtiff-devel zlib-devel openssl-devel screen python-devel lcms2 lcms2-devel lcms2-utils freetype-devel bzip2-devel epstool poppler-utils pdftk p7zip ruby-lsapi ruby-rdoc ttmkfdir cabextract

Install DocSplit & Dependencies
===============================
**msttcorefonts on RHEL6 / Centos6 - Improves Typographic Accuracy of Documents**

**thanks to help obtained from http://oimon.wordpress.com/2011/09/05/msttcorefonts-on-rhel6-centos-6-sl6/**

msttcorefonts is a way of obtaining the Microsoft TrueType fonts on Linux. However, version 6 release of Red Hat Enterprise Linux no longer includes a pre-requisite of msttcorefonts package, namely chkfontpath, which in turn, relies on the font server package xfs.

1. change directory to /usr/local/src
2. mkdir msttfonts and cd msttfonts
3. wget http://corefonts.sourceforge.net/msttcorefonts-2.0-1.spec

The latest version of msttcorefonts at sourceforge doesn’t cater for this, so in the meantime we can patch the spec file and build it ourselves.

Getting msttcorefonts
---------------------

4. vi msttcorefonts.rhel6.patch
5. Copy & paste the following block: 

::

 --- msttcorefonts-2.0-1.spec   2011-09-05 11:09:57.206756336 +0100
 +++ msttcorefonts-2.0-1.1.spec 2011-09-05 11:23:56.925761649 +0100
 @@ -19,8 +19,8 @@
 BuildPrereq: %{ttmkfdir}
 BuildPrereq: wget
 BuildPrereq: cabextract
 -Prereq: /usr/sbin/chkfontpath
 -Packager: Noa Resare <noa@resare.com>
 +#Prereq: /usr/sbin/chkfontpath
 +#Packager: Noa Resare <noa@resare.com>
 
 %description
 The TrueType core fonts for the web that was once available from
 @@ -152,7 +152,7 @@
 %post
 if test $1 -eq 1
 then
 -  /usr/sbin/chkfontpath --add %{fontdir}
 +  ln -s /usr/share/fonts/msttcorefonts/ /etc/X11/fontpath.d/msttcorefonts
 fi
 # something has probably changed, update the font-config cache
 if test -x /usr/bin/fc-cache
 @@ -163,7 +163,7 @@
 %preun
 if test $1 -eq 0
 then
 -  /usr/sbin/chkfontpath --remove %{fontdir}
 +  /bin/rm -f /etc/X11/fontpath.d/msttcorefonts
 fi
 
 %files

6. Write file out and save as **msttcorefonts.rhel6.patch**
7. We should have two files within /usr/local/src/msttfonts, msttcorefonts.rhel6.patch & msttcorefonts-2.0-1.spec

Patch Spec File & Build
-----------------------

8. Patch < msttcorefonts.rhel6.patch 

(Visually inspect the resulting spec file to verify that it no longer requires chkfontpath.)

*rebuild rpm package using new spec file*

9. rpmbuild -bb msttcorefonts-2.0-1.spec

*either copy new RPM to your local repo or install locally*

10. yum localinstall msttcorefonts-2.0-1.noarch.rpm

*install ruby gems*

1. cd /usr/local/src
2. wget http://production.cf.rubygems.org/rubygems/rubygems-1.8.24.tgz
3. tar zxf rubygems-1.8.24.tgz
4. cd rubygems-1.8.24
5. invoke ruby setup.rb 
6. successful install of ruby gems will result in RubyGems 1.8.24 installed returned at the # prompt

*install GraphicsMagick*

1. change directory to /usr/local/src
2. wget http://downloads.sourceforge.net/project/graphicsmagick/graphicsmagick/1.3.15/GraphicsMagick-1.3.15.tar.xz
3. tar xf GraphicsMagick-1.3.15.tar.xz
4. cd GraphicsMagick-1.3.15
5. ./configure --enable-shared --with-bzlib=yes --with-gslib=yes --with-windows-font-dir=/usr/share/fonts/msttcorefonts
6. make; make install -j4 (-j flag should equal cpu's present)

*installation of Tesseract (OCR) & its dependencies*: **leptonica**
    
1. change directory to /usr/local/src
2. wget http://leptonica.org/source/leptonica-1.68.tar.gz
3. tar xf leptonica-1.68.tar.gz
4. cd leptonica-1.38
5. ./autobuild
6. ./configure --enable-shared
7. make; make install -j4 (-j flag should equal cpu's present)

*installation of Tesseract (OCR) & its dependencies*: **tesseract**

1. wget http://tesseract-ocr.googlecode.com/files/tesseract-3.01.tar.gz
2. tar zxf tesseract-3.01.tar.gz 
3. cd tesseract-3.01
4. ./autogen.sh
5. ./configure --enable-shared
6. make; make install
7. export LD_LIBRARY_PATH=/usr/local/lib (this will give shell awareness of installed programs)

*installation of Tesseract (OCR) English language package* **must be installed for OCR to work**

1. cd /usr/local/src
2. wget http://tesseract-ocr.googlecode.com/files/tesseract-ocr-3.01.eng.tar.gz
3. cd /tesseract-ocr/tessdata
4. cp -R * /usr/local/share/tessdata/

*installation of libreoffice* **download most current version**

1. cd /usr/local/src
2. wget http://download.documentfoundation.org/libreoffice/testing/3.6.0/rpm/x86_64/LibO-Dev_3.6.0beta1_Linux_x86-64_install-rpm_en-US.tar.gz
3. tar zxf LibO-Dev_3.6.0beta1_Linux_x86-64_install-rpm_en-US.tar.gz
4. cd LibO-Dev_3.6.0beta1_Linux_x86-64_install-rpm_en-US/RPMS
5. yum install * .rpm -y
6. cd /opt
7. rename libreoffice mv lodev3.6/ libreoffice
8. symlink libreoffice with /usr/lib/libreoffice ln -s /opt/libreoffice /usr/lib/libreoffice

*installation of docsplit gem* 

1. gem install docsplit
    
Installation of Plone
*********************

1. wget https://launchpad.net/plone/4.2/4.2rc2/+download/Plone-4.2rc2-UnifiedInstaller.tgz
2. tar zxf Plone-4.2rc2-UnifiedInstaller.tgz
3. cd Plone-4.2rc2-UnifiedInstaller
4. ./install.sh zeo
5. cd /usr/local/Plone/zeocluster
6. vi buildout.cfg 
7. enter insert mode (i) add collective.documentviewer to eggs section
8. escape :wq to write changes to disk
9. rerun buildout ./bin/buildout

[#]_ Modify Plone User for Headless Libreoffice 
-----------------------------------------------
1. usermod -G root plone 
2. ./bin/restartcluster.sh

.. [#] Warning!!!  Any program can come under attack, and probably will. By default, every process runs with the privileges of the user or process that started it. Therefore, if a user has logged on with restricted privileges, your program should run with those restricted privileges. This effectively limits the amount of damage an attacker can do, even if he successfully hijacks your program into running malicious code. Do not assume that the user is logged in with administrator privileges; you should be prepared to run a helper application with elevated privileges if you need them to accomplish a task. However, keep in mind that, if you elevate your process’s privileges to run as root, an attacker can gain those elevated privileges and potentially take over control of the whole system.

