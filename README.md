# Onkyo/Pioneer AVR Node Server for Polyglot V2

This allows an Onkyo or Pioneer AVR to be interfaced to the ISY. It should work with any AVR that supports the Onkyo EISCP protocol

It supports 
* Power on/off
* Changing volume levels
* Turning mute on/off
* Changing the input selected
* Setting the tuners to a specific frequency
* Using the tuner presets
* Controlling network stations such as Spotify or Pandora
* Controlling the setup menus and options (Called OSD, for On Screen Display)
* Set Late Night Mode
* Set the Listening Mode

## Installation
Recommended:
* Install the nodeserver form the store<br>
* Use the find button on the base node to find the AVR(s)<br>

Manual:<br>
The best way to add a device is by using the query button on the nodeserver.  However, if you prefer to manually add an AVR, add a custom configuration entry with the appropriate Device ID and the IP address (IPV4). The format is:

Key: DeviceID  - AVR Model + last 6 digits of the Device Numeric ID, an underscore between the two.  The easiest way to determine this is to browse to the device web page and look at the friendly name given to it.  For example, if the Friendly Name is <i>Pioneer VSX-LX303 EF4503</i> then the key will be <i>VSX-LX303_EF4503</i><br>
Value 192.168.1.1  - the IP address of the device

Example:
Key: VSX-LX303_EF4503<br>
Value: 192.168.1.1

To remove a device from your system, delete the corresponding name/address entry in the Custom Configuration Parameter area of the nodeserver Configuration.

## Source
The bulk of the Onkyo work was done by miracke2k in his onkyo-eiscp project (https://github.com/miracle2k/onkyo-eiscp).

## Release Notes
v0.1 - Initial release.  
* Only the main zone is supported in this.  It is all I use, so if you use multiple zoned and really want it, drop me a note and let me know.  We can probably work something out. 😊
* I tested the services and options I have on my AVR. There are nicer and newer units than mine.  So if you find something that does not work on yours, let me know. But know that in doing so you are volunteering to be the guinea pig used to test any changes.
* There is a known incompatibility with the UD Mobile app v0.6.8.  This should be resolved in the next release of the app.
