# -*- coding: utf-8 -*-

'''
Created on Dec 27, 2015

@author: Adam Furman
@copyright: MIT License
'''
import pygame
try:
    import pygame.freetype
except ImportError:
    pass
import json
import os
import builtins
from importlib import import_module
from shutil import rmtree
from zipfile import ZipFile
from _thread import start_new_thread
from datetime import datetime
from builtins import staticmethod
from traceback import format_exc
from copy import deepcopy

#state = None
screen = None

import_module("apps.about")

from apps.about import *

settings = {}

DEFAULT = 0xada
    
def readFile(path):
    f = open(path, "rU")
    lines = []
    for line in f.readlines():
        lines.append(line.rstrip())
    f.close()
    return lines

def readJSON(path, default={}):
    try:
        f = open(path, "rU")    
        jsd = json.loads(str(str(f.read())))        
        f.close()
        return jsd
    except:
        return default
    
class Thread(object):
    def __init__(self, method, **data):
        self.eventBindings = {}
        self.pause = False
        self.stop = False
        self.firstRun = True
        self.method = method
        self.pause = data.get("startPaused", False)
        self.eventBindings["onStart"] = data.get("onStart", None)
        self.eventBindings["onStop"] = data.get("onStop", None)
        self.eventBindings["onPause"] = data.get("onPause", None)
        self.eventBindings["onResume"] = data.get("onResume", None)
        self.eventBindings["onCustom"] = data.get("onCustom", None)
        
    @staticmethod
    def __defaultEvtMethod(self, *args):
        return
        
    def execEvent(self, evtKey, *params):
        toExec = self.eventBindings.get(evtKey, Thread.__defaultEvtMethod)
        if toExec == None: return
        if isinstance(toExec, list):
            toExec[0](*toExec[1])
        else:
            toExec(*params);
        
    def setPause(self, state="toggle"):
        if not isinstance(state, bool):
            self.pause = not self.pause
        else:
            self.pause = state
        if self.pause: self.execEvent("onPause")
        else: self.execEvent("onResume")
        
    def setStop(self):
        self.stop = True
        self.execEvent("onStop")
        
    def run(self):
        try:
            if self.firstRun:
                if self.eventBindings["onStart"] != None:
                    self.execEvent("onStart")
                self.firstRun = False
            if not self.pause and not self.stop:
                self.method()
        except:
            State.error_recovery("Thread error.", "Thread bindings: "+str(self.eventBindings))
            self.stop = True
            self.firstRun = False
            
class Task(Thread):
    def __init__(self, method, *additionalData):
        super(Task, self).__init__(method)
        self.returnedData = None
        self.additionalData = additionalData
        
    def run(self):
        self.returnedData = self.method(*self.additionalData)
        self.setStop()
        
    def getReturn(self):
        return self.returnedData
        
    def setPause(self): return
    def execEvent(self, evtKey, *params): return
    
class StagedTask(Task):    
    def __init__(self, method, maxStage=10):
        super(StagedTask, self).__init__(method)
        self.stage = 1
        self.maxStage = maxStage
    
    def run(self):
        self.returnedData = self.method(self.stage)
        self.stage += 1
        if self.stage >= self.maxStage:
            self.setStop()
            
class TimedTask(Task):
    def __init__(self, executeOn, method, *additionalData):
        self.executionTime = executeOn
        super(TimedTask, self).__init__(method, *additionalData)
        
    def run(self):
        delta = self.executionTime - datetime.now()
        if delta.total_seconds() <= 0:
            super(TimedTask, self).run()
            
class ParallelTask(Task):
    #Warning: This starts a new thread.
    def __init__(self, method, *additionalData):
        super(ParallelTask, self).__init__(method, *additionalData)
        self.ran = False
    
    def run(self):
        if not self.ran:
            start_new_thread(self.runHelper, ())
            self.ran = True
        
    def getReturn(self):
        return None
    
    def runHelper(self):
        self.method(*self.additionalData)
        self.setStop()
    
    def setStop(self):
        super(ParallelTask, self).setStop()
                
class Controller(object):
    def __init__(self):
        self.threads = []
        self.dataRequests = {}
        
    def requestData(self, fromThread, default=None):
        self.dataRequests[fromThread] = default
        
    def getRequestedData(self, fromThread):
        return self.dataRequests[fromThread]
    
    def addThread(self, thread):
        self.threads.append(thread)
        
    def removeThread(self, thread):
        try:
            if isinstance(thread, int):
                self.threads.pop(thread)
            else:
                self.threads.remove(thread)
        except:
            print("Thread was not removed!")
            
    def stopAllThreads(self):
        for thread in self.threads:
            thread.setStop()
        
    def run(self):
        for thread in self.threads:
            thread.run()
            if thread in self.dataRequests:
                try:
                    self.dataRequests[thread] = thread.getReturn()
                except:
                    self.dataRequests[thread] = False #getReturn called on Thread, not Task
            if thread.stop:
                self.threads.remove(thread)
        
