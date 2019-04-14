''' This is a restructuring of the Dynammo system, fixture functions will now be
class-based because I'm trying to be a civilized person'''

import os
import yaml
import sys
import colorsys
import socket
import json
import atexit

########################Basic Socket Functions##################################

#Oour local IP address, tells server where to send data back to
ipSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    ipSock.connect(('10.255.255.255', 1))
    localIP = ipSock.getsockname()[0]
except:
    localIP = '127.0.0.1'
ipSock.close()

socket.setdefaulttimeout(15)

def transmit(command, controller):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (fadecandyIPs[controller], 8000)
    sock.connect(server_address)
    message = json.dumps(command)
    try:
        sock.sendall(message.encode())
    except Exception as e:
        if type(e) == socket.timeout:
            print('Socket timed out, attempting connection again')
        else:
            print('Sending ' + command['type'] + ' failed')
            print(e)
    finally:
        sock.shutdown(socket.SHUT_RDWR)
        sock.close()

def recieve():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (localIP, 8800)
    sock.bind(server_address)
    sock.listen(1)
    connection, client_address = sock.accept()
    message = ''
    while True:
        data = connection.recv(16).decode()
        message += data
        if data:
            pass
        else:
            return message
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()

#####################opcBridge Companion Functions##############################

def requestArbitration(controller):
    transmit({'type': 'requestArbitration', 'ip': localIP}, controller)
    arbitration = recieve()
    arbitration = json.loads(arbitration)
    return arbitration

def setArbitration(setting, controller):
    transmit({'type': 'setArbitration', 'setting': setting}, controller)

def sendMultiCommand(commands, controller=False):
    '''Sends a command that issues an absoluteFade to multiple fixtures at once
    This should be used every time more than one command is supposed to happen simultaneously
    it is more efficent for opcBridge, faster, and less error prone'''
    #('type': 'multiCommand', 'commands': [[fixture1, rgb1, fadeTime1], [fixture2, rgb2, fadeTime2]])
    #Index 0 in each command can be fixture or index, but should be index by the time it reaches opcBridge
    for c in commands:
        if isinstance(c[0], Fixture):
            controller = c[0].controller
            #if c[0].controller != controller:
            #    print('You just tried to send one command to multiple controllers, get your lazy ass in gear and make that possible')
            #    return False
            c[0] = c[0].indexrange
        elif isinstance(c[0], int):
            c[0] = [c[0], c[0] + 1]
        elif not isinstance(c[0], list):
            print('Failed to send command, %s should either be a fixture or a list', c[0])
            return False
    command = {'type':'multiCommand', 'commands':commands}
    transmit(command, controller)

def sendCommand(indexrange, rgb, fadetime=5, type='absoluteFade', controller=False):
    #typical command
    #{'type': 'absoluteFade', 'index range': [0,512], 'color': [r,g,b], 'fade time': 8-bit integer}
    command = {'type':'absoluteFade', 'color':rgb, 'fade time': fadetime, 'index range': indexrange}
    transmit(command, controller)

def rippleFade(fixture, rgb, rippleTime=5, type='wipe'):
    sleepTime = rippleTime / (fixture.indexrange[1] - fixture.indexrange[0])
    #0.06s currently represents the minimum time between commands that opcBridge can handle on an RPI3
    #if sleepTime < .06:
    #    sleepTime = .06
    for index in range(fixture.indexrange[0], fixture.indexrange[1]):
        sendCommand([index, index + 1], rgb, fadetime=.9, controller=fixture.controller)
        time.sleep(sleepTime)

def dappleFade(fixture, rgb, fadetime=5):
    indexes = list(range(fixture.indexrange[0], fixture.indexrange[1]))
    sleepTime = fadetime / (fixture.indexrange[1] - fixture.indexrange[0])
    #0.06s currently represents the minimum time between commands that opcBridge can handle on an RPI3
    #if sleepTime < .06:
    #    sleepTime = .06
    while indexes:
        index = indexes.pop(random.randrange(0, len(indexes)))
        fadeTime = 1.5 * random.randrange(8, 15) * .1
        sendCommand([index, index + 1], rgb, fadetime=fadetime, controller=fixture.controller)
        time.sleep(sleepTime)

def exitReset(controllerList):
    for c in controllerList:
        setArbitration(False, c)
    print('Cleaning Sockets')

