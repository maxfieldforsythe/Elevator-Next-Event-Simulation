import sys
import numpy as np
import random
import math
import statistics
from queue import PriorityQueue
from random import uniform
from collections import OrderedDict

#Variable to store bigRando object
rando = None

#Elevator load times
loads = [0,3,5,7,9,11,13,15,17,19,22]

normal_delays = []

#Exponential CDF
def exp_cdf(x):
    mu = 10
    return 1-math.pow(math.e,(-x/mu))

#Exponential Inverse Density Function
def exp_idf(u):
    mu = 10
    rv = -mu*np.log(1-u)
    return rv

#Returns a random int from 2 to 90 truncated by a random uniform variate. 
#Represents the random time for passengers to arrive in the queue
def truncated_exp(u):
    a = 2
    b = 90
    alpha = exp_cdf(a)
    beta = 1.0-exp_cdf(b)
    u = (u * (1-beta-alpha)) + alpha
    d = exp_idf(u)
    return d

def cdftrunc(x, alph, bet):
    first = geoCDF(x) - geoCDF(alph - 1)
    second = geoCDF(bet) - geoCDF(alph - 1)
    return first / second

#Return geometric CDF
def geoCDF(x):
    return 1 - 0.65**(x+1)

#Generates a random int based on a geometric distribution
#Represents the amount of people in groups of 1 to 8
def get_geo():
    global rando
    u = rando.getRando()
    d = 4
    if(cdftrunc(d, 1, 8) <=u ):
        while ( cdftrunc(d, 1, 8) <= u):
            d += 1
    elif cdftrunc(1, 1, 8) <= u:
        while (cdftrunc(d-1, 1, 8) > u):
            d -= 1
    else:
        d = 1
    # print("d:", d)
    return d

#Old function to calculate elevator times
def calc_ele_time(elevator, direction):
    floors = set()
    for person in elevator.people:
        floors.add(person.floor)
    num_floors = len(floors)
    if direction == "u":
        if num_floors == 1:
            return 8
        else:
            return (2*8 + 5*(num_floors - 2))
    else:
        downtime = 5*num_floors
        # elevator.people.clear()
        return downtime

#Get load time based on number of people
def get_load(number):
    global loads
    return loads[number]
    
#Get the amount of stops from people list
def get_stops(people):
    stops = set()
    for p in people:
        stops.add(p.floor)
    # print(len(stops)+1)
    return len(stops)+1

#Returns the travel time of the elevator event. If ascending returns travel time and unload time to next floor. 
#If desending returns travel time from the current floor to the ground. 
def get_the_motion_of_the_ocean_aka_elevators(elevator):
    travel_time = 0
    floors = elevator.stops
    # print(elevator)
    if len(floors) > 1:
        h = floors[1] - floors[0]
        # print(elevator.persons_per_floor)
        persons_on_that_floor_i_guess = elevator.persons_per_floor.get(floors[1], 0)
        unLoad_time = loads[persons_on_that_floor_i_guess]
        if(h == 1):
            travel_time += 8 # + unLoad_time
        elif(h > 1):
            travel_time += (16 + 5*(h - 2)) # + unLoad_time
        elevator.stops.pop(0)
    else:
        h = elevator.stops[0]
        if(h == 1):
            travel_time += 8
        else:
            travel_time += (16 + 5*(h - 2))
    return travel_time


#Updates elevator object with amount of stops from the current group as well as the amount per floor
def sort_floors(elevator):
    stops = {}
    for p in elevator.people:
        stops[p.floor] = stops.get(p.floor, 0) + 1
    floors = sorted(stops)
    stops2electricbogaloo = {k: stops[k] for k in sorted(stops.keys())}
    floors.insert(0, 0)
    elevator.stops = floors
    elevator.persons_per_floor = stops2electricbogaloo
    # print("Sort floors:", elevator.stops, elevator.persons_per_floor)


#Creates groups of people given the random number from 1-8 and from 2-90.
#If a certain floor already has 100 people assigned to it no more can be added to it
#initializes peoples start times with sime clock
def create_group(number, time, av_floors, floor_totals):

    newGroup = Group()
    newGroup.number = number

    for i in range(number):
        if len(av_floors) != 0:
            

            floor = av_floors[int(len(av_floors) * rando.getRando())]
            # print(av_floors, floor)
            # print(floor_totals, floor_totals[floor-1])
            if floor_totals[floor-1] < 100:
                newGroup.add_person(Person(floor, time))
                floor_totals[floor-1] += 1
                if floor_totals[floor-1] == 100:
                    av_floors.remove(floor)
            elif floor_totals[floor-1] >= 100:
                av_floors.remove(floor)
            # print("After:", floors)
        else:
            break
        #print(av_floors, floors)
    return newGroup