class GUI(object):    
    def __init__(self):
        global screen
        self.orientation = 0 #0 for portrait, 1 for landscape
        self.timer = None
        self.update_interval = settings.get("target_fps", 30)
        pygame.init()
        try:
            pygame.display.set_icon(pygame.image.load("res/icons/menu.png"))
        except:
            pass
        if __import__("sys").platform == "linux2" and os.path.exists("/etc/pyos"):
            pygame.mouse.set_visible(False)
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            screen = pygame.display.set_mode((info.current_w, info.current_h))
        else:
            screen = pygame.display.set_mode((settings.get("screen_size", {"width":240}).get("width"),
                                              settings.get("screen_size", {"height":320}).get("height")), pygame.HWACCEL)
            self.width = screen.get_width()
            self.height = screen.get_height()
        try:
            screen.blit(pygame.image.load("res/splash2.png"), [0, 0])
        except:
            screen.blit(pygame.font.Font(None, 20).render("Loading Python OS 6...", 1, (200, 200, 200)), [5, 5])
        pygame.display.flip()
        builtins.screen = screen
        globals()["screen"] = screen
        self.timer = pygame.time.Clock()
        pygame.display.set_caption("PyOS 6")
        
    def orient(self):
        global screen
        self.orientation = 0 if self.orientation == 1 else 1
        bk = self.width
        self.width = self.height
        self.height = bk
        screen = pygame.display.set_mode((self.width, self.height))
        for app in state.getApplicationList().getApplicationList():
            app.ui.refresh()
        State.rescue()
            
    def repaint(self):
        screen.fill(state.getColorPalette().getColor("background"))
        
    def refresh(self):
        pygame.display.flip()
        
    def getScreen(self):
        return screen
    
    def monitorFPS(self):
        real = round(self.timer.get_fps())
        if real >= self.update_interval and self.update_interval < 30:
            self.update_interval += 1
        else:
            if self.update_interval > 10:
                self.update_interval -= 1
    
    def displayStandbyText(self, text="Stand by...", size=20, color=(20, 20, 20), bgcolor=(100, 100, 200)):
        pygame.draw.rect(screen, bgcolor, [0, ((state.getGUI().height - 40)/2) - size, state.getGUI().width, 2*size])
        screen.blit(state.getFont().get(size).render(text, 1, color), (5, ((state.getGUI().height - 40)/2) - size+(size/4)))
        pygame.display.flip()
    
    @staticmethod
    def getCenteredCoordinates(component, larger):
        return [(larger.computedWidth / 2) - (component.computedWidth / 2), (larger.computedHeight / 2) - (component.computedHeight / 2)]
        
    class Font(object):        
        def __init__(self, path="res/RobotoCondensed-Regular.ttf", minSize=10, maxSize=30):
            self.path = path
            curr_size = minSize
            self.sizes = {}
            self.ft_support = True
            self.ft_sizes = {}
            while curr_size <= maxSize:
                if self.ft_support:
                    try:
                        self.ft_sizes[curr_size] = pygame.freetype.Font(path, curr_size)
                    except:
                        self.ft_support = False
                self.sizes[curr_size] = pygame.font.Font(path, curr_size)
                curr_size += 1
            
        def get(self, size=14, ft=False):
            if ft and self.ft_support:
                if size not in self.ft_sizes:
                    self.ft_sizes[size] = pygame.freetype.Font(self.path, size)
                return self.ft_sizes[size]
            else:
                if size not in self.sizes:
                    self.sizes[size] = pygame.font.Font(self.path, size)
                return self.sizes[size]
            
    class Icons(object):
        def __init__(self):
            self.rootPath = "res/icons/"
            self.icons = {
                     "menu": "menu.png",
                     "unknown": "unknown.png",
                     "error": "error.png",
                     "warning": "warning.png",
                     "file": "file.png",
                     "folder": "folder.png",
                     "wifi": "wifi.png",
                     "python": "python.png",
                     "quit": "quit.png",
                     "copy": "files_copy.png",
                     "delete": "files_delete.png",
                     "goto": "files_goto.png",
                     "home_dir": "files_home.png",
                     "move": "files_move.png",
                     "select": "files_select.png",
                     "up": "files_up.png",
                     "back": "back.png",
                     "forward": "forward.png",
                     "search": "search.png",
                     "info": "info.png",
                     "open": "open.png",
                     "save": "save.png"
                     }
        
        def getIcons(self):
            return self.icons
        
        def getRootPath(self):
            return self.rootPath
        
        def getLoadedIcon(self, icon, folder=""):
            try:
                return pygame.image.load(os.path.join(self.rootPath, self.icons[icon]))
            except:
                if os.path.exists(icon):
                    return pygame.transform.scale(pygame.image.load(icon), (40, 40))
                if os.path.exists(os.path.join("res/icons/", icon)):
                    return pygame.transform.scale(pygame.image.load(os.path.join("res/icons/", icon)), (40, 40))
                if os.path.exists(os.path.join(folder, icon)):
                    return pygame.transform.scale(pygame.image.load(os.path.join(folder, icon)), (40, 40))
                return pygame.image.load(os.path.join(self.rootPath, self.icons["unknown"]))
        
        @staticmethod
        def loadFromFile(path):
            f = open(path, "rU")
            icondata = json.load(f)
            toreturn = GUI.Icons()
            for key in list(dict(icondata).keys()):
                toreturn.icons[key] = icondata.get(key)
            f.close()
            return toreturn
    
    class ColorPalette(object):
        def __init__(self):
            self.palette = {
                       "normal": {
                                  "background": (200, 200, 200),
                                  "item": (20, 20, 20),
                                  "accent": (100, 100, 200),
                                  "warning": (250, 160, 45),
                                  "error": (250, 50, 50)
                                  },
                       "dark": {
                                "background": (50, 50, 50),
                                "item": (220, 220, 220),
                                "accent": (50, 50, 150),
                                "warning": (200, 110, 0),
                                "error": (200, 0, 0)
                                },
                       "light": {
                                 "background": (250, 250, 250),
                                 "item": (50, 50, 50),
                                 "accent": (150, 150, 250),
                                 "warning": (250, 210, 95),
                                 "error": (250, 100, 100)
                                 }
                       }
            self.scheme = "normal"
        
        def getPalette(self):
            return self.palette
        
        def getScheme(self):
            return self.scheme
        
        def getColor(self, item):
            if item.find(":") == -1:
                return self.palette[self.scheme][item]
            else:
                split = item.split(":")
                cadd = lambda c, d: (c[0]+d[0], c[1]+d[1], c[2]+d[2])
                if split[0] == "darker":
                    return max(cadd(self.getColor(split[1]), (-20, -20, -20)), (0, 0, 0))
                if split[0] == "dark":
                    return max(cadd(self.getColor(split[1]), (-40, -40, -40)), (0, 0, 0))
                if split[0] == "lighter":
                    return min(cadd(self.getColor(split[1]), (20, 20, 20)), (250, 250, 250))
                if split[0] == "light":
                    return min(cadd(self.getColor(split[1]), (40, 40, 40)), (250, 250, 250))
                if split[0] == "transparent":
                    return self.getColor(split[1]) + (int(split[2].rstrip("%"))/100,)
        
        def __getitem__(self, item):
            return self.getColor(item)
        
        def setScheme(self, scheme="normal"):
            self.scheme = scheme
        
        @staticmethod
        def loadFromFile(path):
            f = open(path, "rU")
            colordata = json.load(f)
            toreturn = GUI.ColorPalette()
            for key in list(dict(colordata).keys()):
                toreturn.palette[key] = colordata.get(key)
            f.close()
            return toreturn
        
        @staticmethod
        def HTMLToRGB(colorstring):
            colorstring = colorstring.strip()
            if colorstring[0] == '#': colorstring = colorstring[1:]
            if len(colorstring) != 6:
                raise ValueError("input #%s is not in #RRGGBB format" % colorstring)
            r, g, b = colorstring[:2], colorstring[2:4], colorstring[4:]
            r, g, b = [int(n, 16) for n in (r, g, b)]
            return (r, g, b)
        
        @staticmethod
        def RGBToHTMLColor(rgb_tuple):
            hexcolor = '#%02x%02x%02x' % rgb_tuple
            return hexcolor
        
    class LongClickEvent(object):        
        def __init__(self, mouseDown):
            self.mouseDown = mouseDown
            self.mouseDownTime = datetime.now()
            self.mouseUp = None
            self.mouseUpTime = None
            self.intermediatePoints = []
            self.pos = self.mouseDown.pos
            
        def intermediateUpdate(self, mouseMove):
            if self.mouseUp == None and (len(self.intermediatePoints) == 0 or mouseMove.pos != self.intermediatePoints[-1]):
                self.intermediatePoints.append(mouseMove.pos)
            
        def end(self, mouseUp):
            self.mouseUp = mouseUp
            self.mouseUpTime = datetime.now()
            self.pos = self.mouseUp.pos
            
        def getLatestUpdate(self):
            if len(self.intermediatePoints) == 0: return self.pos
            else: return self.intermediatePoints[len(self.intermediatePoints) - 1]
            
        def checkValidLongClick(self, time=300): #Checks timestamps against parameter (in milliseconds)
            delta = self.mouseUpTime - self.mouseDownTime
            return (delta.microseconds / 1000) >= time
        
    class IntermediateUpdateEvent(object):
        def __init__(self, pos, src):
            self.pos = pos
            self.sourceEvent = src
        
    class EventQueue(object):
        def __init__(self):
            self.events = []
        
        def check(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    State.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.events.append(GUI.LongClickEvent(event))
                if event.type == pygame.MOUSEMOTION and len(self.events) > 0 and isinstance(self.events[len(self.events)-1], GUI.LongClickEvent):
                    self.events[len(self.events)-1].intermediateUpdate(event)
                if event.type == pygame.MOUSEBUTTONUP and len(self.events) > 0 and isinstance(self.events[len(self.events)-1], GUI.LongClickEvent):
                    self.events[len(self.events)-1].end(event)
                    if not self.events[len(self.events)-1].checkValidLongClick():
                        self.events[len(self.events)-1] = self.events[len(self.events)-1].mouseUp
        
        def getLatest(self):
            if len(self.events) == 0: return None
            return self.events.pop()
        
        def removeEvent(self, ev):
            if ev in self.events:
                self.events.remove(ev)
        
        def getLatestComplete(self):
            if len(self.events) == 0: return None
            p = len(self.events) - 1
            while p >= 0:
                event = self.events[p]
                if isinstance(event, GUI.LongClickEvent):
                    if event.mouseUp != None:
                        return self.events.pop(p)
                    else:
                        return GUI.IntermediateUpdateEvent(self.events[len(self.events) - 1].getLatestUpdate(), self.events[len(self.events) - 1])
                else:
                    return self.events.pop(p)
                p -= 1
            
        def clear(self):
            self.events = []
        
    class Component(object):                    
        def __init__(self, position, **data):
            self.position = list(deepcopy(position))
            self.eventBindings = {}
            self.eventData = {}
            self.data = data
            self.surface = data.get("surface", None)
            self.border = 0
            self.borderColor = (0, 0, 0)
            self.resizable = data.get("resizable", False)
            self.originals = [list(deepcopy(position)),
                              data.get("width", data["surface"].get_width() if data.get("surface", False) != False else 0),
                              data.get("height", data["surface"].get_height() if data.get("surface", False) != False else 0)
                              ]
            self.width = self.originals[1]
            self.height = self.originals[2]
            self.computedWidth = 0
            self.computedHeight = 0
            self.computedPosition = [0, 0]
            self.rect = pygame.Rect(self.computedPosition, (self.computedWidth, self.computedHeight))
            self.setDimensions()
            self.eventBindings["onClick"] = data.get("onClick", None)
            self.eventBindings["onLongClick"] = data.get("onLongClick", None)
            self.eventBindings["onIntermediateUpdate"] = data.get("onIntermediateUpdate", None)
            self.eventData["onClick"] = data.get("onClickData", None)
            self.eventData["onIntermediateUpdate"] = data.get("onIntermediateUpdateData", None)
            self.eventData["onLongClick"] = data.get("onLongClickData", None)
            if "border" in data: 
                self.border = int(data["border"])
                self.borderColor = data.get("borderColor", state.getColorPalette().getColor("item"))
            self.innerClickCoordinates = (-1, -1)
            self.innerOffset = [0, 0]
            self.internalClickOverrides = {}
            
        def _percentToPix(self, value, scale):
            return int(int(value.rstrip("%")) * scale)
            
        def setDimensions(self):
            old_surface = self.surface.copy() if self.surface != None else None
            if self.data.get("fixedSize", False):
                self.computedWidth = self.data.get("width")
                self.computedHeight = self.data.get("height")
                self.rect = pygame.Rect(self.computedPosition, (self.computedWidth, self.computedHeight))
                self.surface = pygame.Surface((self.computedWidth, self.computedHeight), pygame.SRCALPHA)
                if old_surface != None: self.surface.blit(old_surface, (0, 0))
                return
            appc = state.getActiveApplication().ui
            #Compute Position
            if isinstance(self.position[0], str):
                self.computedPosition[0] = self._percentToPix(self.position[0], (state.getActiveApplication().ui.width/100.0))
            else:
                if self.resizable:
                    self.computedPosition[0] = int(self.position[0] * appc.scaleX)
                else:
                    self.computedPosition[0] = int(self.position[0])
            if isinstance(self.position[1], str):
                self.computedPosition[1] = self._percentToPix(self.position[1], (state.getActiveApplication().ui.height/100.0))
            else:
                if self.resizable:
                    self.computedPosition[1] = int(self.position[1] * appc.scaleY)
                else:
                    self.computedPosition[1] = int(self.position[1])
                    
            #Compute Width and Height
            if isinstance(self.width, str):
                self.computedWidth = self._percentToPix(self.width, (state.getActiveApplication().ui.width/100.0))
            else:
                if self.resizable:
                    self.computedWidth = int(self.width * appc.scaleX)
                else:
                    self.computedWidth = int(self.width)
            if isinstance(self.height, str):
                self.computedHeight = self._percentToPix(self.height, (state.getActiveApplication().ui.height/100.0))
            else:
                if self.resizable:
                    self.computedHeight = int(self.height * appc.scaleY)
                else:
                    self.computedHeight = int(self.height)
                    
            #print "Computed to: " + str(self.computedPosition) + ", " + str(self.computedWidth) + "x" + str(self.computedHeight) + ", " + str(self.resizable)
            self.rect = pygame.Rect(self.computedPosition, (self.computedWidth, self.computedHeight))                    
            self.surface = pygame.Surface((self.computedWidth, self.computedHeight), pygame.SRCALPHA)
            if old_surface != None: self.surface.blit(old_surface, (0, 0))

        def onClick(self):
            if "onClick" in self.internalClickOverrides:
                self.internalClickOverrides["onClick"][0](*self.internalClickOverrides["onClick"][1])
            if self.eventBindings["onClick"]: 
                if self.eventData["onClick"]:
                    self.eventBindings["onClick"](*self.eventData["onClick"])
                else:
                    self.eventBindings["onClick"]()
            
        def onLongClick(self):
            if "onLongClick" in self.internalClickOverrides:
                self.internalClickOverrides["onLongClick"][0](*self.internalClickOverrides["onLongClick"][1])
            if self.eventBindings["onLongClick"]:
                if self.eventData["onLongClick"]:
                    self.eventBindings["onLongClick"](*self.eventData["onLongClick"])
                else:
                    self.eventBindings["onLongClick"]()
                    
        def onIntermediateUpdate(self):
            if "onIntermediateUpdate" in self.internalClickOverrides:
                self.internalClickOverrides["onIntermediateUpdate"][0](*self.internalClickOverrides["onIntermediateUpdate"][1])
            if self.eventBindings["onIntermediateUpdate"]: 
                    if self.eventData["onIntermediateUpdate"]:
                        self.eventBindings["onIntermediateUpdate"](*self.eventData["onIntermediateUpdate"])
                    else:
                        self.eventBindings["onIntermediateUpdate"]()
                        
        def setOnClick(self, mtd, data=()):
            self.eventBindings["onClick"] = mtd
            self.eventData["onClick"] = data
            
        def setOnLongClick(self, mtd, data=()):
            self.eventBindings["onLongClick"] = mtd
            self.eventData["onLong"] = data
        
        def setOnIntermediateUpdate(self, mtd, data=()):
            self.eventBindings["onIntermediateUpdate"] = mtd
            self.eventData["onIntermediateUpdate"] = data

        def render(self, largerSurface):
            recompute = False
            if self.position != self.originals[0]:
                self.originals[0] = list(deepcopy(self.position))
                recompute = True
            if self.width != self.originals[1]:
                self.originals[1] = self.width
                recompute = True
            if self.height != self.originals[2]:
                self.originals[2] = self.height
                recompute = True
            if recompute:
                self.setDimensions()
            if self.border > 0:
                pygame.draw.rect(self.surface, self.borderColor, [0, 0, self.computedWidth, self.computedHeight], self.border)
            if not self.surface.get_locked():
                largerSurface.blit(self.surface, self.computedPosition)
            
        def refresh(self):
            self.setDimensions()
            
        def getInnerClickCoordinates(self):
            return self.innerClickCoordinates
            
        def checkClick(self, mouseEvent, offsetX=0, offsetY=0):
            self.innerOffset = [offsetX, offsetY]
            adjusted = [mouseEvent.pos[0] - offsetX, mouseEvent.pos[1] - offsetY]
            if adjusted[0] < 0 or adjusted[1] < 0: return False
            if self.rect.collidepoint(adjusted):
                self.innerClickCoordinates = tuple(adjusted)
                if not isinstance(mouseEvent, GUI.IntermediateUpdateEvent):
                    self.data["lastEvent"] = mouseEvent
                return True
            return False
        
        def setPosition(self, pos):
            self.position = list(pos)[:]
            self.refresh()
            
        def setSurface(self, new_surface, override_dimensions=False):
            if new_surface.get_width() != self.computedWidth or new_surface.get_height() != self.computedHeight:
                if override_dimensions:
                    self.width = new_surface.get_width()
                    self.height = new_surface.get_height()
                else:
                    new_surface = pygame.transform.scale(new_surface, (self.computedWidth, self.computedHeight))
            self.surface = new_surface
            
        @staticmethod
        def default(*items):
            if len(items)%2 != 0: return items
            values = []
            p = 0
            while p < len(items):
                values.append(items[p+1] if items[p] == DEFAULT else items[p])
                p += 2
            return tuple(values)
        
    class Container(Component):        
        def __init__(self, position, **data):
            super(GUI.Container, self).__init__(position, **data)
            self.transparent = False
            self.backgroundColor = (0, 0, 0)
            self.childComponents = []
            self.SKIP_CHILD_CHECK = False
            self.transparent = data.get("transparent", False)
            self.backgroundColor = data.get("color", state.getColorPalette().getColor("background"))
            if "children" in data: self.childComponents = data["children"]
            
        def addChild(self, component):
            if self.resizable and "resizeble" not in component.data:
                component.resizable = True
                component.refresh()
            self.childComponents.append(component)
            
        def addChildren(self, *children):
            for child in children:
                self.addChild(child)
            
        def removeChild(self, component):
            self.childComponents.remove(component)
            
        def clearChildren(self):
            for component in self.childComponents:
                self.removeChild(component)
            self.childComponents = []
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            currChild = len(self.childComponents)
            while currChild > 0:
                currChild -= 1
                child = self.childComponents[currChild]
                if "SKIP_CHILD_CHECK" in child.__dict__:
                    if child.SKIP_CHILD_CHECK:
                        if child.checkClick(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1]):
                            return child
                        else:
                            continue
                    else:
                        subCheck = child.getClickedChild(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1])
                        if subCheck == None: continue
                        return subCheck
                else:
                    if child.checkClick(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1]):
                        return child
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
        def getChildAt(self, position):
            for child in self.childComponents:
                if child.computedPosition == list(position):
                    return child
            return None
        
        def render(self, largerSurface):
            if self.surface.get_locked(): return
            if not self.transparent:
                self.surface.fill(self.backgroundColor)
            else:
                self.surface.fill((0, 0, 0, 0))
            for child in self.childComponents:
                child.render(self.surface)
            super(GUI.Container, self).render(largerSurface)
            
        def refresh(self, children=True):
            super(GUI.Container, self).refresh()
            if children:
                for child in self.childComponents:
                    child.refresh()
                
    class AppContainer(Container):        
        def __init__(self, application):
            self.application = application
            self.dialogs = []
            self.dialogScreenFreezes = []
            self.dialogComponentsFreezes = []
            self.scaleX = 1.0
            self.scaleY = 1.0
            if self.application.parameters.get("resize", False):
                dW = float(self.application.parameters.get("size", {"width": 240}).get("width"))
                dH = float(self.application.parameters.get("size", {"height": 320}).get("height"))
                self.scaleX = (state.getGUI().width / dW)
                self.scaleY = (state.getGUI().height / dH)
                super(GUI.AppContainer, self).__init__((0, 0), width=screen.get_width(), height=screen.get_height()-40,
                                                       resizable=True, fixedSize=True)
            else:
                super(GUI.AppContainer, self).__init__((0, 0), width=screen.get_width(), height=screen.get_height()-40,
                                                       resizable=False, fixedSize=True)
            
        def setDialog(self, dialog):
            self.dialogs.insert(0, dialog)
            self.dialogComponentsFreezes.insert(0, self.childComponents[:])
            self.dialogScreenFreezes.insert(0, self.surface.copy())
            self.addChild(dialog.baseContainer)
            
        def clearDialog(self):
            self.dialogs.pop(0)
            self.childComponents = self.dialogComponentsFreezes[0]
            self.dialogComponentsFreezes.pop(0)
            self.dialogScreenFreezes.pop(0)
            
        def render(self):
            if self.dialogs == []:
                super(GUI.AppContainer, self).render(self.surface)
            else:
                self.surface.blit(self.dialogScreenFreezes[0], (0, 0))
                self.dialogs[0].baseContainer.render(self.surface)
            screen.blit(self.surface, self.position)
            
        def refresh(self):
            self.width = screen.get_width()
            self.height = screen.get_height() - 40
            if self.application.parameters.get("resize", False):
                dW = float(self.application.parameters.get("size", {"width": 240}).get("width"))
                dH = float(self.application.parameters.get("size", {"height": 320}).get("height"))
                self.scaleX = 1.0 * (state.getGUI().width / dW)
                self.scaleY = 1.0 * (state.getGUI().height / dH)
            #super(GUI.AppContainer, self).refresh()
            
    class Text(Component):        
        def __init__(self, position, text, color=DEFAULT, size=DEFAULT, **data):
            #Defaults are "item" and 14.
            color, size = GUI.Component.default(color, state.getColorPalette().getColor("item"), size, 14)
            self.text = text
            self._originalText = text
            self.size = size
            self.color = color
            self.font = data.get("font", state.getFont())
            self.use_freetype = data.get("freetype", False)
            self.responsive_width = data.get("responsive_width", True)
            data["surface"] = self.getRenderedText()
            super(GUI.Text, self).__init__(position, **data)
            
        def getRenderedText(self):
            if self.use_freetype:
                return self.font.get(self.size, True).render(str(self.text), self.color)
            return self.font.get(self.size).render(self.text, 1, self.color)
            
        def refresh(self):
            self.surface = self.getRenderedText()        

        def render(self, largerSurface):
            if self.text != self._originalText:
                self.setText(self.text)
            super(GUI.Text, self).render(largerSurface)
        
        def setText(self, text):
            self.text = text if isinstance(text, str) or isinstance(text, str) else str(text)
            self._originalText = self.text
            self.refresh()
            if self.responsive_width:
                self.width = self.surface.get_width()
                self.height = self.surface.get_height()
            self.setDimensions()
            
    class MultiLineText(Component):
        @staticmethod
        def render_textrect(string, font, rect, text_color, background_color, justification, use_ft):
            final_lines = []
            requested_lines = string.splitlines()
            err = None
            for requested_line in requested_lines:
                if font.size(requested_line)[0] > rect.width:
                    words = requested_line.split(' ')
                    for word in words:
                        if font.size(word)[0] >= rect.width:
                            #print "The word " + word + " is too long to fit in the rect passed."
                            err = 0
                    accumulated_line = ""
                    for word in words:
                        test_line = accumulated_line + word + " "
                        if font.size(test_line)[0] < rect.width:
                            accumulated_line = test_line 
                        else: 
                            final_lines.append(accumulated_line) 
                            accumulated_line = word + " " 
                    final_lines.append(accumulated_line)
                else: 
                    final_lines.append(requested_line)         
            surface = pygame.Surface(rect.size, pygame.SRCALPHA) 
            surface.fill(background_color) 
            accumulated_height = 0 
            for line in final_lines: 
                if accumulated_height + font.size(line)[1] >= rect.height:
                    err = 1
                if line != "":
                    tempsurface = None
                    if use_ft:
                        tempsurface = font.render(line, text_color)
                    else:
                        tempsurface = font.render(line, 1, text_color)
                    if justification == 0:
                        surface.blit(tempsurface, (0, accumulated_height))
                    elif justification == 1:
                        surface.blit(tempsurface, ((rect.width - tempsurface.get_width()) / 2, accumulated_height))
                    elif justification == 2:
                        surface.blit(tempsurface, (rect.width - tempsurface.get_width(), accumulated_height))
                    else:
                        print("Invalid justification argument: " + str(justification))
                        err = 2
                accumulated_height += font.size(line)[1]
            return (surface, err, final_lines)
        
        def __init__(self, position, text, color=DEFAULT, size=DEFAULT, justification=DEFAULT, **data):
            #Defaults are "item", and 0 (left).
            color, size, justification = GUI.Component.default(color, state.getColorPalette().getColor("item"), size, 14,
                                                         justification, 0)
            self.justification = justification
            self.color = color
            self.size = size
            self.text = text if isinstance(text, str) or isinstance(text, str) else str(text)
            self.textSurface = None
            self.font = data.get("font", state.getFont())
            self.use_freetype = data.get("freetype", False)
            super(GUI.MultiLineText, self).__init__(position, **data)
            self.refresh()
            if self.width > state.getGUI().width:
                self.width = state.getGUI().width
                
        def getRenderedText(self):
            return GUI.MultiLineText.render_textrect(self.text, self.font.get(self.size, self.use_freetype), pygame.Rect(0, 0, self.computedWidth, self.computedHeight),
                                                     self.color, (0, 0, 0, 0), self.justification, self.use_freetype)[0]
            
        def refresh(self):
            super(GUI.MultiLineText, self).refresh()
            self.textSurface = self.getRenderedText()
            self.surface.fill((0, 0, 0, 0))
            self.surface.blit(self.textSurface, (0, 0))
            
        def setText(self, text):
            self.text = text if isinstance(text, str) or isinstance(text, str) else str(text)
            self.setDimensions()
            self.refresh()
            
    class ExpandingMultiLineText(MultiLineText):
        def __init__(self, position, text, color=DEFAULT, size=DEFAULT, justification=DEFAULT, lineHeight=DEFAULT, **data):
            #Defaults are "item", 14, 0, and 16.
            color, size, justification, lineHeight = GUI.Component.default(color, state.getColorPalette().getColor("item"),
                                                                           size, 14,
                                                                           justification, 0,
                                                                           lineHeight, 16)
            self.lineHeight = lineHeight
            self.linkedScroller = data.get("scroller", None)
            self.textLines = []
            super(GUI.ExpandingMultiLineText, self).__init__(position, text, color, size, justification, **data)
            self.height = self.computedHeight
            self.refresh()
            
        def getRenderedText(self):
            fits = False
            surf = None
            while not fits:
                d = GUI.MultiLineText.render_textrect(self.text, self.font.get(self.size), pygame.Rect(self.computedPosition[0], self.computedPosition[1], self.computedWidth, self.height),
                                                      self.color, (0, 0, 0, 0), self.justification, self.use_freetype)
                surf = d[0]
                fits = d[1] != 1
                self.textLines = d[2]
                if not fits:
                    self.height += self.lineHeight
                    self.computedHeight = self.height
            self.setDimensions()
            #if self.linkedScroller != None:
            #    self.linkedScroller.refresh(False)
            return surf
            
    class Image(Component):        
        def __init__(self, position, **data):
            self.path = ""
            self.originalSurface = None
            self.transparent = True
            self.resize_image = data.get("resize_image", True)
            if "path" in data:
                self.path = data["path"]
            else:
                self.path = "surface"
            if "surface" not in data:
                data["surface"] = pygame.image.load(data["path"])
            self.originalSurface = data["surface"]
            self.originalWidth = self.originalSurface.get_width()
            self.originalHeight = self.originalSurface.get_height()
            super(GUI.Image, self).__init__(position, **data)
            if self.resize_image: self.setSurface(pygame.transform.scale(self.originalSurface, (self.computedWidth, self.computedHeight)))
            
        def setImage(self, **data):
            if "path" in data:
                self.path = data["path"]
            else:
                self.path = "surface"
            if "surface" not in data:
                data["surface"] = pygame.image.load(data["path"])
            self.originalSurface = data["surface"]
            if data.get("resize", False):
                self.width = self.originalSurface.get_width()
                self.height = self.originalSurface.get_height()
            self.refresh()
            
        def refresh(self):
            if self.resize_image:
                self.setSurface(pygame.transform.scale(self.originalSurface, (self.computedWidth, self.computedHeight)))
            else:
                super(GUI.Image, self).refresh()
            
    class Slider(Component):
        def __init__(self, position, initialPct=0, **data):
            super(GUI.Slider, self).__init__(position, **data)
            self.percent = initialPct
            self.backgroundColor = data.get("backgroundColor", state.getColorPalette().getColor("background"))
            self.color = data.get("color", state.getColorPalette().getColor("item"))
            self.sliderColor = data.get("sliderColor", state.getColorPalette().getColor("accent"))
            self.onChangeMethod = data.get("onChange", Application.dummy)
            self.refresh()
            
        def onChange(self):
            self.onChangeMethod(self.percent)
            
        def setPercent(self, percent):
            self.percent = percent
        
        def refresh(self):
            self.percentPixels = self.computedWidth / 100.0
            super(GUI.Slider, self).refresh()
            
        def render(self, largerSurface):
            self.surface.fill(self.backgroundColor)
            pygame.draw.rect(self.surface, self.color, [0, self.computedHeight/4, self.computedWidth, self.computedHeight/2])
            pygame.draw.rect(self.surface, self.sliderColor, [(self.percent*self.percentPixels)-15, 0, 30, self.computedHeight])
            super(GUI.Slider, self).render(largerSurface)
            
        def checkClick(self, mouseEvent, offsetX=0, offsetY=0):
            isClicked = super(GUI.Slider, self).checkClick(mouseEvent, offsetX, offsetY)
            if isClicked:
                self.percent = ((mouseEvent.pos[0] - offsetX - self.computedPosition[0])) / self.percentPixels
                if self.percent > 100.0: self.percent = 100.0
                self.onChange()
            return isClicked
        
        def getPercent(self):
            return self.percent
            
    class Button(Container):
        def __init__(self, position, text, bgColor=DEFAULT, textColor=DEFAULT, textSize=DEFAULT, **data):
            #Defaults are "darker:background", "item", and 14.
            bgColor, textColor, textSize = GUI.Component.default(bgColor, state.getColorPalette().getColor("darker:background"),
                                  textColor, state.getColorPalette().getColor("item"),
                                  textSize, 14)
            self.textComponent = GUI.Text((0, 0), text, textColor, textSize, font=data.get("font", state.getFont()), freetype=data.get("freetype", False))
            self.paddingAmount = data.get("padding", 5)
            if "width" not in data: data["width"] = self.textComponent.computedWidth + (2 * self.paddingAmount)
            if "height" not in data: data["height"] = self.textComponent.computedHeight + (2 * self.paddingAmount)
            super(GUI.Button, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.textComponent.setPosition(GUI.getCenteredCoordinates(self.textComponent, self))
            self.backgroundColor = bgColor
            self.addChild(self.textComponent)
            
        def setDimensions(self):
            super(GUI.Button, self).setDimensions()
            self.textComponent.setPosition(GUI.getCenteredCoordinates(self.textComponent, self))
            
        def setText(self, text):
            self.textComponent.setText(text)
            self.setDimensions()
            
        def render(self, largerSurface):
            super(GUI.Button, self).render(largerSurface)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
    class Checkbox(Component):
        def __init__(self, position, checked=False, **data):
            if "border" not in data:
                data["border"] = 2
                data["borderColor"] = state.getColorPalette().getColor("item")
            super(GUI.Checkbox, self).__init__(position, **data)
            self.backgroundColor = data.get("backgroundColor", state.getColorPalette().getColor("background"))
            self.checkColor = data.get("checkColor", state.getColorPalette().getColor("accent"))
            self.checkWidth = data.get("checkWidth", self.computedHeight/4)
            self.checked = checked
            self.internalClickOverrides["onClick"] = [self.check, ()]
            
        def getChecked(self):
            return self.checked
        
        def check(self, state="toggle"):
            if state == "toggle":
                self.checked = not self.checked
            else:
                self.checked = bool(state)
            
        def render(self, largerSurface):
            self.surface.fill(self.backgroundColor)
            if self.checked:
                pygame.draw.lines(self.surface, self.checkColor, False, [(0, self.computedHeight/2),
                                                                         (self.computedWidth/2, self.computedHeight-self.checkWidth/2),
                                                                         (self.computedWidth, 0)], self.checkWidth)
            super(GUI.Checkbox, self).render(largerSurface)
            
    class Switch(Component):
        def __init__(self, position, on=False, **data):
            if "border" not in data:
                data["border"] = 2
                data["borderColor"] = state.getColorPalette().getColor("item")
            super(GUI.Switch, self).__init__(position, **data)
            self.backgroundColor = data.get("backgroundColor", state.getColorPalette().getColor("background"))
            self.onColor = data.get("onColor", state.getColorPalette().getColor("accent"))
            self.offColor = data.get("offColor", state.getColorPalette().getColor("dark:background"))
            self.on = on
            self.internalClickOverrides["onClick"] = [self.switch, ()]
            
        def getChecked(self):
            return self.checked
        
        def switch(self, state="toggle"):
            if state == "toggle":
                self.on = not self.on
            else:
                self.on = bool(state)
            
        def render(self, largerSurface):
            self.surface.fill(self.backgroundColor)
            if self.on:
                pygame.draw.rect(self.surface, self.onColor, [self.computedWidth/2, 0, self.computedWidth/2, self.computedHeight])
            else:
                pygame.draw.rect(self.surface, self.offColor, [0, 0, self.computedWidth/2, self.computedHeight])
            pygame.draw.circle(self.surface, state.getColorPalette().getColor("item"), (self.computedWidth/4, self.computedHeight/2), self.computedHeight/4, 2)
            pygame.draw.line(self.surface, state.getColorPalette().getColor("item"), (3*(self.computedWidth/4), self.computedHeight/4),
                             (3*(self.computedWidth/4), 3*(self.computedHeight/4)), 2)
            super(GUI.Switch, self).render(largerSurface)
                    
    class Canvas(Component):
        def __init__(self, position, **data):
            super(GUI.Canvas, self).__init__(position, **data)
        
    class KeyboardButton(Container):
        def __init__(self, position, symbol, altSymbol, **data):
            if "border" not in data:
                data["border"] = 1
                data["borderColor"] = state.getColorPalette().getColor("item")
            super(GUI.KeyboardButton, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.primaryTextComponent = GUI.Text((1, 0), symbol, state.getColorPalette().getColor("item"), 20, font=data.get("font", state.getTypingFont()))
            self.secondaryTextComponent = GUI.Text((self.computedWidth-8, 0), altSymbol, state.getColorPalette().getColor("item"), 10, font=data.get("font", state.getTypingFont()))
            self.primaryTextComponent.setPosition([GUI.getCenteredCoordinates(self.primaryTextComponent, self)[0]-6, self.computedHeight-self.primaryTextComponent.computedHeight-1])
            self.addChild(self.primaryTextComponent)
            self.addChild(self.secondaryTextComponent)
            self.blinkTime = 0
            self.internalClickOverrides["onClick"] = (self.registerBlink, ())
            self.internalClickOverrides["onLongClick"] = (self.registerBlink, (True,))
            
        def registerBlink(self, lp=False):
            self.blinkTime = state.getGUI().update_interval / 6
            self.primaryTextComponent.color = state.getColorPalette().getColor("background")
            self.secondaryTextComponent.color = state.getColorPalette().getColor("background")
            self.backgroundColor = state.getColorPalette().getColor("accent" if lp else "item")
            self.refresh()
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
        def render(self, largerSurface):
            if self.blinkTime >= 0:
                self.blinkTime -= 1
                if self.blinkTime < 0:
                    self.primaryTextComponent.color = state.getColorPalette().getColor("item")
                    self.secondaryTextComponent.color = state.getColorPalette().getColor("item")
                    self.backgroundColor = state.getColorPalette().getColor("background")
                    self.refresh()
            super(GUI.KeyboardButton, self).render(largerSurface)
        
    class TextEntryField(Container):
        def __init__(self, position, initialText="", **data):
            if "border" not in data:
                data["border"] = 1
                data["borderColor"] = state.getColorPalette().getColor("accent")
            if "textColor" not in data:
                data["textColor"] = state.getColorPalette().getColor("item")
            if "blink" in data:
                self.blinkInterval = data["blink"]
            else:
                self.blinkInterval = 500
            self.doBlink = True
            self.blinkOn = False
            self.lastBlink = datetime.now()
            self.indicatorPosition = len(initialText)
            self.indicatorPxPosition = 0
            super(GUI.TextEntryField, self).__init__(position, **data)
            self.SKIP_CHILD_CHECK = True
            self.textComponent = GUI.Text((2, 0), initialText, data["textColor"], 16, font=state.getTypingFont())
            self.updateOverflow()
            self.lastClickCoord = None
            self.textComponent.position[1] = GUI.getCenteredCoordinates(self.textComponent, self)[1]
            self.addChild(self.textComponent)
            self.MULTILINE = None
            self.internalClickOverrides["onClick"] = (self.activate, ())
            self.internalClickOverrides["onIntermediateUpdate"] = (self.dragScroll, ())
            
        def clearScrollParams(self):
            self.lastClickCoord = None
            
        def dragScroll(self):
            if self.lastClickCoord != None and self.overflow > 0:
                ydist = self.innerClickCoordinates[1] - self.lastClickCoord[1]
                self.overflow -= ydist
                if self.overflow > 0 and self.overflow + self.computedWidth < self.textComponent.computedWidth:
                    self.textComponent.position[0] = 2 - self.overflow
                else:
                    self.textComponent.position[0] = 2
            self.lastClickCoord = self.innerClickCoordinates
            
        def getPxPosition(self, fromPos=DEFAULT):
            return state.getTypingFont().get(16).size(self.textComponent.text[:(self.indicatorPosition if fromPos==DEFAULT else fromPos)])[0]
            
        def activate(self):
            self.clearScrollParams()
            self.updateOverflow()
            state.setKeyboard(GUI.Keyboard(self))
            if self.MULTILINE != None:
                for f in self.MULTILINE.textFields: f.doBlink = False
            self.doBlink = True
            mousePos = self.innerClickCoordinates[0] - self.innerOffset[0]
            if mousePos > self.textComponent.computedWidth:
                self.indicatorPosition = len(self.textComponent.text)
            else:
                prevWidth = 0
                for self.indicatorPosition in range(len(self.textComponent.text)):
                    currWidth = self.getPxPosition(self.indicatorPosition)
                    if mousePos >= prevWidth and mousePos <= currWidth:
                        self.indicatorPosition -= 1
                        break
                    prevWidth = currWidth
            state.getKeyboard().active = True
            self.indicatorPxPosition = self.getPxPosition()
            if self.MULTILINE:
                self.MULTILINE.setCurrent(self)
            return self
        
        def updateOverflow(self):
            self.overflow = max(self.textComponent.computedWidth - (self.computedWidth - 4), 0)
            if self.overflow > 0:
                self.textComponent.position[0] = 2 - self.overflow
            else:
                self.textComponent.position[0] = 2
            
        def appendChar(self, char):
            if self.indicatorPosition == len(self.textComponent.text)-1:
                self.textComponent.text += char
            else:
                self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + char + self.textComponent.text[self.indicatorPosition:]
            self.textComponent.refresh()
            self.indicatorPosition += len(char)
            self.updateOverflow()
            if self.MULTILINE != None:
                if self.overflow > 0:
                    newt = self.textComponent.text[max(self.textComponent.text.rfind(" "),
                                                       self.textComponent.text.rfind("-")):]
                    self.textComponent.text = self.textComponent.text.rstrip(newt)
                    self.MULTILINE.addField(newt)
                    self.MULTILINE.wrappedLines.append(self.MULTILINE.currentField)
                    #if self.MULTILINE.currentField == len(self.MULTILINE.textFields)-1:
                    #    self.MULTILINE.addField(newt)
                    #else:
                    #    self.MULTILINE.prependToNextField(newt)
                    self.textComponent.refresh()
                    self.updateOverflow()
            self.indicatorPxPosition = self.getPxPosition()
            
        def backspace(self):
            if self.indicatorPosition >= 1:
                self.indicatorPosition -= 1
                self.indicatorPxPosition = self.getPxPosition()
                self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + self.textComponent.text[self.indicatorPosition+1:]
                self.textComponent.refresh()
            else:
                if self.MULTILINE != None and self.MULTILINE.currentField > 0:
                    self.MULTILINE.removeField(self)
                    self.MULTILINE.textFields[self.MULTILINE.currentField-1].appendChar(self.textComponent.text.strip(" "))
                    self.MULTILINE.textFields[self.MULTILINE.currentField-1].activate()
            self.updateOverflow()
                
        def delete(self):
            if self.indicatorPosition < len(self.textComponent.text):
                self.textComponent.text = self.textComponent.text[:self.indicatorPosition] + self.textComponent.text[self.indicatorPosition+1:]
                self.textComponent.refresh()
            self.updateOverflow()
            if self.MULTILINE != None:
                self.appendChar(self.MULTILINE.getDeleteChar())
                
        def getText(self):
            return self.textComponent.text
        
        def refresh(self):
            self.updateOverflow()
            super(GUI.TextEntryField, self).refresh()
                
        def render(self, largerSurface):
            if not self.transparent:
                self.surface.fill(self.backgroundColor)
            else:
                self.surface.fill((0, 0, 0, 0))
            for child in self.childComponents:
                child.render(self.surface)
            if self.doBlink:
                if ((datetime.now() - self.lastBlink).microseconds / 1000) >= self.blinkInterval:
                    self.lastBlink = datetime.now()
                    self.blinkOn = not self.blinkOn
                if self.blinkOn:
                    pygame.draw.rect(self.surface, self.textComponent.color, [self.indicatorPxPosition, 2, 2, self.computedHeight-4])
            super(GUI.Container, self).render(largerSurface)
            
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None

    class PagedContainer(Container):
        def __init__(self, position, **data):
            super(GUI.PagedContainer, self).__init__(position, **data)
            self.pages = data.get("pages", [])
            self.currentPage = 0
            self.hideControls = data.get("hideControls", False)
            self.pageControls = GUI.Container((0, self.computedHeight-20), color=state.getColorPalette().getColor("background"), width=self.computedWidth, height=20)
            self.pageLeftButton = GUI.Button((0, 0), " < ", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("accent"),
                                            16, width=40, height=20, onClick=self.pageLeft, onLongClick=self.goToPage)
            self.pageRightButton = GUI.Button((self.computedWidth-40, 0), " > ", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("accent"),
                                            16, width=40, height=20, onClick=self.pageRight, onLongClick=self.goToLastPage)
            self.pageIndicatorText = GUI.Text((0, 0), str(self.currentPage + 1)+" of "+str(len(self.pages)), state.getColorPalette().getColor("item"),
                                            16)
            self.pageHolder = GUI.Container((0, 0), color=state.getColorPalette().getColor("background"), width=self.computedWidth, height=(self.computedHeight-20 if not self.hideControls else self.computedHeight))
            self.pageIndicatorText.position[0] = GUI.getCenteredCoordinates(self.pageIndicatorText, self.pageControls)[0]
            super(GUI.PagedContainer, self).addChild(self.pageHolder)
            self.pageControls.addChild(self.pageLeftButton)
            self.pageControls.addChild(self.pageIndicatorText)
            self.pageControls.addChild(self.pageRightButton)
            if not self.hideControls:
                super(GUI.PagedContainer, self).addChild(self.pageControls)
            
        def addPage(self, page):
            self.pages.append(page)
            self.pageIndicatorText.text = str(self.currentPage + 1)+" of "+str(len(self.pages))
            self.pageIndicatorText.refresh()
            
        def getPage(self, number):
            return self.pages[number]
            
        def pageLeft(self):
            if self.currentPage >= 1:
                self.goToPage(self.currentPage - 1)
        
        def pageRight(self):
            if self.currentPage < len(self.pages) - 1:
                self.goToPage(self.currentPage + 1)
        
        def goToPage(self, number=0):
            self.currentPage = number
            self.pageHolder.clearChildren()
            self.pageHolder.addChild(self.getPage(self.currentPage))
            self.pageIndicatorText.setText(str(self.currentPage + 1)+" of "+str(len(self.pages)))
            self.pageIndicatorText.refresh()
        
        def goToLastPage(self): self.goToPage(len(self.pages) - 1)
        
        def getLastPage(self):
            return self.pages[len(self.pages) - 1]
        
        def generatePage(self, **data):
            if "width" not in data: data["width"] = self.pageHolder.computedWidth
            if "height" not in data: data["height"] = self.pageHolder.computedHeight
            data["isPage"] = True
            return GUI.Container((0, 0), **data)
        
        def addChild(self, component):
            if self.pages == []:
                self.addPage(self.generatePage(color=self.backgroundColor, width=self.pageHolder.computedWidth, height=self.pageHolder.computedHeight))
            self.getLastPage().addChild(component)
            
        def removeChild(self, component):
            self.pages[self.currentPage].removeChild(component)
            childrenCopy = self.pages[self.currentPage].childComponents[:]
            for page in self.pages:
                for child in page.childComponents:
                    page.removeChild(child)
            for child in childrenCopy:
                self.addChild(child)
                
        def removePage(self, page):
            if isinstance(page, int):
                self.pages.pop(page)
            else:
                self.pages.remove(page)
            if self.currentPage >= len(self.pages):
                self.goToPage(self.currentPage - 1)
                
        def clearChildren(self):
            self.pages = []
            self.addPage(self.generatePage(color=self.backgroundColor))
            self.goToPage()
            
    class GriddedPagedContainer(PagedContainer):
        def __init__(self, position, rows=5, columns=4, **data):
            self.padding = 5
            if "padding" in data: self.padding = data["padding"]
            self.rows = rows
            self.columns = columns
            super(GUI.PagedContainer, self).__init__(position, **data)
            self.perRow = ((self.computedHeight-20)-(2*self.padding)) / rows
            self.perColumn = (self.computedWidth-(2*self.padding)) / columns
            super(GUI.GriddedPagedContainer, self).__init__(position, **data)
            
        def isPageFilled(self, number):
            if isinstance(number, int):
                return len(self.pages[number].childComponents) == (self.rows * self.columns)
            else:
                return len(number.childComponents) == (self.rows * self.columns)
            
        def addChild(self, component):
            if self.pages == [] or self.isPageFilled(self.getLastPage()):
                self.addPage(self.generatePage(color=self.backgroundColor))
            newChildPosition = [self.padding, self.padding]
            if self.getLastPage().childComponents == []:
                component.setPosition(newChildPosition)
                self.getLastPage().addChild(component)
                return
            lastChildPosition = self.getLastPage().childComponents[len(self.getLastPage().childComponents) - 1].computedPosition[:]
            if lastChildPosition[0] < self.padding + (self.perColumn * (self.columns - 1)):
                newChildPosition = [lastChildPosition[0]+self.perColumn, lastChildPosition[1]]
            else:
                newChildPosition = [self.padding, lastChildPosition[1]+self.perRow]
            component.setPosition(newChildPosition)
            self.getLastPage().addChild(component)
            
    class ListPagedContainer(PagedContainer):
        def __init__(self, position, **data):
            self.padding = data.get("padding", 0)
            self.margin = data.get("margin", 0)
            super(GUI.ListPagedContainer, self).__init__(position, **data)
            
        def getHeightOfComponents(self):
            height = self.padding
            if self.pages == []: return self.padding
            for component in self.getLastPage().childComponents:
                height += component.computedHeight + (2*self.margin)
            return height
            
        def addChild(self, component):
            componentHeight = self.getHeightOfComponents()
            if self.pages == [] or componentHeight + (component.computedHeight + 2*self.margin) + (2*self.padding) >= self.pageHolder.computedHeight:
                self.addPage(self.generatePage(color=self.backgroundColor))
                componentHeight = self.getHeightOfComponents()
            component.setPosition([self.padding, componentHeight])
            self.getLastPage().addChild(component)
            component.refresh()
            
        def removeChild(self, component):
            super(GUI.ListPagedContainer, self).removeChild(component)
            if self.pages[0].childComponents == []:
                self.removePage(0)
                self.goToPage()
            
    class ButtonRow(Container):
        def __init__(self, position, **data):
            self.padding = data.get("padding", 0)
            self.margin = data.get("margin", 0)
            super(GUI.ButtonRow, self).__init__(position, **data)
            
        def getLastComponent(self):
            if len(self.childComponents) > 0:
                return self.childComponents[len(self.childComponents) - 1]
            return None
            
        def addChild(self, component):
            component.height = self.computedHeight - (2*self.padding)
            last = self.getLastComponent()
            if last != None:
                component.setPosition([last.computedPosition[0]+last.computedWidth+self.margin, self.padding])
            else:
                component.setPosition([self.padding, self.padding])
            component.setDimensions()
            super(GUI.ButtonRow, self).addChild(component)
            
        def removeChild(self, component):
            super(GUI.ButtonRow, self).removeChild(component)
            childrenCopy = self.childComponents[:]
            self.clearChildren()
            for child in childrenCopy:
                self.addChild(child)
                
    class ScrollIndicator(Component):
        def __init__(self, scrollCont, position, color, **data):
            super(GUI.ScrollIndicator, self).__init__(position, **data)
            self.internalClickOverrides["onIntermediateUpdate"] = (self.dragScroll, ())
            self.internalClickOverrides["onClick"] = (self.clearScrollParams, ())
            self.internalClickOverrides["onLongClick"] = (self.clearScrollParams, ())
            self.scrollContainer = scrollCont
            self.color = color
            self.lastClickCoord = None
            
        def update(self):
            self.pct = 1.0 * self.scrollContainer.computedHeight / (self.scrollContainer.maxOffset - self.scrollContainer.minOffset)
            self.slide = -self.scrollContainer.offset*self.pct
            self.sih = self.pct * self.computedHeight
            
        def render(self, largerSurface):
            self.surface.fill(self.color)
            pygame.draw.rect(self.surface, state.getColorPalette().getColor("accent"), [0, int(self.slide*(1.0*self.computedHeight/self.scrollContainer.computedHeight)), self.computedWidth, int(self.sih)])
            super(GUI.ScrollIndicator, self).render(largerSurface)
            
        def clearScrollParams(self):
            self.lastClickCoord = None
            
        def dragScroll(self):
            if self.lastClickCoord != None:
                ydist = self.innerClickCoordinates[1] - self.lastClickCoord[1]
                self.scrollContainer.scroll(ydist)
            self.lastClickCoord = self.innerClickCoordinates
                            
    class ScrollableContainer(Container):
        def __init__(self, position, **data): 
            self.scrollAmount = data.get("scrollAmount", state.getGUI().height / 8) 
            super(GUI.ScrollableContainer, self).__init__(position, **data)
            self.container = GUI.Container((0, 0), transparent=True, width=self.computedWidth-20, height=self.computedHeight)
            self.scrollBar = GUI.Container((self.computedWidth-20, 0), width=20, height=self.computedHeight)
            self.scrollUpBtn = GUI.Image((0, 0), path="res/scrollup.png", width=20, height=40,
                                         onClick=self.scroll, onClickData=(self.scrollAmount,))
            self.scrollDownBtn = GUI.Image((0, self.scrollBar.computedHeight-40), path="res/scrolldown.png", width=20, height=40,
                                         onClick=self.scroll, onClickData=(-self.scrollAmount,))
            self.scrollIndicator = GUI.ScrollIndicator(self, (0, 40), self.backgroundColor, width=20, height=self.scrollBar.computedHeight-80, border=1, borderColor=state.getColorPalette().getColor("item"))
            if self.computedHeight >= 120:
                self.scrollBar.addChild(self.scrollIndicator)
            self.scrollBar.addChild(self.scrollUpBtn)
            self.scrollBar.addChild(self.scrollDownBtn)
            super(GUI.ScrollableContainer, self).addChild(self.container)
            super(GUI.ScrollableContainer, self).addChild(self.scrollBar)
            self.offset = 0
            self.minOffset = 0
            self.maxOffset = self.container.computedHeight
            self.scrollIndicator.update()
            
        def scroll(self, amount):
            if amount < 0:
                if self.offset - amount - self.computedHeight <= -self.maxOffset:
                    return
            else:
                if self.offset + amount > self.minOffset:
                    #self.offset = -self.minOffset
                    return
            for child in self.container.childComponents:
                child.position[1] = child.computedPosition[1]+amount
            self.offset += amount
            self.scrollIndicator.update()
                
        def getVisibleChildren(self):
            visible = []
            for child in self.container.childComponents:
                if child.computedPosition[1]+child.computedHeight >= -10 and child.computedPosition[1]-child.computedHeight <= self.computedHeight + 10:
                    visible.append(child)
            return visible
        
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if not self.checkClick(mouseEvent, offsetX, offsetY):
                return None
            clicked = self.scrollBar.getClickedChild(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1])
            if clicked != None: return clicked
            visible = self.getVisibleChildren()
            currChild = len(visible)
            while currChild > 0:
                currChild -= 1
                child = visible[currChild]
                if "SKIP_CHILD_CHECK" in child.__dict__:
                    if child.SKIP_CHILD_CHECK:
                        if child.checkClick(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1]):
                            return child
                        else:
                            continue
                    else:
                        subCheck = child.getClickedChild(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1])
                        if subCheck == None: continue
                        return subCheck
                else:
                    if child.checkClick(mouseEvent, offsetX + self.computedPosition[0], offsetY + self.computedPosition[1]):
                        return child
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
        def addChild(self, component):
            if component.computedPosition[1] < self.minOffset: self.minOffset = component.computedPosition[1]
            if component.computedPosition[1]+component.computedHeight > self.maxOffset: self.maxOffset = component.computedPosition[1]+component.computedHeight
            self.container.addChild(component)
            self.scrollIndicator.update()
            
        def removeChild(self, component):
            self.container.removeChild(component)
            if component.computedPosition[1] == self.minOffset:
                self.minOffset = 0
                for comp in self.container.childComponents:
                    if comp.computedPosition[1] < self.minOffset: self.minOffset = comp.computedPosition[1]
            if component.computedPosition[1] == self.maxOffset:
                self.maxOffset = self.computedHeight
                for comp in self.container.childComponents:
                    if comp.computedPosition[1]+comp.computedHeight > self.maxOffset: self.maxOffset = comp.computedPosition[1]+comp.computedHeight
            self.scrollIndicator.update()
                    
        def clearChildren(self):
            self.container.clearChildren()
            self.maxOffset = self.computedHeight
            self.offset = 0
            self.scrollIndicator.update()
            
        def render(self, largerSurface):
            super(GUI.ScrollableContainer, self).render(largerSurface)
            
        def refresh(self, children=True):
            #super(GUI.ScrollableContainer, self).refresh()
            self.minOffset = 0
            for comp in self.container.childComponents:
                if comp.computedPosition[1] < self.minOffset: self.minOffset = comp.computedPosition[1]
            self.maxOffset = self.computedHeight
            for comp in self.container.childComponents:
                if comp.computedPosition[1]+comp.computedHeight > self.maxOffset: self.maxOffset = comp.computedPosition[1]+comp.computedHeight
            self.scrollIndicator.update()
            self.container.refresh(children)
            
    class ListScrollableContainer(ScrollableContainer):
        def __init__(self, position, **data):
            self.margin = data.get("margin", 0)
            super(GUI.ListScrollableContainer, self).__init__(position, **data)
            
        def getCumulativeHeight(self):
            height = 0
            if self.container.childComponents == []: 0
            for component in self.container.childComponents:
                height += component.computedHeight + self.margin
            return height
            
        def addChild(self, component):
            component.position[1] = self.getCumulativeHeight()
            component.setDimensions()
            super(GUI.ListScrollableContainer, self).addChild(component)
            
        def removeChild(self, component):
            super(GUI.ListScrollableContainer, self).removeChild(component)
            childrenCopy = self.container.childComponents[:]
            self.container.childComponents = []
            for child in childrenCopy:
                self.addChild(child)
                
    class TextScrollableContainer(ScrollableContainer):
        def __init__(self, position, textComponent=DEFAULT, **data):
            #Defaults to creating a text component.
            data["scrollAmount"] = data.get("lineHeight", textComponent.lineHeight if textComponent != DEFAULT else 16)
            super(GUI.TextScrollableContainer, self).__init__(position, **data)
            if textComponent == DEFAULT:
                self.textComponent = GUI.ExpandingMultiLineText((0, 0), "", state.getColorPalette().getColor("item"), width=self.container.computedWidth, height=self.container.computedHeight, scroller=self)
            else:
                self.textComponent = textComponent
                if self.textComponent.computedWidth == self.computedWidth:
                    self.textComponent.width = self.container.width
                    #self.textComponent.refresh()
            self.addChild(self.textComponent)
            
        def getTextComponent(self):
            return self.textComponent
        
    class MultiLineTextEntryField(ListScrollableContainer):
        def __init__(self, position, initialText="", **data):
            if "border" not in data:
                data["border"] = 1
                data["borderColor"] = state.getColorPalette().getColor("accent")
            data["onClick"] = self.activateLast
            data["onClickData"] = ()
            super(GUI.MultiLineTextEntryField, self).__init__(position, **data)
            self.lineHeight = data.get("lineHeight", 20)
            self.maxLines = data.get("maxLines", -2)
            self.backgroundColor = data.get("backgroundColor", state.getColorPalette().getColor("background"))
            self.textColor = data.get("color", state.getColorPalette().getColor("item"))
            self.textFields = []
            self.wrappedLines = []
            self.currentField = -1
            self.setText(initialText)
            
        def activateLast(self):
            self.currentField = len(self.textFields) - 1
            self.textFields[self.currentField].activate()
            
        def refresh(self):
            super(GUI.MultiLineTextEntryField, self).refresh()
            self.clearChildren()
            for tf in self.textFields:
                self.addChild(tf)
            
        def setCurrent(self, field):
            self.currentField = self.textFields.index(field)
            
        def addField(self, initial_text):
            if len(self.textFields) == self.maxLines: 
                return
            field = GUI.TextEntryField((0, 0), initial_text, width=self.container.computedWidth, height=self.lineHeight,
                                       backgroundColor=self.backgroundColor, textColor=self.textColor)
            field.border = 0
            field.MULTILINE = self
            self.currentField += 1
            self.textFields.insert(self.currentField, field)
            field.activate()
            self.refresh()
            
