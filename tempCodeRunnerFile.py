# simulation.py
# Adaptive Traffic Signal Simulation with ambulance priority (preemption)

import random
import math
import time
import threading
import pygame
import sys
import os

# ----------------------
# CONFIG / DEFAULTS
# ----------------------
defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60

noOfSignals = 4
simTime = 400
timeElapsed = 0

currentGreen = 0
nextGreen = (currentGreen + 1) % noOfSignals
currentYellow = 0

speeds = {
    'car': 4.5,
    'bus': 3.8,
    'truck': 3.8,
    'rickshaw': 4.0,
    'bike': 5.0,
    'ambulance': 6.0
}

carTime = 2
busTime = 3
truckTime = 3
rickshawTime = 1
bikeTime = 1
ambulanceTime = 1

noOfLanes = 2
detectionTime = 5
AMBULANCE_DETECT_DIST = 200

x = {'right':[0,0,0], 'down':[755,727,697], 'left':[1400,1400,1400], 'up':[602,627,657]}
y = {'right':[348,370,398], 'down':[0,0,0], 'left':[498,466,436], 'up':[800,800,800]}

vehicles = {
    'right': {0:[], 1:[], 2:[], 'crossed':0},
    'down':  {0:[], 1:[], 2:[], 'crossed':0},
    'left':  {0:[], 1:[], 2:[], 'crossed':0},
    'up':    {0:[], 1:[], 2:[], 'crossed':0}
}

vehicleTypes = {0:'car', 1:'bus', 2:'truck', 3:'rickshaw', 4:'bike', 5:'ambulance'}
directionNumbers = {0:'right', 1:'down', 2:'left', 3:'up'}

signalCoods = [(530,230),(810,230),(810,570),(530,570)]
signalTimerCoods = [(530,210),(810,210),(810,550),(530,550)]
vehicleCountCoods = [(480,210),(880,210),(880,550),(480,550)]

stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}
stops = {'right': [580,580,580], 'down': [320,320,320], 'left': [810,810,810], 'up': [545,545,545]}

gap = 15

# ----------------------
# Pygame init / assets
# ----------------------
pygame.init()
SCREEN_W, SCREEN_H = 1400, 800
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("SIMULATION")

bg_path = os.path.join('images', 'mod_int.png')
background = pygame.image.load(bg_path).convert() if os.path.exists(bg_path) else pygame.Surface((SCREEN_W, SCREEN_H))
if not os.path.exists(bg_path):
    background.fill((180,180,180))

def load_image(path, fallback_size=(40,20), alpha=True):
    if os.path.exists(path):
        img = pygame.image.load(path)
        return img.convert_alpha() if alpha else img.convert()
    else:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill((200,200,200,255))
        return surf

redSignal = load_image(os.path.join('images','signals','red.png'), (40,40))
yellowSignal = load_image(os.path.join('images','signals','yellow.png'), (40,40))
greenSignal = load_image(os.path.join('images','signals','green.png'), (40,40))

font = pygame.font.Font(None, 30)
simulation = pygame.sprite.Group()

DASHBOARD_W = 300
dashboard_rect = pygame.Rect(SCREEN_W-DASHBOARD_W, 0, DASHBOARD_W, SCREEN_H)

