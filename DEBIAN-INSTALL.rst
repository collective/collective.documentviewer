`Debian 9.x Plone 5.2.x & Documentviewer Setup, Author/Leonardo J. Caballero G. CTO - Covantec R.L.`

Debian Software Selection & Setup
---------------------------------

**update core system software**

1. sudo apt update && sudo apt upgrade -y

**complete install of development libraries**

1. sudo apt install -y autoconf automake libtool libpng-dev libjpeg-dev libtiff5-dev zlib1g-dev libssl-dev screen python-dev liblcms2-2 liblcms2-dev liblcms2-utils libfreetype6-dev libbz2-dev epstool poppler-utils pdftk p7zip cabextract git python-virtualenv

2. sudo gem install ruby-lsapi -v 4.2

3. sudo gem install rdoc

Install DocSplit & Dependencies
===============================

*msttcorefonts on Debian - Improves Typographic Accuracy of Documents*

msttcorefonts is a way of obtaining the Microsoft TrueType fonts on Linux.

1. sudo apt install -y ttf-mscorefonts-installer

*install GraphicsMagick*

1. sudo apt install -y graphicsmagick

*installation of Tesseract (OCR) & its dependencies*: **leptonica**
    
1. sudo apt install -y leptonica-progs libleptonica-dev

*installation of Tesseract (OCR) & its dependencies*: **tesseract**

1. sudo apt install -y tesseract-ocr libtesseract3 libtesseract-dev

*installation of Tesseract (OCR) English language package* **must be installed for OCR to work**

1. sudo apt install -y tesseract-ocr-eng

*installation of Tesseract (OCR) Spanish language package* **must be installed for OCR to work**

1. sudo apt install -y tesseract-ocr-spa tesseract-ocr-spa-old

*installation of libreoffice* **download most current version**

1. sudo apt install -y libreoffice

*installation of docsplit gem* 

1. sudo gem install docsplit
    
Installation of Plone
*********************

1. wget https://launchpad.net/plone/5.2/5.2.1/+download/Plone-5.2.1-UnifiedInstaller-r3.tgz
2. tar zxf Plone-5.2.1-UnifiedInstaller-r3.tgz
3. cd Plone-5.2.1-UnifiedInstaller-r3
4. ./install.sh zeo
5. cd /usr/local/Plone/zeocluster
6. vi buildout.cfg 
7. enter insert mode (i) add collective.documentviewer to eggs section
8. escape :wq to write changes to disk
9. run buildout ./bin/buildout

[#]_ Modify Plone User for Headless Libreoffice 
-----------------------------------------------

1. sudo usermod -G root plone 

2. ./bin/restartcluster.sh

.. [#] Warning!!!  Any program can come under attack, and probably will. By default, every process runs with the privileges of the user or process that started it. Therefore, if a user has logged on with restricted privileges, your program should run with those restricted privileges. This effectively limits the amount of damage an attacker can do, even if he successfully hijacks your program into running malicious code. Do not assume that the user is logged in with administrator privileges; you should be prepared to run a helper application with elevated privileges if you need them to accomplish a task. However, keep in mind that, if you elevate your process’s privileges to run as root, an attacker can gain those elevated privileges and potentially take over control of the whole system.