#         def prependToNextField(self, text): #HOLD FOR NEXT RELEASE
#             print "Prep: "+text
#             self.currentField += 1
#             currentText = self.textFields[self.currentField].textComponent.text
#             self.textFields[self.currentField].textComponent.text = ""
#             self.textFields[self.currentField].indicatorPosition = 0
#             self.textFields[self.currentField].refresh()
#             self.textFields[self.currentField].activate()
#             for word in (" "+text+" "+currentText).split(" "):
#                 self.textFields[self.currentField].appendChar(word+" ")
#             self.textFields[self.currentField].refresh()
            
        def removeField(self, field):
            if self.currentField > 0:
                if self.textFields.index(field) == self.currentField:
                    self.currentField -= 1
                self.textFields.remove(field)
            self.refresh()
                
        def getDeleteChar(self):
            if self.currentField < len(self.textFields) - 1:
                c = ""
                try:
                    c = self.textFields[self.currentField + 1].textComponent.text[0]
                    self.textFields[self.currentField + 1].textComponent.text = self.textFields[self.currentField + 1].textComponent.text[1:]
                    self.textFields[self.currentField + 1].updateOverflow()
                    self.textFields[self.currentField + 1].refresh()
                except:
                    self.removeField(self.textFields[self.currentField + 1])
                return c
            return ""
                
        def getText(self):
            t = ""
            p = 0
            for ftext in [f.getText() for f in self.textFields]:
                if p in self.wrappedLines:
                    t += ftext
                else:
                    t += ftext + "\n"
                p += 1
            t.rstrip("\n")
            return t
        
        def clear(self):
            self.textFields = []
            self.wrappedLines = []
            self.currentField = -1
            self.refresh()
            
        def setText(self, text):
            self.clear()
            if text == "":
                self.addField("")
            else:
                for line in text.replace("\r", "").split("\n"):
                    self.addField("")
                    line = line.rstrip()
                    words = line.split(" ")
                    oldN = self.currentField
                    for word in words:
                        self.textFields[self.currentField].appendChar(word)
                        self.textFields[self.currentField].appendChar(" ")
                    if oldN != self.currentField:
                        for n in range(oldN, self.currentField): self.wrappedLines.append(n)
                for field in self.textFields:
                    if field.overflow > 0:
                        field.textComponent.setText(field.textComponent.text.rstrip(" "))
                        field.updateOverflow()
            self.refresh()
            state.getKeyboard().deactivate()
   
    class FunctionBar(object):
        def __init__(self):
            self.container = GUI.Container((0, state.getGUI().height-40), background=state.getColorPalette().getColor("background"), width=state.getGUI().width, height=40)
            self.launcherApp = state.getApplicationList().getApp("launcher")
            self.notificationMenu = GUI.NotificationMenu()
            self.recentAppSwitcher = GUI.RecentAppSwitcher()
            self.menu_button = GUI.Image((0, 0), surface=state.getIcons().getLoadedIcon("menu"), onClick=self.activateLauncher, onLongClick=Application.fullCloseCurrent)
            self.app_title_text = GUI.Text((42, 8), "Python OS 6", state.getColorPalette().getColor("item"), 20, onClick=self.toggleRecentAppSwitcher)
            self.clock_text = GUI.Text((state.getGUI().width-45, 8), self.formatTime(), state.getColorPalette().getColor("accent"), 20, onClick=self.toggleNotificationMenu, onLongClick=State.rescue) #Add Onclick Menu
            self.container.addChild(self.menu_button)
            self.container.addChild(self.app_title_text)
            self.container.addChild(self.clock_text)
    
        def formatTime(self):
            time = str(datetime.now())
            if time.startswith("0"): time = time[1:]
            return time[time.find(" ")+1:time.find(":", time.find(":")+1)]
        
        def render(self):
            if state.getNotificationQueue().new:
                self.clock_text.color = (255, 59, 59)
            self.clock_text.text = self.formatTime()
            self.clock_text.refresh()
            self.container.render(screen)
            
        def activateLauncher(self):
            if state.getActiveApplication() != self.launcherApp:
                self.launcherApp.activate()
            else:
                Application.fullCloseCurrent()
                
        def toggleNotificationMenu(self):
            if self.notificationMenu.displayed: 
                self.notificationMenu.hide()
                return
            else: 
                self.notificationMenu.display()
                
        def toggleRecentAppSwitcher(self):
            if self.recentAppSwitcher.displayed:
                self.recentAppSwitcher.hide()
                return
            else:
                self.recentAppSwitcher.display()
            
    class Keyboard(object):
        def __init__(self, textEntryField=None):
            self.shiftUp = False
            self.active = False
            self.textEntryField = textEntryField
            self.movedUI = False
            self._symbolFont = GUI.Font("res/symbols.ttf", 10, 20)
            if self.textEntryField.computedPosition[1] + self.textEntryField.computedHeight > 2*(state.getGUI().height/3) or self.textEntryField.data.get("slideUp", False):
                state.getActiveApplication().ui.setPosition((0, -80))
                self.movedUI = True
            self.baseContainer = None
            self.baseContainer = GUI.Container((0, 0), width=state.getGUI().width, height=state.getGUI().height/3)
            self.baseContainer.setPosition((0, 2*(state.getGUI().height/3)))
            self.keyWidth = self.baseContainer.computedWidth / 10
            self.keyHeight = self.baseContainer.computedHeight / 4
            use_ft = state.getTypingFont().ft_support
            #if use_ft:
            self.shift_sym = "⇧"
            self.enter_sym = "⏎"
            self.bkspc_sym = "⌫"
            self.delet_sym = "⌦"
