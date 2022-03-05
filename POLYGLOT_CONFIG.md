The best way to add a device is by using the query button on the nodeserver.  However, if you prefer to manually add an AVR, add a custom configuration entry with the appropriate Device ID and the IP address (IPV4). The format is:

Key: DeviceID  - AVR Model + last 6 digits of the Device Numeric ID, an underscore between the two.  The easiest way to determine this is to browse to the device web page and look at the friendly name given to it.  For example, if the Friendly Name is <i>Pioneer VSX-LX303 EF4503</i> then the key will be <i>VSX-LX303_EF4503</i><br>
Value 192.168.1.1  - the IP address of the device

Example:
Key: VSX-LX303_EF4503<br>
Value: 192.168.1.1

To remove a device from your system, delete the corresponding name/address entry in the Custom Configuration Parameter area of the nodeserver Configuration.