#After creating all random group arrival events returns the event list and floor total to the simulator
def peerThroughTime(floors, elevators):
    global rando
    max_persons = floors * 100
    curr_peoples = 0
    prev_time = 0.0
    eventList = PriorityQueue(0)
    groups = []
    floorTotal = []
    avail_floors = [x+1 for x in range(floors)]

    for i in range(floors):
        floorTotal.append(0)
    while curr_peoples < max_persons:
        interarrival = truncated_exp(rando.getRando())
        geo = get_geo()
        if(curr_peoples + geo > max_persons):
            geo = max_persons - curr_peoples
        group = create_group(geo, interarrival+prev_time, avail_floors, floorTotal)
        groups.append(group)
        prev_time = interarrival + prev_time
        event = Event(prev_time, "q", 0, None, group)
        eventList.put(event)
        curr_peoples += group.number

    sum = 0
    for g in groups:
        sum += g.number

    # print("-----",sum, "people in", len(groups), "groups ------")
    return eventList, floorTotal

#Updates a persons end time and calculates the normal delay, which is added to a gloabl array for later
def manage_people(elevator, simclock):
    global normal_delays
    current_floor = elevator.stops[0]
    people = elevator.people
    for person in people:
        if person.floor == current_floor:
            person.off_time = simclock
            if(current_floor == 1):
                person.opt_time = float(8 + 2*loads[1])
            else:
                person.opt_time = float((16 + 5*(current_floor - 2)) + 2*loads[1])

            opt_time = person.opt_time
            travel_time = person.get_total()
            norm = round((travel_time - opt_time)/opt_time, 8)
            # print(travel_time, opt_time, travel_time-opt_time, person.floor)
            # print("Person arrival time:", person.time, "opt_time", person.opt_time, "travel time:", travel_time, "Norm:", norm, "elevator arival:", simclock, "floor:", person.floor, end = "\t")
            normal_delays.append(norm)
    """
    find optimal time
    find the total (travel) time off_time - time
    find normal delay
    """
    
#Run one day of elevator traffic
#This function is the event simulator, starting with all arrival events added to the priority queue event list.
def run_event(floors, elevators):
    stops = 0
    people = []
    simClock = 0.0
    totalPeople = 0
    maxq = 0
    avDelay = 0.0
    stddev = 0.0
    total = floors * 100
    current = 0
    floorTotal = []
    time = 0.0
    ele = []
    person_num = 0

    # sys.stdout = open("output_log.txt", "w")

    #Create arrival events and return event queue
    eventList, floorTotal = peerThroughTime(floors, elevators)
    for i in range(elevators):
        ele.append(Elevator(True))

    #Run this while events still need to happen
    while eventList.qsize() > 0:
        # print(stops)
        #input("Press Enter to continue...")
        currentEvent = eventList.get()

        # "q" even indicates that a group arrival is happening and triggers this event
        #This fills all available elevators with remaining queue members in a round robin fashion
        #Finishes by creating elevator up events and adding them to the queue after the travel time is calculated
        if currentEvent.ty == "q":
            group = currentEvent.group
            simClock = currentEvent.at
            for person in group.people:
                people.append(person)
                person_num += 1

            

            for elevator in ele:              
                if elevator.isDown == True:
                    listemOfaDown.append(elevator)
            # print("in q Elevators Down at time:", currentEvent.at, listemOfaDown)
            counter = 0
            a_variable = 0
            if len(people) <= len(listemOfaDown) * 10:
                a_variable = len(people)
            else:
                a_variable = len(listemOfaDown) * 10
            for i in range(a_variable):
                if len(listemOfaDown) > 0:
                    if people[i].time <= currentEvent.at:
                        listemOfaDown[i % len(listemOfaDown)].people.append(people[i])
                        counter += 1
                    else: 
                        break

            for i in range(counter):
                people.pop(0)
            q_size = len(people)
            if(q_size > maxq):
                maxq = q_size
            for elevator in listemOfaDown:
                if len(elevator.people) > 0:
                    sort_floors(elevator)
                    time = get_the_motion_of_the_ocean_aka_elevators(elevator)
                    load_time = get_load(len(elevator.people))
                    elevator.isDown = False
                    stops += get_stops(elevator.people)
                    # print("257", simClock, simClock+load_time)
                    # print(simClock/60, "elevator timings iotime=",load_time/60, "lift time=", time, "fromfloor=", 0, "tofloor=", elevator.stops[0], elevator, elevator.people)
                    eventList.put(Event(simClock + load_time, "u", time + load_time, elevator, currentEvent.group))
                

        # "u" events indicate an up event.
        #This event updates the sim clock to the events time before either sending another up event or down event if the elevator is empty.
        elif currentEvent.ty == "u":
            
            simClock = currentEvent.at  + currentEvent.service
            time = get_the_motion_of_the_ocean_aka_elevators(currentEvent.elevator)
            manage_people(currentEvent.elevator, simClock)
            elevator = currentEvent.elevator
            if len(elevator.stops) > 1:
                # print(simClock, "elevator timings iotime=",load_time, "lift time=", time, "fromfloor=","?" , "tofloor=", elevator.stops[0])
                # print("U Elevator", elevator, "Up at time:", simClock+load_time, "with people:", len(elevator.people))
                eventList.put(Event((simClock), "u", time, currentEvent.elevator, None)) 
            else:
                # print(simClock/60, "elevator timings iotime=",load_time/60, "lift time=", time, "fromfloor=","?" , "tofloor=", 0)
                eventList.put(Event((simClock), "d", time, currentEvent.elevator, None)) 

        #Down event updates sim clock and starts a new up event if the queue is not empty
        else: 
            simClock = currentEvent.at + currentEvent.service
            currentEvent.elevator.people.clear()
            currentEvent.elevator.isDown = True
            listemOfaDown = []
            for elevator in ele:              
                if elevator.isDown == True:
                    listemOfaDown.append(elevator)
            # print("in d Elevators Down at time:", currentEvent.at, listemOfaDown)
            allFull = False
            if totalPeople == (floors * 100):
                allFull = True
            if allFull:
                if len(listemOfaDown) == elevators:
                    return stops, maxq, avDelay, stddev
            counter = 0
            a_variable = 0
            if len(people) <= len(listemOfaDown) * 10:
                a_variable = len(people)
            else:
                a_variable = len(listemOfaDown) * 10
            for i in range(a_variable):
                if people[i].time <= currentEvent.at:
                    listemOfaDown[i % len(listemOfaDown)].people.append(people[i])
                    counter += 1
                else: 
                    break
            q_size = find_q_size(people, currentEvent.at)
            if(q_size > maxq):
                maxq = q_size
            for i in range(counter):
                people.pop(0)

            if not allFull:
                for elevator in listemOfaDown:
                    if len(elevator.people) > 0:
                        sort_floors(elevator)
                        time = get_the_motion_of_the_ocean_aka_elevators(elevator)
                        load_time = get_load(len(elevator.people))
                        elevator.isDown = False
                        stops += get_stops(elevator.people)
                        # print("308", simClock, simClock+load_time)
                        # print("D Elevator Up at time:", simClock+load_time, "with people:", len(elevator.people))
                        eventList.put(Event(simClock + load_time, "u", time + load_time, elevator, currentEvent.group))
        

    
    return stops, maxq, avDelay, stddev