#             else:
#                 self.shift_sym = "sh"
#                 self.enter_sym = "->"
#                 self.bkspc_sym = "<-"
#                 self.delet_sym = "del"
            self.keys1 = [["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
                         ["a", "s", "d", "f", "g", "h", "j", "k", "l", self.enter_sym],
                         [self.shift_sym, "z", "x", "c", "v", "b", "n", "m", ",", "."],
                         ["!", "?", " ", "", "", "", "", "-", "'", self.bkspc_sym]]
            self.keys2 = [["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
                         ["@", "#", "$", "%", "^", "&", "*", "(", ")", "_"],
                         ["=", "+", "\\", "/", "<", ">", "|", "[", "]", ":"],
                         [";", "{", "}", "", "", "", "", "-", "\"", self.delet_sym]]
            row = 0
            for symrow in self.keys1:
                sym = 0
                for symbol in symrow:
                    button = None
                    if symbol == "": 
                        sym += 1
                        continue
                    if symbol == " ":
                        button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), "", self.keys2[row][sym],
                                                    onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                    onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                    width=self.keyWidth*5, height=self.keyHeight, freetype=use_ft)
                    else:
                        if symbol == self.shift_sym or symbol == self.enter_sym or symbol == self.bkspc_sym or symbol == self.delet_sym:
                            button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), self.keys1[row][sym], self.keys2[row][sym],
                                                    onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                    onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                    width=self.keyWidth, height=self.keyHeight, border=1, borderColor=state.getColorPalette().getColor("accent"),
                                                    font=self._symbolFont, freetype=use_ft)
                        else:
                            button = GUI.KeyboardButton((sym * self.keyWidth, row * self.keyHeight), self.keys1[row][sym], self.keys2[row][sym],
                                                        onClick=self.insertChar, onClickData=(self.keys1[row][sym],), 
                                                        onLongClick=self.insertChar, onLongClickData=(self.keys2[row][sym],),
                                                        width=self.keyWidth, height=self.keyHeight,
                                                        freetype=use_ft)
                    self.baseContainer.addChild(button)
                    sym += 1
                row += 1
            
        def deactivate(self):
            self.active = False
            if self.movedUI:
                state.getActiveApplication().ui.position[1] = 0
            self.textEntryField = None
            
        def setTextEntryField(self, field):
            self.textEntryField = field
            self.active = True
            if self.textEntryField.computedPosition[1] + self.textEntryField.height > state.getGUI().height - self.baseContainer.computedHeight or self.textEntryField.data.get("slideUp", False):
                state.getActiveApplication().ui.setPosition((0, -self.baseContainer.computedHeight))
                self.movedUI = True
            
        def getEnteredText(self):
            return self.textEntryField.getText()
                
        def insertChar(self, char):
            if char == self.shift_sym:
                self.shiftUp = not self.shiftUp
                for button in self.baseContainer.childComponents:
                    if self.shiftUp:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.upper()
                    else:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.lower()
                    button.primaryTextComponent.refresh()
                return
            if char == self.enter_sym:
                mult = self.textEntryField.MULTILINE
                self.deactivate()
                if mult != None:
                    mult.textFields[mult.currentField].doBlink = False
                    mult.addField("")
                return
            if char == self.bkspc_sym:
                self.textEntryField.backspace()
                return
            if char == self.delet_sym:
                self.textEntryField.delete()
            else:
                if self.shiftUp:
                    self.textEntryField.appendChar(char.upper())
                    self.shiftUp = False
                    for button in self.baseContainer.childComponents:
                        button.primaryTextComponent.text = button.primaryTextComponent.text.lower()
                        button.primaryTextComponent.refresh()
                else:
                    self.textEntryField.appendChar(char)
                    
        def render(self, largerSurface):
            self.baseContainer.render(largerSurface)
            
    class Overlay(object):
        def __init__(self, position, **data):
            self.position = list(position)
            self.displayed = False
            self.width = int(int(data.get("width").rstrip("%")) * (state.getActiveApplication().ui.width/100.0)) if isinstance(data.get("width"), str) else data.get("width", state.getGUI().width)
            self.height = int(int(data.get("height").rstrip("%")) * (state.getActiveApplication().ui.height/100.0)) if isinstance(data.get("height"), str) else data.get("height", state.getGUI().height-40)
            self.color = data.get("color", state.getColorPalette().getColor("background"))
            self.baseContainer = GUI.Container((0, 0), width=state.getGUI().width, height=state.getActiveApplication().ui.height, color=(0, 0, 0, 0), onClick=self.hide)
            self.container = data.get("container", GUI.Container(self.position[:], width=self.width, height=self.height, color=self.color))
            self.baseContainer.addChild(self.container)
            self.application = state.getActiveApplication()
            
        def display(self):
            self.application = state.getActiveApplication()
            self.application.ui.setDialog(self)
            self.displayed = True
        
        def hide(self):
            self.application.ui.clearDialog()
            self.application.ui.refresh()
            self.displayed = False
            
        def addChild(self, child):
            self.container.addChild(child)
            
    class Dialog(Overlay):
        def __init__(self, title, text, actionButtons, onResponseRecorded=None, onResponseRecordedData=(), **data):
            super(GUI.Dialog, self).__init__((0, (state.getActiveApplication().ui.height/2)-65), height=data.get("height", 130),
                                             width=data.get("width", state.getGUI().width), 
                                             color=data.get("color", state.getColorPalette().getColor("background")))
            self.container.border = 3
            self.container.borderColor = state.getColorPalette().getColor("item")
            self.container.refresh()
            self.application = state.getActiveApplication()
            self.title = title
            self.text = text
            self.response = None
            self.buttonList = GUI.Dialog.getButtonList(actionButtons, self) if isinstance(actionButtons[0], str) else actionButtons
            self.textComponent = GUI.MultiLineText((2, 2), self.text, state.getColorPalette().getColor("item"), 16, width=self.container.computedWidth-4, height=96)
            self.buttonRow = GUI.ButtonRow((0, 96), width=state.getGUI().width, height=40, color=(0, 0, 0, 0), padding=0, margin=0)
            for button in self.buttonList:
                self.buttonRow.addChild(button)
            self.addChild(self.textComponent)
            self.addChild(self.buttonRow)
            self.onResponseRecorded = onResponseRecorded
            self.onResponseRecordedData = onResponseRecordedData
    
        def display(self):
            state.getFunctionBar().app_title_text.setText(self.title)
            self.application.ui.setDialog(self)
        
        def hide(self):
            state.getFunctionBar().app_title_text.setText(state.getActiveApplication().title)
            self.application.ui.clearDialog()
            self.application.ui.refresh()
            
        def recordResponse(self, response):
            self.response = response
            self.hide()
            if self.onResponseRecorded != None:
                if self.onResponseRecordedData != None:
                    self.onResponseRecorded(*((self.onResponseRecordedData)+(self.response,)))
            
        def getResponse(self):
            return self.response
        
        @staticmethod
        def getButtonList(titles, dialog):
            blist = []
            for title in titles:
                blist.append(GUI.Button((0, 0), title, state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                                        width=dialog.container.computedWidth/len(titles), height=40,
                                        onClick=dialog.recordResponse, onClickData=(title,)))
            return blist
            
    class OKDialog(Dialog):
        def __init__(self, title, text, onResposeRecorded=None, onResponseRecordedData=()):
            okbtn = GUI.Button((0, 0), "OK", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=state.getGUI().width, height=40, onClick=self.recordResponse, onClickData=("OK",))
            super(GUI.OKDialog, self).__init__(title, text, [okbtn], onResposeRecorded)
            
    class ErrorDialog(Dialog):
        def __init__(self, text, onResposeRecorded=None, onResponseRecordedData=()):
            okbtn = GUI.Button((0, 0), "Acknowledged", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=state.getGUI().width, height=40, onClick=self.recordResponse, onClickData=("Acknowledged",))
            super(GUI.ErrorDialog, self).__init__("Error", text, [okbtn], onResposeRecorded)
            self.container.backgroundColor = state.getColorPalette().getColor("error")
            
    class WarningDialog(Dialog):
        def __init__(self, text, onResposeRecorded=None, onResponseRecordedData=()):
            okbtn = GUI.Button((0, 0), "OK", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=state.getGUI().width, height=40, onClick=self.recordResponse, onClickData=("OK",))
            super(GUI.WarningDialog, self).__init__("Warning", text, [okbtn], onResposeRecorded)
            self.container.backgroundColor = state.getColorPalette().getColor("warning")
            
    class YNDialog(Dialog):
        def __init__(self, title, text, onResponseRecorded=None, onResponseRecordedData=()):
            ybtn = GUI.Button((0, 0), "Yes", (200, 250, 200), (50, 50, 50), 18,
                               width=(state.getGUI().width/2), height=40, onClick=self.recordResponse, onClickData=("Yes",))
            nbtn = GUI.Button((0, 0), "No", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=(state.getGUI().width/2), height=40, onClick=self.recordResponse, onClickData=("No",))
            super(GUI.YNDialog, self).__init__(title, text, [ybtn, nbtn], onResponseRecorded)
            self.onResponseRecordedData = onResponseRecordedData
            
    class OKCancelDialog(Dialog):
        def __init__(self, title, text, onResponseRecorded=None, onResponseRecordedData=()):
            okbtn = GUI.Button((0, 0), "OK", state.getColorPalette().getColor("background"), state.getColorPalette().getColor("item"), 18,
                               width=state.getGUI().width/2, height=40, onClick=self.recordResponse, onClickData=("OK",))
            cancbtn = GUI.Button((0, 0), "Cancel", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=state.getGUI().width/2, height=40, onClick=self.recordResponse, onClickData=("Cancel",))
            super(GUI.OKCancelDialog, self).__init__(title, text, [okbtn, cancbtn], onResponseRecorded, onResponseRecordedData)
            
    class AskDialog(Dialog):
        def __init__(self, title, text, onResposeRecorded=None, onResponseRecordedData=()):
            okbtn = GUI.Button((0, 0), "OK", state.getColorPalette().getColor("background"), state.getColorPalette().getColor("item"), 18,
                               width=state.getGUI().width/2, height=40, onClick=self.returnRecordedResponse)
            cancelbtn = GUI.Button((0, 0), "Cancel", state.getColorPalette().getColor("item"), state.getColorPalette().getColor("background"), 18,
                               width=state.getGUI().width/2, height=40, onClick=self.recordResponse, onClickData=("Cancel",))
            super(GUI.AskDialog, self).__init__(title, text, [okbtn, cancelbtn], onResposeRecorded, onResponseRecordedData)
            self.textComponent.computedHeight -= 20
            self.textComponent.refresh()
            self.textEntryField = GUI.TextEntryField((0, 80), width=self.container.computedWidth, height=20)
            self.container.addChild(self.textEntryField)
            
        def returnRecordedResponse(self):
            self.recordResponse(self.textEntryField.getText())
            
    class CustomContentDialog(Dialog):
        def __init__(self, title, customComponent, actionButtons, onResponseRecorded=None, btnPad=0, btnMargin=5, **data):
            self.application = state.getActiveApplication()
            self.title = title
            self.response = None
            self.baseContainer = GUI.Container((0, 0), width=state.getGUI().width, height=state.getActiveApplication().ui.height, color=(0, 0, 0, 0.5))
            self.container = customComponent
            self.buttonList = GUI.Dialog.getButtonList(actionButtons, self) if isinstance(actionButtons[0], str) else actionButtons
            self.buttonRow = GUI.ButtonRow((0, self.container.computedHeight-33), width=self.container.computedWidth, height=40, color=(0, 0, 0, 0), padding=btnPad, margin=btnMargin)
            for button in self.buttonList:
                self.buttonRow.addChild(button)
            self.container.addChild(self.buttonRow)
            self.baseContainer.addChild(self.container)
            self.onResponseRecorded = onResponseRecorded
            self.data = data
            self.onResponseRecordedData = data.get("onResponseRecordedData", ())
            
    class NotificationMenu(Overlay):        
        def __init__(self):
            super(GUI.NotificationMenu, self).__init__(("20%", "25%"), width="80%", height="75%", color=(20, 20, 20, 200))
            self.text = GUI.Text((1, 1), "Notifications", (200, 200, 200), 18)
            self.clearAllBtn = GUI.Button((self.width-50, 0), "Clear", (200, 200, 200), (20, 20, 20), width=50, height=20, onClick=self.clearAll)
            self.nContainer = GUI.ListScrollableContainer((0, 20), width="80%", height=self.height-20, transparent=True, margin=5)
            self.addChild(self.text)
            self.addChild(self.clearAllBtn)
            self.addChild(self.nContainer)
            self.refresh()
            
        def refresh(self):
            self.nContainer.clearChildren()
            for notification in state.getNotificationQueue().notifications:
                self.nContainer.addChild(notification.getContainer())
                
        def display(self):
            self.refresh()
            state.getNotificationQueue().new = False
            state.getFunctionBar().clock_text.color = state.getColorPalette().getColor("accent")
            super(GUI.NotificationMenu, self).display()
            
        def clearAll(self):
            state.getNotificationQueue().clear()
            self.refresh()
            
    class RecentAppSwitcher(Overlay):
        def __init__(self):
            super(GUI.RecentAppSwitcher, self).__init__((0, screen.get_height()-100), height=60)
            self.container.border = 1
            self.container.borderColor = state.getColorPalette().getColor("item")
            
        def populate(self):
            self.container.clearChildren()
            self.recent_pages = GUI.PagedContainer((20, 0), width=self.width-40, height=60, hideControls=True)
            self.recent_pages.addPage(self.recent_pages.generatePage())
            self.btnLeft = GUI.Button((0, 0), "<", state.getColorPalette().getColor("accent"), state.getColorPalette().getColor("item"), 20, width=20, height=60,
                                      onClick=self.recent_pages.pageLeft)
            self.btnRight = GUI.Button((self.width-20, 0), ">", state.getColorPalette().getColor("accent"), state.getColorPalette().getColor("item"), 20, width=20, height=60,
                                      onClick=self.recent_pages.pageRight)
            per_app = (self.width-40)/4
            current = 0
            for app in state.getApplicationList().activeApplications:
                if app != state.getActiveApplication() and app.parameters.get("persist", True) and app.name != "home":
                    if current >= 4:
                        current = 0
                        self.recent_pages.addPage(self.recent_pages.generatePage())
                    cont = GUI.Container((per_app*current, 0), transparent=True, width=per_app, height=self.height, border=1, borderColor=state.getColorPalette().getColor("item"),
                                         onClick=self.activate, onClickData=(app,), onLongClick=self.closeAsk, onLongClickData=(app,))
                    cont.SKIP_CHILD_CHECK = True
                    icon = app.getIcon()
                    if not icon: icon = state.getIcons().getLoadedIcon("unknown")
                    img = GUI.Image((0, 5), surface=icon)
                    img.position[0] = GUI.getCenteredCoordinates(img, cont)[0]
                    name = GUI.Text((0, 45), app.title, state.getColorPalette().getColor("item"), 10)
                    name.position[0] = GUI.getCenteredCoordinates(name, cont)[0]
                    cont.addChild(img)
                    cont.addChild(name)                    
                    self.recent_pages.addChild(cont)
                    current += 1
            if len(self.recent_pages.getPage(0).childComponents) == 0:
                notxt = GUI.Text((0, 0), "No Recent Apps", state.getColorPalette().getColor("item"), 16)
                notxt.position = GUI.getCenteredCoordinates(notxt, self.recent_pages.getPage(0))
                self.recent_pages.addChild(notxt)
            self.recent_pages.goToPage()
            self.addChild(self.recent_pages)
            self.addChild(self.btnLeft)
            self.addChild(self.btnRight)
            
        def display(self):
            self.populate()
            super(GUI.RecentAppSwitcher, self).display()
                    
        def activate(self, app):
            self.hide()
            app.activate()
            
        def closeAsk(self, app):
            GUI.YNDialog("Close", "Are you sure you want to close the app "+app.title+"?", self.close, (app,)).display()
            
        def close(self, app, resp):
            if resp == "Yes":
                app.deactivate(False)
                self.hide()
                if state.getActiveApplication() == state.getApplicationList().getApp("launcher"):
                    Application.fullCloseCurrent()
            
            
    class Selector(Container):      
        def __init__(self, position, items, **data):
            self.onValueChanged = data.get("onValueChanged", Application.dummy)
            self.onValueChangedData = data.get("onValueChangedData", ())
            self.overlay = GUI.Overlay((20, 20), width=state.getGUI().width-40, height=state.getGUI().height-80)
            self.overlay.container.border = 1
            self.scroller = GUI.ListScrollableContainer((0, 0), transparent=True, width=self.overlay.width, height=self.overlay.height, scrollAmount=20)
            for comp in self.generateItemSequence(items, 14, state.getColorPalette().getColor("item")):
                self.scroller.addChild(comp)
            self.overlay.addChild(self.scroller)
            super(GUI.Selector, self).__init__(position, **data)
            self.eventBindings["onClick"] = self.showOverlay
            self.eventData["onClick"] = ()
            self.textColor = data.get("textColor", state.getColorPalette().getColor("item"))
            self.items = items
            self.currentItem = self.items[0]
            self.textComponent = GUI.Text((0, 0), self.currentItem, self.textColor, 14, onClick=self.showOverlay)
            self.textComponent.setPosition([2, GUI.getCenteredCoordinates(self.textComponent, self)[1]])
            self.addChild(self.textComponent)
            
        def showOverlay(self):
            self.overlay.display()
            
        def generateItemSequence(self, items, size=22, color=(0, 0, 0)):
            comps = []
            acc_height = 0
            for item in items:
                el_c = GUI.Container((0, acc_height), transparent=True, width=self.overlay.width, height=40,
                                     onClick=self.onSelect, onClickData=(item,), border=1, borderColor=(20, 20, 20))
                elem = GUI.Text((2, 0), item, color, size,
                                onClick=self.onSelect, onClickData=(item,))
                elem.position[1] = GUI.getCenteredCoordinates(elem, el_c)[1]
                el_c.addChild(elem)
                el_c.SKIP_CHILD_CHECK = True
                comps.append(el_c)
                acc_height += el_c.computedHeight
            return comps
            
        def onSelect(self, newVal):
            self.overlay.hide()
            self.currentItem = newVal
            self.textComponent.text = self.currentItem
            self.textComponent.refresh()
            self.onValueChanged(*(self.onValueChangedData + (newVal,)))
            
        def render(self, largerSurface):
            super(GUI.Selector, self).render(largerSurface)
            pygame.draw.circle(largerSurface, state.getColorPalette().getColor("accent"), (self.computedPosition[0]+self.computedWidth-(self.computedHeight/2)-2, self.computedPosition[1]+(self.computedHeight/2)), (self.computedHeight/2)-5)
                                     
        def getClickedChild(self, mouseEvent, offsetX=0, offsetY=0):
            if self.checkClick(mouseEvent, offsetX, offsetY):
                return self
            return None
        
        def getValue(self):
            return self.currentItem
        