# ----------------------
# TrafficSignal & Vehicle
# ----------------------
class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0
        self.willTurn = will_turn
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1

        path = os.path.join("images", direction, vehicleClass + ".png")
        fallback_size = (40,20)
        if vehicleClass in ('bus','truck'): fallback_size = (80,40)
        elif vehicleClass == 'bike': fallback_size = (24,12)
        elif vehicleClass == 'ambulance': fallback_size = (48,24)
        self.originalImage = load_image(path, fallback_size)
        self.currentImage = self.originalImage.copy()
        simulation.add(self)

    def move(self):
        lane_vehicles = vehicles[self.direction][self.lane]
        idx = lane_vehicles.index(self)
        if idx > 0:
            front_vehicle = lane_vehicles[idx-1]
            if front_vehicle.crossed==0:
                if self.direction in ['right','left']:
                    front_edge = front_vehicle.x + front_vehicle.currentImage.get_width() if self.direction=='right' else front_vehicle.x
                    self.stop = front_edge - self.currentImage.get_width() - gap if self.direction=='right' else front_edge + self.currentImage.get_width() + gap
                else:
                    front_edge = front_vehicle.y + front_vehicle.currentImage.get_height() if self.direction=='down' else front_vehicle.y
                    self.stop = front_edge - self.currentImage.get_height() - gap if self.direction=='down' else front_edge + self.currentImage.get_height() + gap
            else:
                self.stop = defaultStop[self.direction]
        else:
            self.stop = defaultStop[self.direction]

        effective_stop = self.stop
        if self.vehicleClass == 'ambulance' and currentGreen == self.direction_number and currentYellow == 0:
            effective_stop = -1000

        if self.direction == 'right':
            if self.crossed==0 and self.x + self.currentImage.get_width() > stopLines[self.direction]:
                self.crossed=1
                vehicles[self.direction]['crossed'] +=1
            if self.x + self.currentImage.get_width() <= effective_stop or self.crossed==1 or (currentGreen==self.direction_number and currentYellow==0):
                self.x += self.speed
        elif self.direction=='left':
            if self.crossed==0 and self.x < stopLines[self.direction]:
                self.crossed=1
                vehicles[self.direction]['crossed'] +=1
            if self.x >= effective_stop or self.crossed==1 or (currentGreen==self.direction_number and currentYellow==0):
                self.x -= self.speed
        elif self.direction=='down':
            if self.crossed==0 and self.y + self.currentImage.get_height() > stopLines[self.direction]:
                self.crossed=1
                vehicles[self.direction]['crossed'] +=1
            if self.y + self.currentImage.get_height() <= effective_stop or self.crossed==1 or (currentGreen==self.direction_number and currentYellow==0):
                self.y += self.speed
        elif self.direction=='up':
            if self.crossed==0 and self.y < stopLines[self.direction]:
                self.crossed=1
                vehicles[self.direction]['crossed'] +=1
            if self.y >= effective_stop or self.crossed==1 or (currentGreen==self.direction_number and currentYellow==0):
                self.y -= self.speed

# ----------------------
# SIGNAL FUNCTIONS
# ----------------------
signals = []
def initialize_signals():
    global signals
    for i in range(noOfSignals):
        ts = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
        signals.append(ts)

def setTime():
    global nextGreen
    dir_name = directionNumbers[nextGreen]
    counts = {'car':0,'bus':0,'truck':0,'rickshaw':0,'bike':0,'ambulance':0}
    for l in range(3):
        for v in vehicles[dir_name][l]:
            if v.crossed==0: counts[v.vehicleClass] +=1
    if counts['ambulance']>0:
        greenTime = max(defaultMinimum,7)
    else:
        greenTime = math.ceil((counts['car']*carTime + counts['bus']*busTime +
                            counts['truck']*truckTime + counts['rickshaw']*rickshawTime +
                            counts['bike']*bikeTime)/(noOfLanes+1))
        greenTime = max(defaultMinimum, min(defaultMaximum, greenTime))
    signals[nextGreen].green = greenTime

# ----------------------
# AMBULANCE DETECTION (EARLIEST ARRIVED)
# ----------------------
def detect_ambulance():
    earliest_ambulance = None
    earliest_index = None
    earliest_direction_idx = None

    for d_idx in range(4):
        dname = directionNumbers[d_idx]
        for lane in range(3):
            for v in vehicles[dname][lane]:
                if v.vehicleClass == 'ambulance' and v.crossed == 0:
                    if earliest_ambulance is None or v.index < earliest_index:
                        earliest_ambulance = v
                        earliest_index = v.index
                        earliest_direction_idx = d_idx

    if earliest_ambulance:
        v = earliest_ambulance
        if v.direction == 'right':
            dist = stopLines[v.direction] - (v.x + v.currentImage.get_width())
        elif v.direction == 'left':
            dist = v.x - stopLines[v.direction]
        elif v.direction == 'down':
            dist = stopLines[v.direction] - (v.y + v.currentImage.get_height())
        elif v.direction == 'up':
            dist = v.y - stopLines[v.direction]
        else:
            dist = 99999

        if dist <= AMBULANCE_DETECT_DIST:
            return earliest_direction_idx
    return None

