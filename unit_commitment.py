#   Unit Commitment Mathematical Model
#   author: Paul Kerl (paul.kerl@gatech.edu)
#

#imports

import datetime
from gurobipy import *
#import numpy as np
#import matplotlib.pyplot as plt
from pylab import *
import random

#########  input data  #########

#power plants


#start up costs


#shut down costs


#variable costs


#date and hourly demand


#emissions inventory data


#####################################
########        Classes      ########
#####################################

########    demand   ########
class LoadCurve:
    def __init__(self,load,date):
        self.load = load
        self.date = date
    def __str__(self):
        load_print = ""
        for i, value in enumerate(self.load):
            load_print += "\n Hour %d: %.3f MW " % (i,value)
        return "Date: %s, Load: %s" % (self.date, load_print)

########    locations   ########
class Location:
    def __init__(self,lat,lon,state):
        self.lat = lat
        self.lon = lon
        self.state = state
    def __str__(self):
        return "Location: (%f,%f) %s" % (self.lat,self.lon,self.state)

########    power plant costs   ########
class PowerPlantCosts:
    def __init__(self,start_up,fuel_cost):
        self.start_up = start_up
        self.fuel_cost = fuel_cost
    def __str__(self):
        return "Start up: $%.2f, Fuel Cost: $%.2f per MWh" % (self.start_up,self.fuel_cost)


########    power plants   ########
class PowerPlant:
    def __init__(self,type,cap_factor,capacity,min_p,name, location, costs):
        self.type = type            #type of plant, in number form see "pp_types"
        self.cap_factor = cap_factor#capacity factor, 0 to 1
        self.capacity = capacity    #capacity in MW
        self.min_p = min_p              #minimum power if started
        self.name = name            #name of the plant
        self.location = location    #location of the plant
        self.costs = costs
    def __str__(self):
        return "%s \n\t Type: %s \n\t Cap Factor: %s \n\t Capacity (MW): %s \n\t Minimum Gen (MW): %s \n\t %s \n\t %s" % (self.name, self.type, self.cap_factor, self.capacity, self.min_p, self.location, self.costs)


########    power plant types dictionary   ########
pp_types = {0 : 'coal',
            1 : 'oil',
            2 : 'hydro',
            3 : 'nuclear',
            4 : 'gas',
            5 : 'biomass'}

######################################################
######################################################
########    FAKE DATA CREATION FOR TESTING    ########
######################################################
######################################################

########    random power plants creation    ########
#make some random power plants
number_plants = 100;
pp = []

for i in range(0, number_plants):
    pp_name = "powerplant_%d" % i #made up name
    pp_type = pp_types[random.randint(0,5)] #random type

    #costs
    start_up = 500
    fuel_cost = random.randrange(30,40)
    costs = PowerPlantCosts(start_up,fuel_cost)

    #location
    # Georgia corner coordinates 34.966999,-85.649414
    #                            30.694612,-80.90332

    r_lat = round(random.uniform(30.694512, 34.966999), 6) #random latitude
    r_lon = round(random.uniform(-85.649414, -80.90332), 6) #random longitude
    loc = Location(r_lat,r_lon,"GA") #random location

    #add the power plant
    ppadd = PowerPlant(pp_type,0.8,153,1,pp_name,loc,costs)
    pp.append(ppadd)

    #print out the power plant for testing
    #print ppadd

#demand
#make a random load curve
year = 2007;
month = 7;
day = 29;
date = datetime.date(year, month, day)
load = [100*(5+random.randint(1,10)) for _ in range(24)]
lc = LoadCurve(load,date)
#print lc


######################################################
######################################################
#######  END FAKE DATA CREATION FOR TESTING    #######
######################################################
######################################################

#other data needed
num_hours = 24
hours = list(xrange(num_hours))