class ImmersionUI(object):
    def __init__(self, app):
        self.application = app
        self.method = getattr(self.application.module, self.application.parameters["immersive"])
        self.onExit = None
        
    def launch(self, resp):
        if resp == "Yes":
            self.method(*(self, screen))
            if self.onExit != None:
                self.onExit()
        
    def start(self, onExit=None):
        self.onExit = onExit
        GUI.YNDialog("Fullscreen", "The application "+self.application.title+" is requesting total control of the UI. Launch?", self.launch).display()
        
class Application(object):  
    @staticmethod
    def dummy(*args, **kwargs): pass
        
    @staticmethod
    def getListings():
        return readJSON("apps/apps.json")
    
    @staticmethod
    def chainRefreshCurrent():
        if state.getActiveApplication() != None:
            state.getActiveApplication().chainRefresh()
    
    @staticmethod
    def setActiveApp(app="prev"):
        if app == "prev":
            app = state.getApplicationList().getMostRecentActive()
        state.setActiveApplication(app)
        state.getFunctionBar().app_title_text.setText(state.getActiveApplication().title)
        state.getGUI().repaint()
        state.getApplicationList().pushActiveApp(app)
        
    @staticmethod
    def fullCloseApp(app):
        app.deactivate(False)
        state.getApplicationList().getMostRecentActive().activate(fromFullClose=True)
        
    @staticmethod
    def fullCloseCurrent():
        if state.getActiveApplication().name != "home":
            Application.fullCloseApp(state.getActiveApplication())
    
    @staticmethod
    def removeListing(location):
        alist = Application.getListings()
        try: del alist[location]
        except: print("The application listing for " + location + " could not be removed.")
        listingsfile = open("apps/apps.json", "w")
        json.dump(alist, listingsfile)
        listingsfile.close()
        
    @staticmethod
    def install(packageloc):
        package = ZipFile(packageloc, "r")
        package.extract("app.json", "temp/")
        app_info = readJSON("temp/app.json")
        app_name = str(app_info.get("name"))
        if app_name not in list(state.getApplicationList().applications.keys()):
            os.mkdir(os.path.join("apps/", app_name))
        else:
            print("Upgrading "+app_name)
        package.extractall(os.path.join("apps/", app_name))
        package.close()
        alist = Application.getListings()
        alist[os.path.join("apps/", app_name)] = app_name
        listingsfile = open("apps/apps.json", "w")
        json.dump(alist, listingsfile)
        listingsfile.close()
        return app_name
    
    @staticmethod
    def registerDebugAppAsk():
        state.getApplicationList().getApp("files").getModule().FolderPicker((10, 10), width=220, height=260, onSelect=Application.registerDebugApp,
                                                                            startFolder="apps/").display()
        
    @staticmethod
    def registerDebugApp(path):
        app_info = readJSON(os.path.join(path, "app.json"))
        app_name = str(app_info.get("name"))
        alist = Application.getListings()
        alist[os.path.join("apps/", app_name)] = app_name
        listingsfile = open("apps/apps.json", "w")
        json.dump(alist, listingsfile)
        listingsfile.close()
        state.getApplicationList().reloadList()
        GUI.OKDialog("Registered", "The application from "+path+" has been registered on the system.").display()
    
    def __init__(self, location):
        self.parameters = {}
        self.location = location
        app_data = readJSON(os.path.join(location, "app.json").replace("\\", "/"))
        self.name = str(app_data.get("name"))
        self.title = str(app_data.get("title", self.name))
        self.version = float(app_data.get("version", 0.0))
        self.author = str(app_data.get("author", "No Author"))
        self.module = import_module("apps." + str(app_data.get("module", self.name))) 
        self.module.state = state
        self.file = None
        try:
            self.mainMethod = getattr(self.module, str(app_data.get("main"))) 
        except:
            self.mainMethod = Application.dummy
        try: self.parameters = app_data.get("more")
        except: pass
        self.description = app_data.get("description", "No Description.")
        #Immersion check
        if "immersive" in self.parameters:
            self.immersionUI = ImmersionUI(self)
        else:
            self.immersionUI = None
        #check for and load event handlers
        self.evtHandlers = {}
        if "onStart" in self.parameters: 
            self.evtHandlers["onStartReal"] = self.parameters["onStart"]
        self.evtHandlers["onStart"] = [self.onStart, ()]
        if "onStop" in self.parameters: self.evtHandlers["onStop"] = getattr(self.module, self.parameters["onStop"])
        if "onPause" in self.parameters: self.evtHandlers["onPause"] = getattr(self.module, self.parameters["onPause"])
        if "onResume" in self.parameters: self.evtHandlers["onResume"] = getattr(self.module, self.parameters["onResume"])
        if "onCustom" in self.parameters: self.evtHandlers["onCustom"] = getattr(self.module, self.parameters["onCustom"])
        if "onOSLaunch" in self.parameters: self.evtHandlers["onOSLaunch"] = getattr(self.module, self.parameters["onOSLaunch"])
        self.thread = Thread(self.mainMethod, **self.evtHandlers)
        self.ui = GUI.AppContainer(self)
        self.dataStore = DataStore(self)
        self.thread = Thread(self.mainMethod, **self.evtHandlers)
        
    def getModule(self):
        return self.module
        
    def chainRefresh(self):
        self.ui.refresh()
        
    def onStart(self):
        self.loadColorScheme()
        if "onStartReal" in self.evtHandlers and not self.evtHandlers.get("onStartBlock", False): getattr(self.module, self.evtHandlers["onStartReal"])(state, self)
        if self.evtHandlers.get("onStartBlock", False):
            self.evtHandlers["onStartBlock"] = False
                        
    def loadColorScheme(self):
        if "colorScheme" in self.parameters: 
            state.getColorPalette().setScheme(self.parameters["colorScheme"])
        else: state.getColorPalette().setScheme()
        self.ui.backgroundColor = state.getColorPalette().getColor("background")
        self.ui.refresh()
        
    def activate(self, **data):
        try:
            if data.get("noOnStart", False):
                self.evtHandlers["onStartBlock"] = True
            if state.getActiveApplication() == self: return
            if state.getApplicationList().getMostRecentActive() != None and not data.get("fromFullClose", False):
                state.getApplicationList().getMostRecentActive().deactivate()
            Application.setActiveApp(self)
            self.loadColorScheme()
            if self.thread in state.getThreadController().threads:
                self.thread.setPause(False)
            else:
                if self.thread.stop:
                    self.thread = Thread(self.mainMethod, **self.evtHandlers)
                state.getThreadController().addThread(self.thread)
        except:
            State.error_recovery("Application init error.", "App name: "+self.name)
            
    def getIcon(self):
        if "icon" in self.parameters:
            if self.parameters["icon"] == None:
                return False
            return state.getIcons().getLoadedIcon(self.parameters["icon"], self.location)
        else:
            return state.getIcons().getLoadedIcon("unknown")
        
    def deactivate(self, pause=True):
        if "persist" in self.parameters:
            if self.parameters["persist"] == False:
                pause = False
        if pause:
            self.thread.setPause(True)
        else:
            self.ui.clearChildren()
            self.thread.setStop()
            state.getApplicationList().closeApp(self)
        state.getColorPalette().setScheme()
        
    def uninstall(self):
        rmtree(self.location, True)
        Application.removeListing(self.location)
        
