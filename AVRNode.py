#
#
#  Onkyo AVR Node Class
#
#

## Stop, and AM to 0

import traceback
import time
import polyinterface
from OnkyoCore import eISCP,  Receiver
from  Node_Shared import *


def message_received(message, data):
    """
        Recieves the raw messages from the AVR
        This filters out a lot of messages not needed 
        by the the node
    """
    try:
        # LOGGER.debug("raw Received message: " + message)
        if message[0:3] == 'FLD': #fl diplay information - shows what is on the disply, so not useful here
            return
        if message[0:3] == 'NJA':  # gives a bitmap of the album cover, so not useful here
            return
        if type(data) is AVRNode:
            data.avrDataReceived( message)
    except Exception as e:
         LOGGER.error("Raw receive error on message " + message + ' - ' + e )

class AVRNode(polyinterface.Node):
    """
    Class Variables:
    self.primary: String address of the Controller node.
    self.parent: Easy access to the Controller Class from the node itself.
    self.address: String address of this Node 14 character limit. (ISY limitation)
    self.added: Boolean Confirmed added to ISY
    """

    #####################################################
    #region - Start Up
    ##
    ##  Functions handle getting things set up and started
    ##
    #####################################################

    def __init__(self, controller, primary, isy_address, device_address, device_name):
        #You do NOT have to override the __init__ method, but if you do, you MUST call super.
        super(AVRNode, self).__init__(controller, primary, isy_address, device_name)
        LOGGER.debug("Node: Init Node " + device_name + " ("+ device_address + ")")

        #set Node specific values
        self.queryON = True
        self.avr = Receiver(device_address)
        self.avr.on_message = message_received
        self.avr.message_data = self
        #####################################################
        #region - Map Arrays 
        ## These arrays  map ISY index values to the AVR command value
        ## The arrays MUST be in same order as the strings in the 
        ## nls file.  Nls goes from string user sees to ISY index 
        # these convert the ISY index to the AVR command
        #####################################################
        self._lmd_options = [
            '00', '01', '02', '03', '04', '05', '06', '07', '08', 
            '09', '0A', '0B', '0C', '0D', '0E', '0F', '11', '12', 
            '13', '14', '15', '16', '1F', '23', '25', '26', '2E', 
            '40', '41', '42', '43', '44', '45', '50', '51', '52', 
            '80', '81', '82', '83', '84', '85', '86', '87', '88',
            '89', '8A', '8B', '8C', '8D',  '8E','8F', '90', '91',
            '92', '93', '94', '95', '96',  '97','98', '99', '9A',
            'A0', 'A1',  'A2','A3', 'A4',  'A5','A6', 'A7', 'FF',
            'UP', 'DOWN', 'MOVIE', 'MUSIC', 'GAME', 'THX', 'AUTO',
            'SURR', 'STEREO', 'N/A', 'UNKNOWN',
        ]

        # NSV
        self._net_service_names = None  # dynamcially filled in start
        # Input selector
        self._sli_options = None # dynamcially filled in start

        self._ntc_options = [
            'PLAY', 'STOP', 'PAUSE', 'P/P', 'TRUP', 'TRDN', 'REPEAT',
            'RANDOM', 'REP/SHF', 'DISPLAY', 'RIGHT', 'LEFT', 'UP',
            'DOWN', 'SELECT', '0', '1', '2', '3', '4', '5', '6', '7',
            '8', '9', 'DELETE', 'CAPS', 'RETURN', 'CHUP', 'CHDN', 'MENU',
            'TOP', 'MODE', 'LIST', 'MEMORY', 'F1',  'F2','N/A', 'UNKNOWN',
        ]


        self._nst_play_options    = ['S', 'P', 'p', 'F', 'R', 'E', 'N/A','UNKNOWN',]
        self._nst_repeat_options  = ['-', 'R', 'F', '1', 'x', 'N/A','UNKNOWN',]
        self._nst_shuffle_options = ['-', 'S', 'A', 'F', 'x', 'N/A','UNKNOWN',]        
        self._ltn_options   = [ '00','01', '02', '03', 'UP', 'N/A','UNKNOWN'] #late night mode
        self._pwr_options   = [ '00','01', 'ALL','N/A','UNKNOWN'] #power
        self._amt_options   = [ '00','01', 'TG','N/A','UNKNOWN'] #muting
        self._osd_options   = [ 'MENU','UP','DOWN','RIGHT','LEFT','ENTER','EXIT','AUDIO','VIDEO','HOME','QUICK','IPV','N/A','UNKNOWN']  #On Screen
        self._onOff_options = [ 'OFF', 'ON','UNKNOWN']
        self._yesNo_options = [ 'NO', 'YES','UNKNOWN']

        """
        Since updating the driver (or status) variables is very slow  in Polyglot2, one needs to make his own copy to know where
        they are.
        """
        self._my_drivers = {  
                'ST': 0,    'GV1': 0,  'GV2': 0,  'GV3': 0,  'GV4': 0,  'GV5': 0,  'GV6': 0,  'GV7': 0,  'GV8': 0,  'GV9': 0, 'GV10': 0,  
                'GV11': 0, 'GV12': 0, 'GV13': 0, 'GV14': 0, 'GV15': 0, 'GV16': 0, 'GV17': 0, 'GV18': 0, 'GV19': 0,  'GV20': 0,   
        }
        #endregion - Map Arrays 

        # Messages for the UI to gie the user some feedback
        self.__MSG_INDEX_GOOD = 0
        self.__MSG_INDEX_OFFLINE=1
        self.__MSG_INDEX_NA = 2
        self.__MSG_INDEX_UNKNOWN = 3
        self.__MSG_INDEX_VALUE = 4
        self.__MSG_INDEX_SERVICE_NOT_SUPPORTED = 5

        LOGGER.debug("Node: Leaving Init")

    def start(self):
        """
        This method is run once the Node is successfully added to the ISY
        and we get a return result from Polyglot. Only happens once.
        """
        LOGGER.debug('Node: Start called for node ' + self.name + ' (' + self.address + ')')
        self.avr.nri # expensive to get then cached, so get it early
        
        #get the names that are in the AVR, then add the couple of entries used 
        # by the nodein the UI to indicate errors or power off states
        self._net_service_names = self.avr.networkServiceNamesSortedById()
        self._net_service_names.append('N/A')
        self._net_service_names.append('UNKNOWN')
        self._sli_options = self.avr.selectorSortedById()
        self._sli_options.append('N/A')
        self._sli_options.append('UNKNOWN')
        self.updateStatuses() 

    def stop( self):  # TODO
        self.avr.disconnect()
        self.avr = None

    #endregion - Start Up

    #####################################################
    #region - Polling and Statuses
    ##
    ##  Functions that handle polling, messsage handling
    #  and updating statuses
    ##
    #####################################################

    def shortPoll(self):
        self.updateStatuses()

    def avrDataReceived(self, message):
        """
        Updates the UI based on the messages coming in.  This makes it so the UI responds
        regardless of how the message is genreated, at the device, ISY, or another program
        """
        #LOGGER.debug("AVR Node Received A Message: " + message)
        #LOGGER.debug('Statuses: '+ str(self._my_drivers) )
        avrMsg = message[0:3]
        if   avrMsg == 'PWR': self.showMessageStatus(message, 'ST',   self. _pwr_options,      3, None, 'N/A', self.__MSG_INDEX_UNKNOWN)
        elif avrMsg == 'MVL': self.showMessageStatus(message, 'GV1',  None,                    3, None,    0,  self.__MSG_INDEX_UNKNOWN, self.adjustVolume )
        elif avrMsg == 'SLI': self.showMessageStatus(message, 'GV2',  self._sli_options,       3, None, 'N/A', self.__MSG_INDEX_UNKNOWN, self.adjustSelectorIndex)
        elif avrMsg == 'AMT': self.showMessageStatus(message, 'GV3',  self._amt_options,       3, None, 'N/A', self.__MSG_INDEX_UNKNOWN, self.adjustToNaOnPowerOff )
        elif avrMsg == 'LMD': self.showMessageStatus(message, 'GV4',  self._lmd_options,       3, None, 'N/A', self.__MSG_INDEX_UNKNOWN, self.adjustToNaOnPowerOff )
        elif avrMsg == 'LTN': self.showMessageStatus(message, 'GV5',  self._ltn_options,       3, None, 'N/A', self.__MSG_INDEX_UNKNOWN, self.adjustToNaOnPowerOff )
        elif avrMsg == 'TUN': self.showMessageStatus(message, 'GV15', None,                    3, None,     0, self.__MSG_INDEX_UNKNOWN, self.adjustTunerFreq )
        elif avrMsg == 'PRS': self.showMessageStatus(message, 'GV8',  None,                    3, None,     0, self.__MSG_INDEX_UNKNOWN, self.adjustToInt )
        elif avrMsg == 'TPD': self.showMessageStatus(message, 'GV9',  None,                    4,   -4,     0, self.__MSG_INDEX_UNKNOWN, self.adjustToInt)
        elif avrMsg == 'NLT': self.showMessageStatus(message, 'GV11', self._net_service_names, 3,    5, 'N/A', self.__MSG_INDEX_UNKNOWN, self.adjustServiceName )
        elif avrMsg == 'NST': self.showPlayStatus(message)  # sets GV12, GV13, and GV14

    def updateStatuses(self):
        """
        Just sends a update request.  avrDataReceived updates the UI when the request is responded to
        """
        LOGGER.debug('Node: updateStatuses() called for  %s (%s)', self.name, self.address)
        try :
            self.avr.send('PWRQSTN')  #Play Status (Play/Pause/Stop) *
            self.avr.send('SLIQSTN')  #Play Status (Play/Pause/Stop) *
            self.avr.send('NSTQSTN')  #Play Status (Play/Pause/Stop) *
            self.avr.send('NLTQSTN')  #List Tile Information (Service playing) *
            self.avr.send('TPDQSTN')  #Temp Query
            self.avr.send('AMTQSTN')  #Mute Query
            self.avr.send('LMDQSTN')  #Listening Mode Query
            self.avr.send('LTNQSTN')  #Late Night Mode Query
            self.avr.send('PRSQSTN')  #Preset Query
            self.avr.send('TUNQSTN')  #Tuner Query
            self.avr.send('MVLQSTN')  #volume Query
            self.SetUserMessage(self.__MSG_INDEX_GOOD)  #GV10
        except Exception as ex :
            LOGGER.error('Node: updateStatuses: %s', str(ex))
            LOGGER.error('Node: updateStatuses: %s', traceback.format_exc())
            self.SetUserMessage(self.__MSG_INDEX_UNKNOWN)
    #endregion - Polling and Statuses

    #####################################################
    #region - Command Handlers
    ##
    ##  Functions that sending  the commands to the AVR
    ##
    #####################################################

    def on_DON(self, command):
        self.avrSendCommand('power', 'on')
        
    def on_DOF(self, command):
        self.avrSendCommand('power', 'off')
    
    def on_Query(self, command):
        LOGGER.debug('Node: On_Query() called')
        self.resetStatusElements()
        self.updateStatuses()

    def  on_VolUp(self, command):
        self.avrSendCommand('MVL', 'level-up')

    def  on_VolDown(self, command):
        self.avrSendCommand('MVL', 'level-down')

    def  on_MuteOn(self, command):
        self.avrSendCommand('AMT', 'on')

    def  on_MuteOff(self, command):
        self.avrSendCommand('AMT', 'off')

    def  on_TunerUp(self, command):
        self.avr.send('TUNUP')  #scans and can take  while, so timeouts a lot.  This just send

    def  on_TunerDown(self, command):
        self.avr.send('TUNDOWN') #scans and can take  while, so timeouts a lot.  This just send

    def  on_PresetUp(self, command):
        self.avrSendCommand('PRS', 'up')

    def  on_PresetDown(self, command):
        self.avrSendCommand('PRS', 'down')

    def  on_SetMasterVol(self, command):
        self.avrSendCommandNumber(command, 'MVL')

    def  on_SetLateNightMode(self, command):
        self.avrSendCommandFromOptions( command, 'LTN', self._ltn_options,'GV5' )

    def  on_SetAMTuner(self, command):
        self.avrSetTunerDirect('AM', self.getValueFromCommand(command) )

    def  on_SetFMTuner(self, command):
        self.avrSetTunerDirect('FM', self.getValueFromCommand(command) )

    def  on_SetPreset(self, command):
        self.avrSendCommandNumber(command, 'PRS','GV8')

    def  on_LMDCommmand(self, command):
        self.avrSendCommandFromOptions( command, 'LMD', self._lmd_options, 'GV4' )

    def on_NTCCommmand(self, command):
        try:
            isy_index = int(self.getValueFromCommand(command))
            parm = self._ntc_options[isy_index]
            avr_cmd = 'NTC' + parm
            LOGGER.debug('Node:sending net command of ' + avr_cmd )
            self.avr.send(avr_cmd)
        except Exception as ex :
            LOGGER.error('  +-- Exception sending NTC commmand: %s', str(ex))
            LOGGER.error('  +-- list is: %s', str(self._ntc_options))
            self.SetUserMessage(self.__MSG_INDEX_UNKNOWN)

    def on_NSVCommmand(self, command):
        """
        Sets the network service to be used.  The list of 
        services is kept in the AVR, so cannot use the 
        generic functions and fixed arrays.
        """

        #Uses raw send since no responce comes when the 
        #selector is not on a network source. Avoids timeouts
        
        name = '<blank>'
        try:
            isy_index = int(self.getValueFromCommand(command))
            name  = self._net_service_names [isy_index]
            cmd_id =  self.avr.networkServicesNameToId(name)
            avr_cmd = 'NSV' + cmd_id + '0'
            LOGGER.debug('Node:sending net NSV command of ' + avr_cmd )
            self.avr.send(avr_cmd)
        except Exception as ex :
            LOGGER.debug('Node:failure setting to service ' + name + ': ' + str(ex) )
            self.SetUserMessage(self.__MSG_INDEX_SERVICE_NOT_SUPPORTED)


    def  on_SetInputSel(self, command):
        """
        Sets the input selection based on the ISY index
        Since this is one of the dynamic paramaters taken
        from the AVR, it needs a special step in going
        from the ISY index to the command ID
        """

        name = '<blank>'
        try:
            isy_index = int(self.getValueFromCommand(command))
            name  = self._sli_options [isy_index]
            cmd_id =  self.avr.selectorNameToId(name)
            avr_cmd = 'SLI' + cmd_id
            LOGGER.debug('Node:sending SLI command: ' + avr_cmd )
            self.avr.send(avr_cmd)
        except Exception as ex :
            LOGGER.debug('Node:failure setting service to ' + name + ': ' + str(ex) )
            self.SetUserMessage(self.__MSG_INDEX_SERVICE_NOT_SUPPORTED)

    def  on_OSDCommmand(self, command):
        """
        Sends a command to control the menus and setup options
        These do not respond back, so use raw send
        """
        try:
            isy_index = int(self.getValueFromCommand(command))
            parm = self._osd_options[isy_index]
            avr_cmd = 'OSD' + parm
            LOGGER.debug('Node:sending OSD command: ' + avr_cmd )
            avrResponse = self.avr.send(avr_cmd)
        except Exception as ex:
            LOGGER.error('Error sending OSD command: %s', str(ex))
            self.SetUserMessage( self.__MSG_INDEX_UNKNOWN)

    #endregion - Command Handlers

    #####################################################
    #region - Low Level Query Functions
    ##
    ##  Queries AVR and returns data
    ##
    #####################################################
    def showMessageStatus( self, message, isyDriver, responseOptions, startDataParseIndex = 3, stopDataParseIndex =None,  defaultIsyState = 'UNKNOWN', defaultUserMessage = 3, dataAdjuster = None ):  # 3= UNKNOWN
        """
        Turns the raw message parameter into an ISY UI index, that is, the index in the select list defined in en_us.txt
        The reponse_options must be a list that maps the message data to the UI, so exactly the same order and num elements
        if  reponse_options is not given, then convert the value to a number
        """
        data = None
        try:
            if len(message)  <  4:
                raise ValueError( 'Bad message for status: ' + str(message))
            data = message[startDataParseIndex:stopDataParseIndex]
            if dataAdjuster:
                data = dataAdjuster(data)
            index = data
            if  responseOptions:
                index = responseOptions.index(data)
            self.mySetDriver(isyDriver, index)
            LOGGER.debug('Status Parse: %s  with data %s set to index  %s', message[0:3],str(data),str(index))
        except Exception as ex :
            LOGGER.error('  +-- Exception parsing msg %s: %s',message,  str(ex))
            data = defaultIsyState
            if  responseOptions:
                data = responseOptions.index(defaultIsyState)
            self.mySetDriver(isyDriver, data ) 
            self.SetUserMessage(defaultUserMessage)
        finally:
            return data
    
    def showPlayStatus(self, message):
        """
        Gets the play status and sets the three UI elements
        """
        play_index    = 99
        repeat_index  = 99
        shuffle_index = 99
        try:
            if len(message) <  6:
                raise ValueError( 'Bad NST message: ' + str(message))
            play_index    = self._nst_play_options.index( message[3])
            repeat_index  = self._nst_repeat_options.index( message[4])
            shuffle_index = self._nst_shuffle_options.index( message[5])
            self.mySetDriver('GV12', play_index) # play state
            self.mySetDriver('GV13', repeat_index) # repeat state
            self.mySetDriver('GV14', shuffle_index) # shuffle state
            LOGGER.debug('Status Parse: %s with play indices= P-%s R-%s, S-%s', str(message), str(play_index), str(repeat_index), str(shuffle_index))
        except Exception as ex :
            LOGGER.error('  +-- Exception parsing NST message  to indices: %s', str(ex))
            self.mySetDriver('GV12', self._nst_play_options.index('N/A')) # play state
            self.mySetDriver('GV13', self._nst_repeat_options.index('N/A')) # repeat state
            self.mySetDriver('GV14', self._nst_shuffle_options.index('N/A')) # shuffle state
            self.SetUserMessage(self.__MSG_INDEX_UNKNOWN)

    #endregion - Queries

    #####################################################
    #region - Adjusters
    ##
    ##  Message Data Adjusters.  These are functions 
    ##  passed into the general response handing function
    ##  that allows specific manipulaiton for that message
    ##
    #####################################################
    def adjustTunerFreq(self, value):
        """
        Adjusts from number given by AVR to what the UI
        expects.  divides by 100 for FM, and straight
        number for AM
        """
        try:
            if value.isnumeric() == False:
                LOGGER.debug('Non Numeric Freq' + value)
                return 0

            # GV2 is the index into the array the UI uses
            isyIndex =  self.myGetDriver('GV2')
            inputName = self._sli_options[isyIndex]

            if inputName == 'FM':
                LOGGER.debug('Adjusting FM Freq')
                fm_freq = float(value)/100.0
                self.mySetDriver('GV7', fm_freq)
                return fm_freq
            if inputName == 'AM':
                LOGGER.debug('Adjusting AM Freq')
                am_freq = int(value)
                self.mySetDriver('GV6', am_freq)
                return am_freq
            else:
                return 0
        except Exception as ex:
            LOGGER.error('Adjusting Freq exception:' + str(ex))
            return 0

    def adjustServiceName(self, value):
        """
        Gets the actual command code from the AVR itself
        since this command is one of the ones dynamically
        changed based on what the user has named the 
        input and what the AVR supports
        """
        if self.myGetDriver('ST') != 1:
            return 'N/A'
        return self.avr.networkServicesIdToName(value) 

    def adjustSelectorIndex(self, value):
        """
        Gets the actual command code from the AVR itself
        since this command is one of the ones dynamically
        changed based on what the  AVR supports
        """
        return self.avr.selectorIdToName(value) 

    def adjustToNaOnPowerOff(self, value):
        """
        Show N/A when the power is off
        used because many commands just don't respond
        when AVR is in standby. so this way the UI
        is not left in the last state forever
        """
        if self.myGetDriver('ST')  != 1:
            return 'N/A'
        return value

    def adjustToInt(self, value):
        """
        converts a sting to an int for index based
        commands
        """
        if self.myGetDriver('ST')  != 1:
            return 0
        return int(value)

    def adjustVolume(self, value):
        """
        Converts AVR hex based volume to 
        ISY decimal based number
        """
        vol = 0
        try:
            vol = int(value,16)  #AVR returns hex value
        except ValueError: # not a valid hex string
            LOGGER.error( "invalid hex volume")
        return vol
        

    #endregion - Adjusters

    #####################################################
    #region - Low Level Command Sending Functions
    ##
    ##  Sends commands to AVR
    ##
    #####################################################
    def avrSendCommandFromOptions(self, isyCommand, avrCommandtoSend, avrCommandOptions, statusVar = None, zone ='main' ):
        """
        Converts and ISY command into command the AVR understands, sends it, and checks the reponse to make 
        sure it is valid.
        This is for commands that are strings
        If there is a status (driver) set up in ISY for the value, it updates that as well
        """
        ret = ('','',0)  # tuple of command sent, response, and index for response (if applicable)
        try:
            isy_index = int(self.getValueFromCommand(isyCommand))
            parm = avrCommandOptions[isy_index]
            response = self.avrSendCommand( avrCommandtoSend, parm, statusVar, zone)
            if response[0] == avrCommandtoSend:
                ret =(response[0],response[1],avrCommandOptions.index(response[1]))
            return ret
        except Exception as ex:
            LOGGER.error('avrSendCommandFromOptions: %s', str(ex))
            self.SetUserMessage( self.__MSG_INDEX_UNKNOWN)
            return ret

    def avrSendCommandNumber(self, isyCommand, avrCommandtoSend, statusVar = None, zone='main'):
        """
        Converts and ISY command into command the AVR understands, sends it, and checks the reponse to make 
        sure it is valid.
        THis is for commands that are integers
        If there is a status (driver) set up in ISY for the value, it updates that as well
        """
        try:
            parm = int(self.getValueFromCommand(isyCommand))
            return self.avrSendCommand( avrCommandtoSend, parm, statusVar, zone)

        except Exception as ex:
            LOGGER.error('avrSendCommandNumber: %s', str(ex))
            self.SetUserMessage( self.__MSG_INDEX_UNKNOWN )
            return  ('','',0)  # tuple of command sent, response, and index for response (if applicable)

    def avrSendCommand(self, avrCommandtoSend, parm, statusVar = None, zone='main'):
        """
        Sends a command to the AVR and checks the response to make sure it is valid
        """
        ret = ('','',0)  # tuple of command sent, response, and index for response (if applicable)
        try:
            LOGGER.debug('Node:sending command %s %s', avrCommandtoSend, parm)
            avrResponse = self.avr.command(avrCommandtoSend,parm, zone )
            LOGGER.debug('  +-- command response %s', avrResponse)
            self.updateStatuses()
            if (len( avrResponse) == 4) and ( avrResponse[2] == avrCommandtoSend ):
                ret = (avrResponse[2], avrResponse[3], '')
                if  ret[1] == 'N/A':
                    self.SetUserMessage( self.__MSG_INDEX_NA)
                    if statusVar != None:   #Status query return setting, so this will set it to NA unitl next poll, giving user some feedback
                        LOGGER.debug('+--  %s overriding status to N/A',avrCommandtoSend)
                        self.mySetDriver(statusVar, ret[2]) 
            return ret
        except Exception as ex:
            LOGGER.error('avrSendCommand: %s', str(ex))
            self.SetUserMessage( self.__MSG_INDEX_UNKNOWN)
            return ret

    def avrSetTunerDirect(self, band, freq ):
        """
        Band: AM or FM
        From Onkyo Doco: Ex: FM 100.55 MHz(50kHz Step) Direct Tuning is [!1SLI24][!1TUNDIRECT][!1TUN1][!1TUN0][!1TUN0][!1TUN5][!1TUN5]	
        The direct tune commands do not return info, so must use send
        """
        try:
            tuner = 'SLI24' #FM Tuner
            if band == 'AM':
                tuner = 'SLI25'#AM Tuner

            freqAsString = str(freq)
            self.avr.raw(tuner)  
            self.avr.send('TUNDIRECT') 
            for char in freqAsString:
                if char.isdigit() == False:
                    continue
                time.sleep(0.25)
                self.avr.send('TUN'+ char)
        except Exception as ex:
            self.SetUserMessage( self.__MSG_INDEX_UNKNOWN)
            LOGGER.error('SetTunerDirect: %s', str(ex))
    #endregion - Commands

    #####################################################
    #region - Helpers
    ##
    ##  Helper functions
    ##
    #####################################################
    def getValueFromCommand(self, isyCommand):
        """
        returns the value of the command the ISY sends back for its commands
        This assumes there is only one command needed (i.e only one item in the nodedefs under the main command)
        """
        ic = isyCommand.get('query')
        res = list(ic.keys())[0]  #get first key, should only be one
        return ic.get(res)

    def SetUserMessage( self, msgIndex):
        """
        This updates the UI with a message for the user.  
        It is designed to give a little feedback, but gets 
        blanked out each short poll
        """
        self.mySetDriver('GV10', msgIndex) 

    def resetStatusElements(self):
        """
        Clears all the UI elements.  They will gradually get repopulated
        as messages come in from the AVR
        """
        LOGGER.debug('Node: Clearing Status Elements')
        self.mySetDriver('ST',  self._pwr_options.index('UNKNOWN') )
        self.mySetDriver('GV1', 0)  # Master Vol
        self.mySetDriver('GV2', self._sli_options.index('UNKNOWN')) # Input select
        self.mySetDriver('GV3', self._amt_options.index('UNKNOWN')) # mute
        self.mySetDriver('GV4', self._lmd_options.index('UNKNOWN')) # 
        self.mySetDriver('GV5', self._ltn_options.index('UNKNOWN')) # Late Night Mode
        self.mySetDriver('GV15', 0) # tuner Freq
        self.mySetDriver('GV8', 0) # Preset
        self.mySetDriver('GV9', 0) # temp
        self.mySetDriver('GV11', self._net_service_names.index('UNKNOWN')) # net service playing
        self.mySetDriver('GV12', self._nst_play_options.index('UNKNOWN')) # play state
        self.mySetDriver('GV13', self._nst_repeat_options.index('UNKNOWN')) # repeat state
        self.mySetDriver('GV14', self._nst_shuffle_options.index('UNKNOWN')) # shuffle state

    def mySetDriver(self, driver, value):
        """
        Since updating the driver (or status) variables is very slow
        in Polyglot2, one needs to make his own copy to know where
        they are.  This is a very simple setter to do this
        """
        self._my_drivers[driver]= value
        self.setDriver( driver, value) 
        pass

    def myGetDriver(self, driver):
        """
        Since updating the driver (or status) variables is very slow
        in Polyglot2, one needs to make his own copy to know where
        they are.  This is a very simple getter to do this
        """
        return self._my_drivers[driver]

    #endregion - Helpers

    #####################################################
    #region - ISY Drivers and Commands
    ##
    ##  ISY Command and Status Lookup Info
    ##
    #####################################################
    drivers = [{'driver': 'ST',  'value': 0, 'uom': ISY_UOM_25_INDEX        },      # Status = Power On State
               {'driver': 'GV1', 'value': 0, 'uom': ISY_UOM_100_BYTE        },      # Master Vol
               {'driver': 'GV2', 'value': 0, 'uom': ISY_UOM_25_INDEX        },      # Input select
               {'driver': 'GV3', 'value': 0, 'uom': ISY_UOM_25_INDEX        },      # Mute
               {'driver': 'GV4', 'value': 0, 'uom': ISY_UOM_25_INDEX        },      # Listining Mode
               {'driver': 'GV5', 'value': 0, 'uom': ISY_UOM_25_INDEX        },      # Late Night Mode
               {'driver': 'GV6', 'value': 0, 'uom': ISY_UOM_56_RAW          },      # AM Tuner Freq
               {'driver': 'GV7', 'value': 0, 'uom': ISY_UOM_56_RAW          },      # FM Tuner Freq
               {'driver': 'GV8', 'value': 0, 'uom': ISY_UOM_56_RAW          },      # Preset
               {'driver': 'GV9', 'value': 0, 'uom': ISY_UOM_17_TEMP_F       },      # Temp
               {'driver': 'GV10', 'value': 0, 'uom': ISY_UOM_25_INDEX       },      # User Messages
               {'driver': 'GV11', 'value': 0, 'uom': ISY_UOM_25_INDEX       },      # Net Status
               {'driver': 'GV12', 'value': 0, 'uom': ISY_UOM_25_INDEX       },      # Net Play 
               {'driver': 'GV13', 'value': 0, 'uom': ISY_UOM_25_INDEX       },      # Net repeat
               {'driver': 'GV14', 'value': 0, 'uom': ISY_UOM_25_INDEX       },      # Net shuffle
               {'driver': 'GV15', 'value': 0, 'uom': ISY_UOM_56_RAW          },      # Tuner Freq
              ]  

    id = "AVRNode"
    commands = {
                    'DON'     : on_DON,
                    'DOF'     : on_DOF,
                    'UPDATE'  : on_Query,
                    "BRT"     : on_VolUp,
                    "DIM"     : on_VolDown,
                    "AMT_ON"  : on_MuteOn,
                    "AMT_OFF" : on_MuteOff,
                    "TUN_U"   : on_TunerUp,
                    "TUN_D"   : on_TunerDown,
                    "TUNC"    : on_NTCCommmand,
                    "PRS_U"   : on_PresetUp,
                    "PRS_D"   : on_PresetDown,
                    "MVL"     : on_SetMasterVol,
                    "SLI"     : on_SetInputSel,
                    "LTN"     : on_SetLateNightMode,
                    "TUNA"    : on_SetAMTuner,
                    "TUNF"    : on_SetFMTuner,
                    "PRS"     : on_SetPreset,
                    "OSD"     : on_OSDCommmand,
                    "LMD"     : on_LMDCommmand,
                    "NSV"     : on_NSVCommmand,
}
#endregion - ISY Drivers and Commands