try:
    #########  create model  #########
    m = Model("unit_commitment")

    #########  optimization parameters  #########
    #set tolerance
    #m.setParam("OptimalityTol", .000001)


    #########  variables  #########
    x = {}
    y = {}
    z = {}

    #binary startup of plant i in hour h
    for h in hours:
        for i,p in enumerate(pp):
            x[i,h] = m.addVar(vtype = GRB.BINARY,
                              obj = p.costs.start_up,
                              name = 'startup_%s_%s' % (i,h))
    #binary state of plant i in hour h
    for h in hours:
        for i,p in enumerate(pp):
            y[i,h] = m.addVar(vtype = GRB.BINARY,
                              obj = 0.0,
                              name = 'state_%s_%s' % (i,h))

    #electricity generated at plant i in hour h
    for h in hours:
        for i,p in enumerate(pp):
            z[i,h] = m.addVar(vtype = GRB.CONTINUOUS,
                              obj = p.costs.fuel_cost,
                              name = 'gen_%s_%s' % (i,h))

    #x1 = m.addVar(vtype=GRB.CONTINUOUS, name="x1")
    #x2 = m.addVar(vtype=GRB.CONTINUOUS, name="x2")

    # Integrate new variables
    m.update()

    #########  objective  #########
    #objective
    #NOTE: objective set within variable definitions!
    #m.setObjective(1600 * (x1 + x2), GRB.MINIMIZE)
    m.setAttr(GRB.attr.ModelSense, GRB.MINIMIZE)

    #########  constraints  #########

    for h in hours:
        for i,p in enumerate(pp):
            #minimum amount of power
            m.addConstr(z[i,h] >= p.min_p * y[i,h] , "min_power_%s_%s" % (i,h))
            #maximum amount of power
            m.addConstr(z[i,h] <= p.capacity * y[i,h] , "max_power_%s_%s" % (i,h))
            #startup constraint
            if h > 0 :
                m.addConstr(y[i,h] <= y[i,h-1] + x[i,h-1] , "start_up_%s_%s" % (i,h))

    for h in hours:
             m.addConstr(quicksum([z[i,h] for i in range(number_plants)]) == lc.load[h],
                             "load_%s" % h)
    #########  solve  #########
    m.optimize()

    #########  output  #########
    # Check optimization result
    if m.status != GRB.status.OPTIMAL:
        print 'Relaxation is infeasible'

###   print out all variables > 0
##    for v in m.getVars():
##        if v.x > 0.0 :
##            print "%s\t:\t%.1f " % (v.varName, v.x)

    #gather data for each hour, for each power plant type (coal, nuclear, etc...)
    ##    #inverse the key-value mapping for power plant types
    ##    inv_pp_types = {v:k for k, v in pp_types.items()}

    load_totals = {}
    for h in hours :
        for j,t in pp_types.items():
            load_totals[h,j] = 0.0

    for h in hours :
        for i,p in enumerate(pp) :
            for j,t in pp_types.items():
                if p.type == t :
                    load_totals[h,j] += z[i,h].getAttr("X")

    print "Objective: $%.2f" % m.objVal


############################################
####### make a horizontal bar chart ########
############################################
    #val = 3+10*rand(5)
    # the bar lengths
    val = [0.0]*6
    i = 0
    for j,t in pp_types.items():
        for h in hours :
            val[i] += load_totals[h,j]
        i+=1
    val = np.asarray(val[0:6])
    pos = arange(6)+.5    # the bar centers on the y axis

    #labels
    labels = [None]*6
    for j,t in pp_types.items():
        labels[j] = pp_types[j]

    labels = array(labels)
    figure(1)
    barh(pos,val, align='center')
    yticks(pos, labels)
    xlabel('MWh')
    title('Power plant fuel use')
    grid(True)

###    figure(2)
###    barh(pos,val, xerr=rand(5), ecolor='r', align='center')
###    yticks(pos, ('Tom', 'Dick', 'Harry', 'Slim', 'Jim'))
###    xlabel('Performance')

    show()




except GurobiError:
    print('Error reported')







#constr