import opc
import time
import math
import numpy as np
import PIL
from DYNAcore import *
import yaml
import random
import threading

encoderVal = 0
locationMap = []
intersections = []
allMap = list(range(128,178)) + list(range(192,242)) + list(range(256,306)) + list(range(320,370)) + list(range(384,448))

#SUPPORT FUNCTIONS
def getNextPixel(currentPixel):
    '''Returns the next pixel in the line, or has a chance of returning an
    intersecting pixel if available. If end of the line is reached, function
    will return False and should be handled by encapsulating call'''
    for array in intersections:
        if currentPixel in array:
            nextPixel = random.choice([i for i in array if i != currentPixel])
            return nextPixel
    if currentPixel % 63 == 0:
        return False
    else:
        return currentPixel + 1

def gradientBuilder(stepList):
    '''Typical input:
    [[startValue, steps], [nextValue, steps], [nextValue, steps], [endValue, 1]]
    Values are RGB
    End value should be followed by a one,
    everything else must have at least 1 step'''

    gradientOut = []
    for s in range(len(stepList - 1)):
        gradientOut.append(s[0])

    return gradientOut

def randomPercent(lower, upper):
    '''Returns a decimal percent given integer percentages'''
    return .01 * random.randrange(lower, upper)

def randomPixels(number):
    '''Returns a list [number] items long of random pixels picked from allMap'''
    pixelList = []
    for i in range(0, number + 1):
        pixelList.append(random.choice(allMap))
    return pixelList



#EFFECT LOOP
#ALL OF THESE SHOULD EVENTUALLY HAVE DEFAULT VALUES
def tracers(size, speed, tracerCount, colorPrimary, colorSecondary):
    '''Lines wander around the lighting array'''
    encoderVal = 0
    leadingEdge = 0
    trailingEdge = False
    capturedPixels = [0]
    while True:
        leadingEdge = getNextPixel(leadingEdge)
        capturedPixels.insert(0, leadingEdge)
        if len(capturedPixels) > size:
            trailingEdge = capturedPixels.pop(-1)

def imageSample(imagedir, imagefile, density=60, frequency=7, speed=1, stagger=True):
    #Render array with beautiful colors
    fullImagePath = os.path.join(imagedir, imagefile)
    colorList = sample_sectors(fullImagePath, allMap)
    megaCommand = []
    iterate = 0
    for p in allMap:
        color = grbFix(colorList[iterate])
        megaCommand.append([p, color, .5 * speed])
        iterate += 1
    sendMultiCommand(megaCommand, controller='bedroomFC')

    while True:
        #Grab some number of pixels
        sampledPix = randomPixels(density)
        colorList = sample_sectors(fullImagePath, sampledPix)
        iterate = 0
        if stagger:
            for pix in sampledPix:
                color = grbFix(colorList[iterate])
                sendCommand(pix, color, fadetime=(.5 * speed), controller='bedroomFC')
                time.sleep(.1 / speed)
                iterate += 1
        else:
            multiCommand = []
            for pix in sampledPix:
                color = grbFix(colorList[iterate])
                multiCommand.append([pix, color, 4 * speed * randomPercent(60, 160)])
                iterate += 1
            sendMultiCommand(multiCommand, controller='bedroomFC')
        if frequency:
            time.sleep(frequency)

#imageSample('E:\\Spidergod\\Images\\Color pallettes','perply.png')

def firefly(index, colorPrimary, colorSecondary, colorBackground, speed):
    '''Used by fireflies() function. A single pixel fades up, fades down to a different color, and then recedes to background'''
    #Fly fades up to primary color
    upTime = (.5 * randomPercent(80, 160)) / speed
    sendCommand(index, colorPrimary, fadetime=upTime, controller='bedroomFC')
    time.sleep((1.3 / speed) * randomPercent(80, 160))
    #Fly fades down to secondary color
    downTime = (3.7 * randomPercent(75, 110)) / speed
    sendCommand(index, colorSecondary, fadetime=downTime, controller='bedroomFC')
    time.sleep((5.0 / speed) * randomPercent(80, 120))
    #Fly recedes into background
    sendCommand(index, colorBackground, fadetime=.5, controller='bedroomFC')

def fireflies(density=9, frequency=5, speed=1, colorPrimary=[85,117,0], colorSecondary=[10,26,0], colorBackground=[0,12,22]):
    '''Dots randomly appear on the array, and fade out into a different color'''
    #Establish the background layer
    backgroundLayer = []
    for f in rooms['bedroom']:
        if f.system == 'Fadecandy':
            color = colorCorrect(f, colorBackground)
            backgroundLayer.append([f, color, .5])
        if f.system == 'Hue':
            color = convert(colorCorrect(f, colorBackground))
            command = {'hue': color[0], 'sat': color[1], 'bri': color[2], 'on': False, 'transitiontime': 5}
            bridge.set_light(f.id, command)
    sendMultiCommand(backgroundLayer, controller='bedroomFC')
    #Effect loop
    iteration = 0
    nextChoice = random.randrange(4, 8)
    while True:
        #Grab pixels to put fireflies on
        flyLocations = randomPixels(int(density * randomPercent(25, 150)))
        #All flies appear
        for l in flyLocations:
            flyThread = threading.Thread(target=firefly, args=[l, colorPrimary, colorSecondary, colorBackground, speed])
            flyThread.start()
            time.sleep((.1 / speed) * randomPercent(100, 250))
        if iteration % nextChoice == 0:
            iteration = 0
            nextChoice = random.randrange(5, 10)
            time.sleep(frequency * randomPercent(50, 110))
        else:
            iteration += 1
            time.sleep((.5 / speed) * randomPercent(90, 190))

fireflies(speed=.75)

def static(staticMap, fadeTime, globalBrightness):
    '''User definied fixed look for the room'''

def sunrise(realTime, cycleTime, startTime):
    '''Simulates circadian cycle in the room'''

def hyperspace(speed, colorPrimary, colorSecondary):
    '''Radial streaks of color move through the space'''

def shimmer(speed, density, colorSpread, colorPrimary, colorSecondary):
    '''Base color field with flashes of secondary color'''