# ----------------------
# VEHICLE GENERATION
# ----------------------
# ----------------------
# VEHICLE GENERATION (ONE AMBULANCE DIRECTION RULE)
# ----------------------
def generateVehicles():
    ambulance_limit = 1
    start_time = time.time()
    ambulance_delay = 50
    active_ambulance_dir = None  # Track which direction currently has an ambulance

    while True:
        elapsed = time.time() - start_time

        # Choose vehicle type
        if elapsed < ambulance_delay:
            vehicle_type = random.choices([0,1,2,3,4],[25,15,15,15,30],k=1)[0]
        else:
            vehicle_type = random.choices([0,1,2,3,4,5],[25,15,15,15,25,5],k=1)[0]

        # Handle ambulance logic
        if vehicle_type == 5:
            # If an ambulance already exists in one direction, skip others
            if active_ambulance_dir is not None:
                vehicle_type = random.choices([0,1,2,3,4],[25,15,15,15,30],k=1)[0]
            else:
                d_idx = random.randint(0,3)
                dname = directionNumbers[d_idx]

                # Restrict perpendicular directions
                if dname in ['right', 'left']:
                    blocked_dirs = ['up', 'down']
                else:
                    blocked_dirs = ['right', 'left']

                # If perpendicular directions already have ambulances waiting, skip
                any_blocked = any(
                    any(v.vehicleClass == 'ambulance' and v.crossed == 0 for v in vehicles[bdir][lane])
                    for bdir in blocked_dirs for lane in range(3)
                )
                if any_blocked:
                    vehicle_type = random.choices([0,1,2,3,4],[25,15,15,15,30],k=1)[0]
                else:
                    active_ambulance_dir = dname

        # Assign lane number
        if vehicle_type == 4:
            lane_number = 0
        elif vehicle_type == 5:
            available_lanes = [l for l in range(3) if len(vehicles[active_ambulance_dir][l]) < 5]
            lane_number = random.choice(available_lanes) if available_lanes else random.randint(0,2)
            direction_number = list(directionNumbers.keys())[list(directionNumbers.values()).index(active_ambulance_dir)]
        else:
            lane_number = random.randint(1,2)
            temp = random.randint(0,999)
            direction_number = 0 if temp < 400 else 1 if temp < 800 else 2 if temp < 900 else 3

        # Create vehicle
        will_turn = 1 if lane_number == 2 and random.randint(0,4) <= 2 else 0
        direction = directionNumbers[direction_number]
        Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, direction, will_turn)

        # Clear active ambulance direction if no ambulances left
        if active_ambulance_dir:
            active_exists = any(
                any(v.vehicleClass == 'ambulance' and v.crossed == 0 for v in vehicles[active_ambulance_dir][lane])
                for lane in range(3)
            )
            if not active_exists:
                active_ambulance_dir = None

        time.sleep(0.7)


# ----------------------
# SIMULATION TIME THREAD
# ----------------------
def simulationTime():
    global timeElapsed
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed >= simTime:
            totalVehicles = sum(vehicles[directionNumbers[i]]['crossed'] for i in range(noOfSignals))
            print('Total vehicles passed:', totalVehicles)
            os._exit(1)

# ----------------------
# SIGNAL UPDATE LOGIC
# ----------------------
def updateValues():
    for i in range(noOfSignals):
        if i==currentGreen:
            if currentYellow==0:
                signals[i].green -=1
                signals[i].totalGreenTime +=1
            else:
                signals[i].yellow -=1
        else:
            signals[i].red -=1

# ----------------------
# MAIN LOOP THREAD
# ----------------------
def repeat_loop():
    global currentGreen, currentYellow, nextGreen
    while True:
        # Always check for ambulance first
        detected = detect_ambulance()
        if detected is not None and detected != currentGreen:
            currentYellow = 0
            currentGreen = detected
            nextGreen = (currentGreen + 1) % noOfSignals
            for i in range(noOfSignals):
                signals[i].red = defaultRed
                signals[i].green = defaultGreen
                signals[i].yellow = defaultYellow
            signals[currentGreen].green = max(defaultMinimum, 7)
            signals[currentGreen].yellow = defaultYellow

        while signals[currentGreen].green > 0:
            detected = detect_ambulance()
            if detected is not None and detected != currentGreen:
                break
            updateValues()
            if signals[nextGreen].red == detectionTime:
                setTime()
            time.sleep(1)

        currentYellow = 1
        for i in range(3):
            stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]]
            for v in vehicles[directionNumbers[currentGreen]][i]:
                v.stop = defaultStop[directionNumbers[currentGreen]]
        while signals[currentGreen].yellow > 0:
            detected = detect_ambulance()
            if detected is not None and detected != currentGreen:
                break
            updateValues()
            time.sleep(1)

        currentYellow = 0
        signals[currentGreen].green = defaultGreen
        signals[currentGreen].yellow = defaultYellow
        signals[currentGreen].red = defaultRed

        detected = detect_ambulance()
        if detected is not None:
            nextGreen = detected
        else:
            vehicle_counts = []
            for i in range(noOfSignals):
                dir_name = directionNumbers[i]
                count = sum(1 for l in range(3) for v in vehicles[dir_name][l] if v.crossed == 0)
                vehicle_counts.append(count)
            nextGreen = vehicle_counts.index(max(vehicle_counts))

        currentGreen = nextGreen
        signals[nextGreen].red = signals[currentGreen].yellow + signals[currentGreen].green

