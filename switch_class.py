"""
switch_class.py - by Nick Doidge (ndoidge@cisco.com)
----------------
A basic class definition for a switch (or device). Allows you to connect to a switch using the NXAPI and 'sessions',
this maintains session information such as cookies, so you do not have to parse this info yourself. At present these
scripts assume you are using JSON to format message bodies etc. I will write extensions for XML when I can be bothered :-D

You do not need to specify arguments for the class if you are using the argparse library
    <switch_name> = switch(ip, username, password, *args, **kwargs)

You can then perform a AAA login
    <switch_name>.aaaLogin()

Now you can perform GET and POST requests with the functions:
    <switch_name>.get(<url>)
    <switch_name.post(<url>, <body>)
    ... as well as other functions. See below for details.

Note in both cases (get() and post()) the URL is the API path, not including the hostname/ IP/ port etc... i.e.
'/api/mo/sys.json?rsp-subtree=children'
The <body> argument to the POST method should be a Python dictionary

Once you are finished you can logout of the switch with
    <switch_name>.aaaLogout()

As a final clean up, delete the created class
    del <switch_name>

"""

import requests
import json
import ipaddress


__author__ = 'ndoidge'


class switch():

    def __init__(self, ip, username, password, *args, **kwargs):
        # reads option arguments provided to the function, if specified use value given, else use default (80/ http)
        port = kwargs.get('port')
        proto = kwargs.get('proto')

        # check we have been passed an IP address
        ipadd = ipaddress
        ipadd.ip_address(ip)

        self.url = '{0}://{1}:{2}'.format(proto, ip, port)
        self.username = username
        self.password = password
        self.verify = kwargs.get('verify')

        # if we are disabling SSL cert checks, then disable warnings, else we get a shit-tonne of warning messages
        if self.verify == False:
            requests.packages.urllib3.disable_warnings()

        #create the session object which allows each switch class a single session for all API calls
        self.session = requests.session()


    def aaaLogin(self):
        """aaaLogin() is used to login to the switch which details are held within the parent class. No arguments are required"""
        body = {
            "aaaUser": {
                "attributes": {
                    "name": self.username,
                    "pwd": self.password
                }
            }
        }

        # append the aaaLogin.json portion to create the full URL
        url = '/api/aaaLogin.json'

        response = self.post(url, body)

        if response.status_code != requests.codes.ok:
            return False
        else:
            return True


    def aaaLogout(self):
        """aaaLogout() is used to logout to the switch which details are held within the class. No arguments are required"""

        body = {
		    'aaaUser' : {
			    'attributes' : {
				    'name' : self.username
			    }
		    }
	    }

        #append the aaaLogout.json portion to create the full URL
        url = '/api/aaaLogout.json'

        #logout of the switch
        response = self.post(url, body)

        if response.status_code != requests.codes.ok:
            return False
        else:
            return True



    def get(self, url):
        """get(<url>) is used to issue a GET request to the switch which details are held within the class"""
        try:
            response = self.session.get('{0}{1}'.format(self.url, url), verify=self.verify)
        except requests.exceptions.RequestException:
            print('Unable to connect to {0}{1}'.format(self.url, url))
        return response


    def post(self, url, body):
        """post(<url>, <body>) is used to issue a POST request to the switch which details are held within the class.
        <url> is a string, and should not include the host/port portion, i.e. '/api/mo/sys/fm.json?rsp-subtree=full&rsp-prop-include=config-only'
        <body> is a dictionary, which is converted to json by the requests.session.post() call
        """
        try:
            response = self.session.post('{0}{1}'.format(self.url, url), json=body, verify=self.verify)
        except requests.exceptions.RequestException:
            print('Unable to connect to {0}{1}'.format(self.url, url))
        return response


    def is_feature_enabled(self, feature):
        """is_feature_enabled(<feature>) is used to issue a GET request to the switch, and returns a True if the feature
        is enabled, and False if it isnt.
        <feature> is a string, examples include 'hsrp', 'bgp', 'nxapi', 'ifvlan'
        """
        url = '/api/mo/sys/fm.json?rsp-subtree=full&rsp-prop-include=config-only'
        rx_json = self.get(url)
        rx_json = json.loads(rx_json.text)
        #print (json.dumps(rx_json, indent=4))

        feature_enabled = False
        # loop through each child element of the output, looking to match the feature name, if successful, check its enabled
        for i in range(len(rx_json['imdata'][0]['fmEntity']['children'])):
            if feature in rx_json['imdata'][0]['fmEntity']['children'][i].keys():
                if rx_json['imdata'][0]['fmEntity']['children'][i][feature]['attributes']['adminSt'] == 'enabled':
                    feature_enabled = True
                    print ('Feature \'' + feature + '\' is enabled')
                    break
        return feature_enabled


    def enable_feature(self, feature):
        """enable_feature(<feature>) enables the specified feature on the switch, this is performed using the json-rpc
        CLI calls as the DME doesnt have the ability to do it
        """
        url = '/ins'

        print ('Feature ' + feature + ' is not enabled... having to use CLI-based API to enable it... you might have to wait a while!')

        myheaders = {'content-type': 'application/json-rpc'}

        payload = [
            {
                "jsonrpc": "2.0",
                "method": "cli",
                "params": {
                    "cmd": "conf t",
                    "version": 1
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "cli",
                "params": {
                    "cmd": "feature interface-vlan",
                    "version": 1
                },
                "id": 2
            }
        ]

        response = requests.post(self.url + url, json=payload, headers=myheaders, auth=(self.username, self.password))
        if response.status_code == requests.codes.ok:
            print ('Feature ' + feature + ' is now enabled')
            return True
        else:
            return False


    def create_vlan(self, vlan, description):

        url = '/api/mo/sys/bd.json'

        payload = {
            "bdEntity": {
                "children": [{
                    "l2BD": {
                        "attributes": {
                            "fabEncap": "vlan-" + str(vlan),
                            "name": description
                        }
                    }
                }]
            }
        }

        #create the vlan and if the HTTP response is good then return 1, else return 0 to show the vlan couldnt be created
        if self.post(url, payload).status_code == requests.codes.ok:
            return 1
        else:
            return 0

    def create_svi(self, vlan, ip, state='up'):
        """create_svi(<vlan>, <ip address>, ) will create a new SVI on the switch, then assign it the specified IP
        and mask. Note the <ip> should be of type ipaddress.ip_interface
        """

        body = {
            "topSystem": {
                "children": [{
                    "interfaceEntity": {
                        "children": [{
                            "sviIf": {
                                "attributes": {
                                    "id": 'vlan{0}'.format(vlan),
                                    "adminSt": state
                                }
                            }
                        }]
                    }
                }]
            }
        }

        #print (json.dumps(body, indent=4))

        url = '/api/mo/sys.json'

        response = self.post(url, body)

        if response.status_code == requests.codes.ok:
            print('created SVIs ok, now setting IPs')
            setipresponse = self.set_int_ipaddress('vlan{0}'.format(vlan), ip)
        else:
            print (response.text)


    def set_int_ipaddress(self, intf, ip):
        """ set_int_ipaddress(<intf>, <ip>) sets an IP address for a specific interface
        <intf> examples include 'vlan101' or 'eth1/96'
        """

        body = {
            "topSystem": {
                "children": [{
                    "ipv4Entity": {
                        "children": [{
                            "ipv4Inst": {
                                "children": [{
                                    "ipv4Dom": {
                                        "attributes": {
                                            "name": "default"
                                        },
                                        "children": [{
                                            "ipv4If": {
                                                "attributes": {
                                                    "id": intf
                                                },
                                                "children": [{
                                                    "ipv4Addr": {
                                                        "attributes": {
                                                            "addr": ip
                                                        }
                                                    }
                                                }]
                                            }
                                        }]
                                    }
                                }]
                            }
                        }]
                    }
                }]
            }
        }

        url = '/api/mo/sys.json'

        #print (json.dumps(body, indent=4))

        response = self.post(url, body)
        #print(json.dumps(response.text, indent=4))
        return response



    def get_interfaces(self, intf_type):

        url = '/api/mo/sys/intf.json?rsp-subtree=children'
        response = switch_get(url)

        interfaces = []

        if response.status_code != requests.codes.ok:
            print ('Error, unable to GET interface config. Error Code: ' + str(rx_code))
            rx_json = json.loads(response.text)
            print ('\tError msg:\t' + rx_json['imdata'][0]['error']['attributes']['text'])
        else:
            # load JSON into python type(dict)
            rx_json = json.loads(response.text)

            # loop through every interface instance
            for intf in range(len(rx_json['imdata'][0]['interfaceEntity']['children'])):
                # Check every interface for the type we want, if it matches, add it to the list of interfaces
                # important it is converted into a string, because it is unicode in native format
                if intf_type in rx_json['imdata'][0]['interfaceEntity']['children'][intf].keys():
                    interfaces.append(
                        str(rx_json['imdata'][0]['interfaceEntity']['children'][intf]['l1PhysIf']['attributes']['id']))

        return interfaces