class ApplicationList(object):    
    def __init__(self):
        self.applications = {}
        self.activeApplications = []
        applist = Application.getListings()
        for key in list(dict(applist).keys()):
            try:
                self.applications[applist.get(key)] = Application(key)
            except:
                State.error_recovery("App init error: "+key, "NoAppDump")
            
    def getApp(self, name):
        if name in self.applications:
            return self.applications[name]
        else:
            return None
        
    def getApplicationList(self):
        return list(self.applications.values())
    
    def getApplicationNames(self):
        return list(self.applications.keys())
        
    def pushActiveApp(self, app):
        if app not in self.activeApplications:
            self.activeApplications.insert(0, app)
        else:
            self.switchLast(app)
        
    def closeApp(self, app=None):
        if app == None:
            if len(self.activeApplications) > 1:
                return self.activeApplications.pop(0)
        self.activeApplications.remove(app)
    
    def switchLast(self, app):
        if app == None: return
        self.activeApplications = [self.activeApplications.pop(self.activeApplications.index(app))] + self.activeApplications
        
    def getMostRecentActive(self):
        if len(self.activeApplications) > 0:
            return self.activeApplications[0]
    
    def getPreviousActive(self):
        if len(self.activeApplications) > 1:
            return self.activeApplications[1]
        
    def reloadList(self):
        applist = Application.getListings()
        for key in list(dict(applist).keys()):
            try:
                if (applist.get(key) not in list(self.applications.keys())) and not state.getActiveApplication().name == key:
                    self.applications[applist.get(key)] = Application(key)
            except:
                State.error_recovery("App init error: "+key, "NoAppDump")
        for key in list(self.applications.keys()):
            if key not in list(applist.values()):
                del self.applications[key]
        