# ----------------------
# MAIN LOOP
# ----------------------
if __name__=="__main__":
    initialize_signals()
    threading.Thread(target=simulationTime, daemon=True).start()
    threading.Thread(target=repeat_loop, daemon=True).start()
    threading.Thread(target=generateVehicles, daemon=True).start()

    black, white = (0, 0, 0), (255, 255, 255)
    clock = pygame.time.Clock()

    DASHBOARD_W = 300
    DASHBOARD_H = 200
    dashboard_rect = pygame.Rect(SCREEN_W - DASHBOARD_W - 10, 10, DASHBOARD_W, DASHBOARD_H)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.blit(background, (0, 0))

        # Draw traffic signals
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    signals[i].signalText = "STOP" if signals[i].yellow == 0 else str(signals[i].yellow)
                    screen.blit(yellowSignal, signalCoods[i])
                else:
                    signals[i].signalText = "SLOW" if signals[i].green == 0 else str(signals[i].green)
                    screen.blit(greenSignal, signalCoods[i])
            else:
                signals[i].signalText = "GO" if signals[i].red <= 10 else "---"
                screen.blit(redSignal, signalCoods[i])

        # Signal text & vehicle counts
        for i in range(noOfSignals):
            txt = font.render(str(signals[i].signalText), True, white, black)
            screen.blit(txt, signalTimerCoods[i])
            vc = font.render(str(vehicles[directionNumbers[i]]['crossed']), True, black, white)
            screen.blit(vc, vehicleCountCoods[i])

        # Time elapsed
        screen.blit(font.render("Time Elapsed: "+str(timeElapsed), True, black, white), (1100, 50))

        # Draw vehicles
        for v in list(simulation):
            # Ambulance flashing
            if v.vehicleClass == 'ambulance':
                if (timeElapsed // 2) % 2 == 0:
                    halo = pygame.Surface((v.currentImage.get_width()+10, v.currentImage.get_height()+10), pygame.SRCALPHA)
                    pygame.draw.rect(halo, (255,0,0,120), halo.get_rect(), border_radius=5)
                    screen.blit(halo, (v.x-5, v.y-5))
                txt_amb = font.render("AMBULANCE", True, (255,0,0))
                screen.blit(txt_amb, (v.x, v.y - 20))

            screen.blit(v.currentImage, (v.x, v.y))
            v.move()

        # ----------------------
        # DASHBOARD
        # ----------------------
        pygame.draw.rect(screen, (50,50,50), dashboard_rect, border_radius=8)
        pygame.draw.rect(screen, (255,255,255), dashboard_rect, 2, border_radius=8)

        y_offset = 20
        padding_x = SCREEN_W - DASHBOARD_W + 10
        for i in range(noOfSignals):
            dir_name = directionNumbers[i]
            txt = font.render(f"{dir_name.upper()}: {vehicles[dir_name]['crossed']} crossed", True, (255,255,255))
            screen.blit(txt, (padding_x, y_offset))
            y_offset += 25

        ambulances_waiting = sum(
            1 for d in directionNumbers.values() for l in range(3)
            for v in vehicles[d][l] if v.vehicleClass=='ambulance' and v.crossed==0
        )
        txt = font.render(f"AMBULANCES WAITING: {ambulances_waiting}", True, (255,0,0) if ambulances_waiting>0 else (0,255,0))
        screen.blit(txt, (padding_x, y_offset))
        y_offset += 30

        txt = font.render(f"GREEN: {directionNumbers[currentGreen].upper()} ({signals[currentGreen].green}s)", True, (0,255,0))
        screen.blit(txt, (padding_x, y_offset))

        pygame.display.update()
        clock.tick(30)
