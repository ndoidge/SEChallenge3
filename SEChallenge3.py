#!/usr/bin/env python
__author__ = 'ndoidge'


from switch_class import switch
import argparse
import ipaddress
import sys

#Define an empty class which we will use to store the arguments from the argument parser
class args(object):
    pass


#Uses the argparse library to create command line options, and check that the required ones have been specified
def parse_args():
    #create arg parser object and add arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', help='The IP address of the switch', required=True)
    parser.add_argument('--user', help='Username to log into the switch with', required=True)
    parser.add_argument('--passwd', help='Password to log into the switch with', required=True)
    parser.add_argument('--proto', help='http or https (default is http)', choices=['http', 'https'], default='http')
    parser.add_argument('--port', help='Port number of HTTP/S service (default to port 80)', default='10180')
    parser.add_argument('--ignoreSSL', help='Ignore SSL certificate checks', action='store_false')

    #create a class of type args (which is empty)
    c = args()
    #pushes the namespace into the new class
    parser.parse_args(namespace=c)

    ipadd = ipaddress

    return c



def main(args):
    #create an instance of the switch class
    nxos = switch(args.ip, args.user, args.passwd, port=args.port, proto=args.proto, verify=args.ignoreSSL)

    #login to the switch and only proceed if the login returns successful
    if nxos.aaaLogin():
        print ('Successfully logged into the switch, beginning feature checks...')

        # variable used to track if the interface-vlan feature is enabled
        # assume it is enabled until we have checked...
        enabled = True

        #check if the interface-vlan feature is enabled
        if nxos.is_feature_enabled('fmInterfaceVlan') == False:
            enabled = False
            #if not enabled try three times to enable it
            for i in range(0, 3):
                #if the feature is enabled, then
                if nxos.enable_feature('interface-vlan'):
                    enabled = True
                    break

        if enabled == False:
            print ('Tried to enable the interface-vlan feature, but failed, exiting...')
            return 0

        """if we have got this far then the feature is (or had previously been) enabled so lets make some vlans!
        I had thought about building one big dictionary with all the VLANs I want to add, allowing a single REST call
        for all VLANS. Whilst this way is less efficient I have opted to do one at a time so you could call the
        function many times over making the structure of the function call easier
        """

        # Create the L2 Vlans
        complete = True
        for i in range (5, 255, 5):
            if nxos.create_vlan(i, 'auto-generated vlan-' + str(i)):
                pass
            else:
                print ('Failed to create VLAN ' + str(i))
                complete = False

        """This is a pain in the tits and I've given up trying to make it work properly, so got a hack in place instead.
        I will come back to it later.
        When incrementing ipaddress.ip_interface('10.0.0.1/30) it increments the host portion (and subnet if necessary) 
        however it also changes the mask to a /32. Don't know why, so instead I'm just using ipaddress.ip_address instead
        and have tweaked the switch.set_int_ipaddress() to just add on the mask... So its hard coded... I don't like it.
        """

        if complete:
            #create an ipaddress object
            ipadd = ipaddress
            mask = '30'
            incrementip = ipadd.ip_address('10.0.0.1')
            #Create SVIs for the first 10 VLANs
            for i in range(5, 55, 5):
                incrementip += 4
                nxos.create_svi(i, "{0}/{1}".format(incrementip, mask))
                #fullip = ipadd.ip_interface("{0}/{1}".format(incrementip, mask))
        else:
            print('Unable to create VLANs, exiting...')

        #All done! Logout of the switch and then delete the class instances as we dont need them anymore
        if nxos.aaaLogout():
            print ('Successfully logged out of the switch. Goodbye!')
            del ipadd
            del nxos
            return 1

        return 0




if __name__ == "__main__":
    #print(sys.version_info)
    if sys.version_info.major != 3:
        print('Error: You need Python 3 to run this script')
    else:
        main(parse_args())