class Notification(object):
    def __init__(self, title, text, **data):
        self.title = title
        self.text = text
        self.active = True
        self.source = data.get("source", None)
        self.image = data.get("image", None)
        if self.source != None:
            self.onSelectedMethod = data.get("onSelected", self.source.activate)
        else:
            self.onSelectedMethod = data.get("onSelected", Application.dummy)
        self.onSelectedData = data.get("onSelectedData", ())
        
    def onSelected(self):
        self.clear()
        state.getFunctionBar().toggleNotificationMenu()
        self.onSelectedMethod(*self.onSelectedData)
        
    def clear(self):
        self.active = False
        state.getNotificationQueue().sweep()
        state.getFunctionBar().notificationMenu.refresh()
        
    def getContainer(self, c_width=200, c_height=40):
        cont = GUI.Container((0, 0), width=c_width, height=c_height, transparent=True, onClick=self.onSelected, onLongClick=self.clear)
        if self.image != None:
            try:
                self.image.setPosition([0, 0])
                cont.addChild(self.image)
            except:
                if isinstance(self.image, pygame.Surface):
                    self.image = GUI.Image((0, 0), surface=self.image, onClick=self.onSelected)
                else:
                    self.image = GUI.Image((0, 0), path=self.image, onClick=self.onSelected)
        else:
            self.image = GUI.Image((0, 0), surface=state.getIcons().getLoadedIcon("unknown"), onClick=self.onSelected, onLongClick=self.clear)
        rtitle = GUI.Text((41, 0), self.title, (200, 200, 200), 20, onClick=self.onSelected, onLongClick=self.clear)
        rtxt = GUI.Text((41, 24), self.text, (200, 200, 200), 14, onClick=self.onSelected, onLongClick=self.clear)
        cont.addChild(self.image)
        cont.addChild(rtitle)
        cont.addChild(rtxt)
        return cont
    
