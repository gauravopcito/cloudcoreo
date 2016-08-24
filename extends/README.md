servers-base
============

## Description
This [CloudCoreo](http://www.cloudcoreo.com) repository is simply a starting point for any server. Currently, the boot process includes:

## Tags
1. Server
1. Base

## Boot scripts
1. `expand_root_fs.sh`
  - This will run a resize2fs on the root file system in order to make sure the server can 
    utilize all available space
1. `install_cloudcoreo_repo.sh`
  - This is lay down the cloudcoreo repository
1. `install_emacs.sh`
  - Emacs is a very popular tool for people who work in the linux environment
1. `install_screen.sh`
  - Screen is very helpful for window management in linux
1. `setup_python.sh`
  - ensure python-pip is installed, as well as the python package "boto" for controlling aws.

###OVERRIDE REQUIRED VARIABLES
* **NONE**

<h3>OVERRIDE OPTIONAL VARIABLES</h3>
* **NONE**