def gatherControllers(room):
    controllerList = []
    for l in room:
        if l.system == 'Fadecandy':
            if l.controller not in controllerList:
                controllerList.append(l.controller)
    for c in controllerList:
        setArbitration(True, c)
    atexit.register(exitReset, controllerList)
    return controllerList

def gatherArbitration(controllerList):
    if controllerList:
        for c in controllerList:
            if not requestArbitration(c):
                return False
        return True
    else:
        return True

############################Hue Control Object##################################

hueBridge = Bridge(hueIP)

def rgbToHue(RGB):
    '''Converts rgb color to the specific format that Hue API uses'''
    #colorsys takes values between 0 and 1, PIL delivers between 0 and 255
    R = RGB[0] / 255
    G = RGB[1] / 255
    B = RGB[2] / 255
    #Makes standard HSV
    hsv = colorsys.rgb_to_hsv(R, G, B)
    #Converts to Hue api HSV
    hsv_p = [int(hsv[0] * 360 * 181.33), int(hsv[1] * 255), int(hsv[2] * 255)]
    return hsv_p

def hueToRGB(hsvHue):
    hue = hsvHue[0] / 65278.8
    sat = hsvHue[1] / 255
    val = hsvHue[2] / 255

    rgbTMP = colorsys.hsv_to_rgb(hue, sat, val)

    rgbOut = [rgbTMP[0] * 255, rgbTMP[1] * 255, rgbTMP[2] * 255]

    return rgbOut

#####################Color manipulation functions###############################

def clamp(value, lower, upper):
    #Returns lower if value is below bounds, returns upper if above, returns value if inside
    return min((max(value, lower), upper))

def grbFix(grb):
    '''returns a grb list as an rgb list'''
    return [grb[1], grb[0], grb[2]]

def rgbRGBW(rgb):
    max = max(rgb)
    rgbwOut = [0,0,0,0]
    if not max:
        return rgbwOut

    multiplier = 255 / max
    hR = rgb[0] * multiplier
    hG = rgb[1] * multiplier
    hB = rgb[3] * multiplier

    M = max(hR, max(hG, hB))
    m = min(hR, min(hG, hB))
    luminance = ((M + m) / 2.0 - 127.5) * (255 / 127.5) / multiplier

    rgbwOut[0] = rgb[0] - luminance
    rgbwOut[1] = rgb[1] - luminance
    rgbwOut[2] = rgb[2] - luminance
    rgbwOut[3] = luminance

    for i in rgbwOut:
        i = clamp(i, 0, 255)
    return rgbwOut

def cctRGB(kelvin):
    outR, outG, outB = 0, 0, 0
    temp = kelvin / 100.0
    if temp <= 66:
        outR = 255
        outG = 99.4708025861 * math.log(temp - 10) - 161.1195681661
        if temp <= 19:
            outB = 0
        else:
            outB = 138.5177312231 * math.log(temp - 10) - 305.0447927307
    else:
        outR = 329.698727446 * math.pow(temp - 60, -0.1332047592)
        outG = 288.1221695283 * math.pow(temp - 60, -0.0755148492)
        outB = 255

    outR = clamp(outR, 0, 255)
    outG = clamp(outG, 0, 255)
    outB = clamp(outB, 0, 255)

    return [outR, outG, outB]

##################Begin Fixture Patching Process################################

roomDict = {'all': [], 'relays': []}
fixtureDict = []


class Fixture:
    '''Basic lighting object, can easily push colors to it, get status, and
    other control functions'''
    def __init__(self, patchDict):
        self.name = patchDict['name']
        self.system = patchDict['system']
        self.room = testDict(patchDict, 'room', 'UNUSED')
        self.colorCorrection = testDict(patchDict, 'colorCorrection', [1, 1, 1])

        #Get us a directory of fixtures by name
        fixtureDict[self.name] = self

        #Get us a directory of fixutres by room
        if self.room in roomDict:
            roomDict[self.room].append(self)
        else:
            roomDict[self.room] = [self]

    def colorCorrect(self, rgb):
        '''Returns a corrected value for the specific fixture to use'''
        tempList =  [self.colorCorrection[0] * rgb[0],
                    self.colorCorrection[1] * rgb[1],
                    self.colorCorrection[2] * rgb[2]]
        return tempList


