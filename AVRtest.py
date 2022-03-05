import time
from OnkyoEiscp import Receiver, iscp_to_command


def findDevices():
    print( "Looking for Onkyo/Pioneer Devices")
    devices =  Receiver.discover(timeout=2)
    print( "Found:")
    for avr in devices:
        print( avr.info['model_name'], "with ID of ",avr.info['identifier'], "at IP address of ", avr.host )
    if len( devices) > 0:
        return ( devices[0].info['model_name'], devices[0].info['identifier'], devices[0].host)
    else:
        return [ {"","",""}]
    

def message_received(message):
    try:
        command = iscp_to_command(message)
        print("Received:", message, command)
    except ValueError:
        print("Received unparsable message:", message)

def DoCommands(receiver):
    power_state = receiver.command('power query')
    if 'off' in power_state[1]:
        receiver.command('power', 'on')
    sli = receiver.getSelectorIDfromMappedName("Roku")
    receiver.command('input-selector', sli.get('sli_name'), zone=sli.get('zone'))
    receiver.command('master-volume', '40') 



if __name__=="__main__":
    #dev = findDevices()
    #name = dev[0]
    #ip = dev[2]
    name = 'Rx'
    ip = '192.168.3.220'
    print( "Connecting  to ",name, "at", ip)
    try:
        receiver = Receiver(ip)
        receiver.on_message = message_received
        DoCommands(receiver)
        while True:
            time.sleep(5)

    except KeyboardInterrupt:
        print( 'Keyboard interrupt received')
        #receiver.command('power off')
        receiver.command('power', 'off')
    finally:
        print( 'Disconnecting ...')
        receiver.disconnect()