#Finds current queue length
def find_q_size(queue, time):
    size = 0
    for p in queue:
        if p.time <= time:
            size += 1
    return size

# Welfords Double Pass equation
def welford1():
    global normal_delays
    n = len(normal_delays)
    xbar = 0
    # first pass
    for i in normal_delays:
        xbar += i
    xbar /= n
    s_2=0
    # second pass
    for i in normal_delays:
        s_2 += (xbar - i)**2
    s_2 /= n
    s = math.sqrt(s_2)
    return xbar, s

# Welfords Single pass eqation
def welford2():
    global normal_delays
    xbar = 0
    hold = 0
    n = len(normal_delays)

    for i in range(n):
        hold += (normal_delays[i]**2)
        xbar += normal_delays[i]
    hold /= n
    xbar /= n
    s_2 = hold - (xbar**2) 
    s = math.sqrt(s_2)
    return xbar, s

#Main function. Runs the sim for the given number of days
def funct( a, b, c, d):
    global rando
    all_stops = []
    stops = 0
    all_maxq = []
    maxq = 0
    avDelay = 0.0
    stdDelay = 0.0
    rando = BigRando(c)

    for i in range(d):
        stops, maxq, avDelay, stddev = run_event(a, b)
        all_stops.append(stops/b)
        # print(stops)
        all_maxq.append(maxq)
    # print(normal_delays)
    # print(sorted(all_stops))
    avDelay, stdDelay = welford1()
    stops = statistics.mean(all_stops)
    maxq = max(all_maxq)
    output(stops, maxq, avDelay, stdDelay)
    # print()
    # sys.stdout.close()

#Formats output
def output(stops, maxq, avgDelay, stddev):
    print("OUTPUT stops ", str("{:.5f}".format(stops)), sep="")
    print("OUTPUT max qsize ", maxq, sep="")
    print("OUTPUT average delay ", str("{:.5f}".format(avgDelay)), sep="")
    print("OUTPUT stddev delay ", str("{:.5f}".format(stddev)), sep="")


class Person:
    def __init__(self, floor, time):
        self.floor = floor
        self.time = time
        self.off_time = 0.0
        self.total_time = 0.0
        self.opt_time = 0.0

    def __lt__(self, other):
        return self.floor < other.floor

    def get_total(self):
        self.total_time = self.off_time - self.time
        return self.total_time

class Elevator:
    def __init__(self, isDown):
        self.isDown = isDown
        self.people = []
        self.floor = 0
        self.stops = []
        self.persons_per_floor = {}
    


class Group:
    def __init__(self):
        self.number = 0
        self.people = []
    def add_person(self,p):
        # print(self, self.people, end="\t")
        self.people.append(p)
    


class Event:
    def __init__(self, at: float, ty: str, service: float, elevator, group):
        self.at = at
        self.ty = ty
        self.service = service
        self.elevator = elevator
        self.group = group 
    def __lt__(self, other):
        return self.at < other.at

#Pulls next uniform random value from the input file
class BigRando:
    def __init__(self, filename):
        try:
            self.file = open(filename, "r")
        except:
            exit(1)
    def getRando(self):
        try:
            return float(self.file.readline())
        except:
            exit(1)