class Fadecandy(Fixture):
    '''WS28** control over fadecandy processor. Commands all tie to opcBridge.py
    included in this project. These fixtures are exclusively RGB or GRB'''
    def __init__(self, patchDict):
        Fixture.__init__(self, patchDict)
        self.indexRange = testDict(patchDict, 'indexrange', [0,0])
        self.grb = testDict(patchDict, 'grb', True)
        self.controller = patchDict['controller']

    def __repr__(self):
        stringOut = ''
        stringOut += self.name
        stringOut += '\nType: %s' % self.system
        stringOut += '\nRoom: %s' % self.room
        stringOut += '\nIndexes: %s' % self.indexrange
        stringOut += '\nController: %s' % self.controller
        return(stringOut)

    def setColor(self, rgb, fadeTime):
        rgb = self.colorCorrect(rgb)
        if self.grb:
            rgb = grbFix(rgb)
        command = {'type': 'absoluteFade', 'color': rgb, 'fade time': fadeTime, 'index range': self.indexRange}
        transmit(command, self.controller)

    def returnCommand(self, rgb, fadeTime):
        '''Generates the command needed to set color for this fixutre, called by
        a room function to build a multiCommand for the server'''
        rgb = self.colorCorrect(rgb)
        if self.grb:
            rgb = grbFix(rgb)
        command = {'type': 'absoluteFade', 'color': rgb, 'fade time': fadeTime, 'index range': self.indexRange}
        return command

    def off(self, fadeTime):
        '''Turns the fixture off in specified time'''
        self.setColor([0, 0, 0], fadeTime)

    def on(self, fadeTime):
        '''Turns fixture on to default value in specified time'''
        #TODO: handle default values for fadecandy fixtures
        pass

    def getValue():
        pass

    def fadeUp(self, increaseAmount):
        pass

    def fadeDown(self, decreaseAmount):
        pass





class Hue(Fixture):
    '''Expensive phillips hue fixtures. Can be color or just white, all of these
    communicate through the pHue library and use a bridge on the network'''
    def __init__(self, patchDict):
        Fixture.__init__(self, patchDict)
        self.color = testDict(patchDict, 'color', True)
        self.id = testDict(patchDict, 'id', 0)

    def __repr__(self):
        stringOut = ''
        stringOut += self.name
        stringOut += '\nType: %s' % self.system
        stringOut += '\nRoom: %s' % self.room
        stringOut += '\nID: %s' % self.id
        return(stringOut)

    def setColor(self, rgb, fadeTime):
        rgb = self.colorCorrect(rgb)
        rgb = rgbToHue(rgb)
        command = {'hue': rgb[0], 'sat': rgb[1], 'bri': rgb[2], 'transitiontime': fadeTime * 10, 'on': True}
        hueBridge.set_light(self.id, command)

    def off(self, fadeTime):
        command = {'on': False, 'transitiontime': fadeTime * 10}

    def on(self, fadeTime):
        command = {'on': True, 'transitiontime': fadeTime * 10}

    def getValue():
        if not hueBridge.get_light(self.id, 'on'):
            return False
        hue = hueBridge.get_light(self.id, 'hue')
        sat = hueBridge.get_light(self.id, 'sat')
        val = hueBridge.get_light(self.id, 'bri')

        rgb = hueToRGB([hue, sat, val])

        return rgb

    def fadeUp(self, increaseAmount):
        if not hueBridge.get_light(self.id, 'on'):
            return False
        currentBri = hueBridge.get_light(self.id, 'bri')
        currentBri += increaseAmount
        currentBri = clamp(currentBri, 0, 255)
        command = {'bri': currentBri}
        hueBridge.set_light(command)

    def fadeDown(self, decreaseAmount):
        if not hueBridge.get_light(self.id, 'on'):
            return False
        currentBri = hueBridge.get_light(self.id, 'bri')
        currentBri -= decreaseAmount
        currentBri = clamp(currentBri, 0, 255)
        command = {'bri': currentBri}
        hueBridge.set_light(command)


class DMX(Fixture):
    '''DMX gateway control, communicates with dmxBridge.py included in this
    project. DMX fixtures can be RGB, RGBW, and anything else out there'''
    pass




class Relay:
    '''Simple on/off power control, used for stereo control or power saving'''
    pass

class CustomRelay(Relay):
    '''Custom built relay box, communicates with relayBridge.py for control'''
    pass

class HueRelay(Relay):
    '''Hue system relay, uses different communication method, but functionally
    the same'''
    pass



class Room:
    '''Basic control groups, makes controlling a number of fixtures easy'''
    pass