#!/usr/bin/env python3

"""
This is a Polglot NodeServer for a Onkyo/Pioneer AVR written by TangoWhiskey1
"""
import polyinterface
import sys
import time
import logging
import ipaddress
from typing import Any

from Node_Shared import *
from AVRNode import *
from WriteProfile import write_nls, write_editors

_MIN_IP_ADDR_LEN = 8
#
#
#  Controller Class
#
#
class AVRServer(polyinterface.Controller):

    def __init__(self, polyglot):
        """
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.

         Class Variables:
        self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
        self.name: String name of the node
        self.address: String Address of Node, must be less than 14 characters (ISY limitation)
        self.polyConfig: Full JSON config dictionary received from Polyglot for the controller Node
        self.added: Boolean Confirmed added to ISY as primary node
        self.config: Dictionary, this node's Config
        """
        super(AVRServer, self).__init__(polyglot)
        # ISY required
        self.name = 'AVRServer'
        self.hb = 0 #heartbeat
        self.poly = polyglot
        self.queryON = True

        LOGGER.setLevel(logging.INFO)
        #LOGGER.setLevel(logging.DEBUG)

        LOGGER.debug('Entered init')

        # implementation specific
        self.device_nodes = dict()  #dictionary of ISY address to device Name and device IP address.
        self.configComplete = False

        polyglot.addNode(self)  #add this controller node first

    def start(self):
        """
        This  runs once the NodeServer connects to Polyglot and gets it's config.
        No need to Super this method, the parent version does nothing.
        """        
        LOGGER.info('AVR NodeServer: Started Onkyo/Pioneer AVR Polyglot Node Server  v2')
        self.server_data = self.poly.get_server_data(check_profile=True)

        # Show values on startup if desired.
        LOGGER.debug('ST=%s',self.getDriver('ST'))
        self.setDriver('ST', 1)
        self.heartbeat(0)
        
        #  Auto Find devices if nothing in config
        if (self.polyConfig["customParams"] == None) or (len(self.polyConfig["customParams"]) == 0):
            self.auto_find_devices()

        self.process_config(self.polyConfig)
        
        while not self.configComplete:
            self.addNotice({"WaitingForConfig":"Projector: Waiting for a valid user config"})
            LOGGER.info('Waiting for a valid user config')
            time.sleep(5)
            self.removeNotice("WaitingForConfig")

        # Set the nodeserver status flag to indicate nodeserver is running
        self.setDriver("ST", 1, True, True)


    def auto_find_devices(self) -> bool:
        """
        Finds the AVRs on the network
        """
        self.addNotice({"AVR discovery: Looking for devices on network, this will take few seconds"})
        new_device_found = False

        LOGGER.debug( "Looking for Onkyo/Pioneer Devices")
        devices =  Receiver.discover(timeout=5)
        LOGGER.debug(  "Controller: Found " + str( len( devices) ) + " devices:" )
        for avr in devices:
            ipAddr =avr.host
            cleaned_dev_name = self.generate_name(avr.info['model_name'],avr.info['identifier'] )
            if( cleaned_dev_name == None):
                LOGGER.error('Controller: Unable to generate key name for: ' +  avr.info['model_name'] + ' ID ' + avr.info['identifier'] )
                continue
            #See if device exists, if  not add
            if( self.getCustomParam(cleaned_dev_name) == None ):
                LOGGER.info('Adding Discovered device to config: ' + cleaned_dev_name + ' ('+ ipAddr + ')')
                self.addCustomParam(  {cleaned_dev_name : ipAddr } )
                new_device_found = True
        self.removeNotice("ControllerAutoFind")
        return new_device_found

    def generate_name(self, model_name, identifier, )->str:
        """
        Create a name for the AVR if one is found
        """
        try:
            network_device_name = model_name
            network_device_name.replace(' ','_')
            network_device_name = network_device_name+'_'+identifier[-6:]
            return network_device_name
        except Exception as ex:
            return None


    def parseConfigIP(self, addressToParse: str):
        """Make sure IP format with port"""
        try:
            port_index = addressToParse.index(':')
            if port_index < _MIN_IP_ADDR_LEN:
                return None
            port = addressToParse[port_index+1 : ]
            if not port.isnumeric():
                return None
            ip = ipaddress.IPv4Address(addressToParse[0 :port_index])
        except ValueError:
            return None
        return {'ip' : str(ip), 'port' : port }


    def process_config(self, config):
        """
        Set up the polyglot config
        """
        self.removeNoticesAll()
        LOGGER.debug('process_config called')
        LOGGER.debug(config)
        try:
            if config == None:
                LOGGER.error('Controller: Poly config not found')
                return

            if config["customParams"] == None:
                LOGGER.error('Controller: customParams not found in Config')
                return

            for devName in config["customParams"]:
                device_name = devName.strip()
                if device_name.upper() == 'LOGGING':
                    if config["customParams"][devName].strip().upper() == 'DEBUG':
                        LOGGER.setLevel(logging.DEBUG)
                        continue

                device_addr = config["customParams"][devName].strip()
                isy_addr = 's'+device_addr.replace(".","")
                if( len(isy_addr) < _MIN_IP_ADDR_LEN ):
                    LOGGER.error('Controller: Custom Params device IP format incorrect. IP Address too short:' + isy_addr)
                    continue
                self.device_nodes[isy_addr] = [device_name, device_addr]
                LOGGER.debug('AVR NodeServer: Added device_node: ' + device_name + ' as isy address ' + isy_addr + ' (' + device_addr + ')')
            
            if len(self.device_nodes) == 0:
                LOGGER.error('AVR NodeServer: No devices found in config, nothing to do!')
                return
            self.configComplete = True
            self.add_devices()
        except Exception as ex:
            LOGGER.error('AVR NodeServer: Error parsing config in the Projector NodeServer: %s', str(ex))

    def add_devices(self):
        """
        Add any devices found
        """
        LOGGER.debug('AVR NodeServer: add_devices called')
        for isy_addr in self.device_nodes.keys():
            if not isy_addr in self.nodes:
                device_name = self.device_nodes[isy_addr][0]
                device_addr = self.device_nodes[isy_addr][1]
                try:                
                    avr = Receiver(device_addr)
                    nri = avr.nri # get NRI info
                    write_nls(LOGGER,avr)
                    write_editors(LOGGER,avr)
                    avr.disconnect()
                    self.addNode( AVRNode(self, self.address, isy_addr,device_addr,  device_name) )
                except Exception as ex:
                    LOGGER.error('AVR NodeServer: Could not add device ' + device_name + ' at address ' + device_addr )
                    LOGGER.error('   +--- Could not get entries for profile.  Error: ' + str(ex))
           
    
    def shortPoll(self):
        """
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        LOGGER.debug('AVR NodeServer: shortPoll called')
        self.setDriver('ST',  1)
        for node in self.nodes:
            if node != self.address:
                self.nodes[node].shortPoll()

    def longPoll(self):
        LOGGER.debug('AVR NodeServer: longPoll')
        self.heartbeat()
        
    def heartbeat(self,init=False):
        LOGGER.debug('AVR NodeServer: heartbeat: init={}'.format(init))
        if init is not False:
            self.hb = init
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0

    def delete(self):
        """
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        LOGGER.info('AVR NodeServer: Deleting the Projector Nodeserver')

    def set_module_logs(self,level):
        logging.getLogger('urllib3').setLevel(level)

    def update_profile(self,command):
        LOGGER.debug('AVR NodeServer: update_profile called')
        st = self.poly.installprofile()
        return st
    
    def on_discover(self,command):
        """
        UI call to look fo rnew devices
        """
        dev_found = self.auto_find_devices()
        if dev_found == True:
            self.process_config(self.polyConfig)

    id = 'AVRServer'
    commands = { 
                'DISCOVER': on_discover,

    }
    drivers = [{'driver': 'ST', 'value': 1, 'uom': ISY_UOM_2_BOOL},  # Status
    ]

if __name__ == "__main__":
    try:
        poly = polyinterface.Interface('')
        poly.start()
        controller = AVRServer(poly)
        controller.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