class PermanentNotification(Notification):
    def clear(self):
        pass
    
    def forceClear(self):
        super(PermanentNotification, self).clear()
    
class NotificationQueue(object):
    def __init__(self):
        self.notifications = []
        self.new = False
        
    def sweep(self):
        for notification in self.notifications:
            if not notification.active:
                self.notifications.remove(notification)
                
    def push(self, notification):
        self.notifications.insert(0, notification)
        self.new = True
        
    def clear(self):
        self.notifications = []
        
class DataStore(object):
    def __init__(self, app):
        self.application = app
        self.dsPath = os.path.join("res/", app.name+".ds")
        
    def getStore(self):
        if not os.path.exists(self.dsPath):
            wf = open(self.dsPath, "w")
            json.dump({"dsApp": self.application.name}, wf)
            wf.close()
        rf = open(self.dsPath, "rU")
        self.data = json.loads((rf.read()))
        rf.close()
        return self.data
    
    def saveStore(self):
        wf = open(self.dsPath, "w")
        json.dump(self.data, wf)
        wf.close()
    
    def get(self, key, default=None):
        return self.getStore().get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
        self.saveStore()
        
    def __getitem__(self, itm):
        return self.get(itm)
    
    def __setitem__(self, key, val):
        self.set(key, val)
                
class State(object):                  
    def __init__(self, activeApp=None, colors=None, icons=None, controller=None, eventQueue=None, notificationQueue=None, functionbar=None, font=None, tFont=None, gui=None, appList=None, keyboard=None):   
        self.activeApplication = activeApp
        self.colorPalette = colors
        self.icons = icons
        self.threadController = controller
        self.eventQueue = eventQueue
        self.notificationQueue = notificationQueue
        self.functionBar = functionbar
        self.font = font
        self.typingFont = tFont
        self.appList = appList
        self.keyboard = keyboard
        self.recentAppSwitcher = None
        if gui == None: self.gui = GUI()
        if colors == None: self.colorPalette = GUI.ColorPalette()
        if icons == None: self.icons = GUI.Icons()
        if controller == None: self.threadController = Controller()
        if eventQueue == None: self.eventQueue = GUI.EventQueue()
        if notificationQueue == None: self.notificationQueue = NotificationQueue()
        if font == None: self.font = GUI.Font()
        if tFont == None: self.typingFont = GUI.Font("res/RobotoMono-Regular.ttf")
        
    def getActiveApplication(self): return self.activeApplication
    def getColorPalette(self): return self.colorPalette
    def getIcons(self): return self.icons
    def getThreadController(self): return self.threadController
    def getEventQueue(self): return self.eventQueue
    def getNotificationQueue(self): return self.notificationQueue
    def getFont(self): return self.font
    def getTypingFont(self): return self.typingFont
    def getGUI(self): return self.gui
    def getApplicationList(self): 
        if self.appList == None: self.appList = ApplicationList()
        return self.appList
    def getFunctionBar(self):
        if self.functionBar == None: self.functionBar = GUI.FunctionBar()
        return self.functionBar
    def getKeyboard(self): return self.keyboard
    
    def setActiveApplication(self, app): self.activeApplication = app
    def setColorPalette(self, colors): self.colorPalette = colors
    def setIcons(self, icons): self.icons = icons
    def setThreadController(self, controller): self.threadController = controller
    def setEventQueue(self, queue): self.eventQueue = queue
    def setNotificationQueue(self, queue): self.notificationQueue = queue
    def setFunctionBar(self, bar): self.functionBar = bar
    def setFont(self, font): self.font = font
    def setTypingFont(self, tfont): self.typingFont = tfont
    def setGUI(self, gui): self.gui = gui
    def setApplicationList(self, appList): self.appList = appList
    def setKeyboard(self, keyboard): self.keyboard = keyboard
    
    @staticmethod
    def getState():
        return state
        
    @staticmethod
    def exit():
        state.getThreadController().stopAllThreads()
        pygame.quit()
        os._exit(1)
        
    @staticmethod
    def rescue():
        global state
        rFnt = pygame.font.Font(None, 16)
        rClock = pygame.time.Clock()
        state.getNotificationQueue().clear()
        state.getEventQueue().clear()
        print("Recovery menu entered.")
        while True:
            rClock.tick(10)
            screen.fill([0, 0, 0])
            pygame.draw.rect(screen, [200, 200, 200], [0, 0, 280, 80])
            screen.blit(rFnt.render("Return to Python OS", 1, [20, 20, 20]), [40, 35])
            pygame.draw.rect(screen, [20, 200, 20], [0, 80, 280, 80])
            screen.blit(rFnt.render("Stop all apps and return", 1, [20, 20, 20]), [40, 115])
            pygame.draw.rect(screen, [20, 20, 200], [0, 160, 280, 80])
            screen.blit(rFnt.render("Stop current app and return", 1, [20, 20, 20]), [40, 195])
            pygame.draw.rect(screen, [200, 20, 20], [0, 240, 280, 80])
            screen.blit(rFnt.render("Exit completely", 1, [20, 20, 20]), [40, 275])
            pygame.display.flip()
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT or evt.type == pygame.KEYDOWN and evt.key == pygame.K_ESCAPE:
                    print("Quit signal detected.")
                    try: state.exit()
                    except:
                        pygame.quit()
                        exit()
                if evt.type == pygame.MOUSEBUTTONDOWN:
                    if evt.pos[1] >= 80:
                        if evt.pos[1] >= 160:
                            if evt.pos[1] >= 240:
                                print("Exiting.")
                                try: state.exit()
                                except:
                                    pygame.quit()
                                    exit()
                            else:
                                print("Stopping current app")
                                try:
                                    Application.fullCloseCurrent()
                                except:
                                    print("Regular stop failed!")
                                    Application.setActiveApp(state.getApplicationList().getApp("home"))
                                return
                        else:
                            print("Closing all active applications")
                            for a in state.getApplicationList().activeApplications:
                                try: a.deactivate()
                                except:
                                    print("The app "+str(a.name)+" failed to deactivate!")
                                    state.getApplicationList().activeApplications.remove(a)
                            state.getApplicationList().getApp("home").activate()
                            return
                    else:
                        print("Returning to Python OS.")
                        return
    
    @staticmethod       
    def error_recovery(message="Unknown", data=None):
        print(message)
        screen.fill([200, 100, 100])
        rf = pygame.font.Font(None, 24)
        sf = pygame.font.Font(None, 18)
        screen.blit(rf.render("Failure detected.", 1, (200, 200, 200)), [20, 20])
        f = open("temp/last_error.txt", "w")
        txt = "Python OS 6 Error Report\nTIME: "+str(datetime.now())
        txt += "\n\nOpen Applications: "+(str([a.name for a in state.getApplicationList().activeApplications]) if data != "NoAppDump" else "Not Yet Initialized")
        txt += "\nMessage: "+message
        txt += "\nAdditional Data:\n"
        txt += str(data)
        txt += "\n\nTraceback:\n"
        txt += format_exc()
        f.write(txt)
        f.close()
        screen.blit(sf.render("Traceback saved.", 1, (200, 200, 200)), [20, 80])
        screen.blit(sf.render("Location: temp/last_error.txt", 1, (200, 200, 200)), [20, 100])
        screen.blit(sf.render("Message:", 1, (200, 200, 200)), [20, 140])
        screen.blit(sf.render(message, 1, (200, 200, 200)), [20, 160])
        pygame.draw.rect(screen, [200, 200, 200], [0, 280, 240, 40])
        screen.blit(sf.render("Return to Python OS", 1, (20, 20, 20)), [20, 292])
        pygame.draw.rect(screen, [50, 50, 50], [0, 240, 240, 40])
        screen.blit(sf.render("Open Recovery Menu", 1, (200, 200, 200)), [20, 252])
        rClock = pygame.time.Clock()
        pygame.display.flip()
        while True:
            rClock.tick(10)
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT or evt.type == pygame.KEYDOWN and evt.key == pygame.K_ESCAPE:
                    try: state.exit()
                    except:
                        pygame.quit()
                        exit()
                if evt.type == pygame.MOUSEBUTTONDOWN:
                    if evt.pos[1] >= 280:
                        return
                    elif evt.pos[1] >= 240:
                        State.rescue()
                        return
    
    @staticmethod
    def main():
        while True:
            #Limit FPS
            state.getGUI().timer.tick(state.getGUI().update_interval)
            #Update event queue
            state.getEventQueue().check()
            #Refresh main thread controller
            state.getThreadController().run()
            #Paint UI
            if state.getActiveApplication() != None:
                try:
                    state.getActiveApplication().ui.render()
                except:
                    State.error_recovery("UI error.", "FPS: "+str(state.getGUI().update_interval))
                    Application.fullCloseCurrent()
            state.getFunctionBar().render()
            if state.getKeyboard() != None and state.getKeyboard().active:
                state.getKeyboard().render(screen)
            
            state.getGUI().refresh()
            #Check Events
            latestEvent = state.getEventQueue().getLatestComplete()
            if latestEvent != None:
                clickedChild = None
                if state.getKeyboard() != None and state.getKeyboard().active:
                    if latestEvent.pos[1] < state.getKeyboard().baseContainer.computedPosition[1]:
                        if state.getActiveApplication().ui.getClickedChild(latestEvent) == state.getKeyboard().textEntryField:
                            state.getKeyboard().textEntryField.onClick()
                        else:
                            state.getKeyboard().deactivate()
                        continue
                    clickedChild = state.getKeyboard().baseContainer.getClickedChild(latestEvent)
                    if clickedChild == None:
                        clickedChild = state.getActiveApplication().ui.getClickedChild(latestEvent)
                    if clickedChild == None and state.getKeyboard().textEntryField.computedPosition == [0, 0] and state.getKeyboard().textEntryField.checkClick(latestEvent):
                        clickedChild = state.getKeyboard().textEntryField
                else:
                    if latestEvent.pos[1] < state.getGUI().height - 40:
                        if state.getActiveApplication() != None:
                            clickedChild = state.getActiveApplication().ui.getClickedChild(latestEvent)
                    else:
                        clickedChild = state.getFunctionBar().container.getClickedChild(latestEvent)
                if clickedChild != None:
                    try:
                        if isinstance(latestEvent, GUI.LongClickEvent):
                            clickedChild.onLongClick()
                        else:
                            if isinstance(latestEvent, GUI.IntermediateUpdateEvent):
                                clickedChild.onIntermediateUpdate()
                            else:
                                clickedChild.onClick()
                    except:
                        State.error_recovery("Event execution error", "Click event: "+str(latestEvent))
            
    @staticmethod
    def state_shell():
        #For debugging purposes only. Do not use in actual code!
        print("Python OS 6 State Shell. Type \"exit\" to quit.")
        user_input = input ("S> ")
        while user_input != "exit":
            if not user_input.startswith("state.") and user_input.find("Static") == -1: 
                if user_input.startswith("."):
                    user_input = "state" + user_input
                else:
                    user_input = "state." + user_input
            print(eval(user_input, {"state": state, "Static": State}))
            user_input = input("S> ")
        State.exit(True)
        
    
if __name__ == "__main__":
    try:
        settings = readJSON("res/settings.json")
    except:
        print("Error loading settings from res/settings.json")
    state = State()
    globals()["state"] = state
    builtins.state = state
    #TEST
    #print(state)
    for app in state.getApplicationList().getApplicationList():
        if app.evtHandlers.get("onOSLaunch", None) != None:
            try:
                app.evtHandlers.get("onOSLaunch")()
            except:
                State.error_recovery("App startup task failed to run properly.", "App: " + str(app.name))             
    state.getApplicationList().getApp("home").activate()
    try:
        State.main()
    except:
        State.error_recovery("Fatal system error.")
