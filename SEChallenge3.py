#!/usr/bin/env python
__author__ = 'ndoidge'


from switch_class import switch, credentials
import argparse

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
    parser.add_argument('--proto', help='HTTP or HTTPS (default is HTTP)', choices=['HTTP', 'HTTPS'], default='HTTP')
    parser.add_argument('--port', help='Port number of HTTP/S service (default to port 80)', default='10180')
    parser.add_argument('--ignoreSSL', help='Ignore SSL certificate checks', action='store_false')

    #create a class of type args (which is empty)
    c = args()
    #pushes the namespace into the new class
    parser.parse_args(namespace=c)

    return c



def main(args):
    #create an instance of the switch class
    switch_credentials = credentials(args.ip, args.user, args.passwd, port=args.port, proto=args.proto, verify=args.ignoreSSL)
    nxos = switch(switch_credentials)

    #login to the switch and only proceed if the login returns successful
    if nxos.aaaLogin():
        print 'Successfully logged into the switch, beginning feature checks...'
        enabled = True #variable used to track if the interface-vlan feature is enabled

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
            print 'Tried to enable the interface-vlan feature, but failed, exiting...'
            return 0

        #if we have got this far then the feature is (or had previously been) enabled so lets make some vlans!
        #I had thought about building one big dictionary with all the VLANs I want to add, allowing a single REST call
        #for all VLANS. Whilst this way is less efficient I have opted to do one at a time so you could call the
        #function many times over making the structure of the function call easier

        for i in range (5, 255, 5):
            if nxos.create_vlan(i, 'auto-generated vlan-' + str(i)):
                print 'Created VLAN ' + str(i)
            else:
                print 'Failed to create VLAN ' + str(i)

        if nxos.aaaLogout():
            print 'Successfully logged out of the switch. Goodbye!'
            del details
            del nxos



if __name__ == "__main__":
    main(parse_args())
