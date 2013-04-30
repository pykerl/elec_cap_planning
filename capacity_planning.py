#   Electricity Capacity Planning Model including Air Quality Controls and
#   Health Effects
#
#   Author: Paul Kerl (paul.kerl@gatech.edu)
#

#imports

import datetime
from gurobipy import *
#import numpy as np
#import matplotlib.pyplot as plt
from pylab import *
import random
import csv

#####################################
#########  input data  ##############
#####################################

######### CONSTANTS #########
########    power plant types    ########
emission_types = {0 : 'OZ',
            1 : 'PM25',
            2 : 'SOX'}

pp_types = {0 : 'coal',
            1 : 'oil',
            2 : 'hydro',
            3 : 'nuclear',
            4 : 'gas',
            5 : 'biomass'}
############other sub-types required here!!!!#########

num_hours = 24 #24 hours per day
hours = list(xrange(num_hours))

num_years = 1 #number of years in horizonstarting at year ????
years = list(xrange(num_years))

num_seasons = 3 #winter, summer, intermediate
seasons = list(xrange(num_seasons))

#dummy power plant set
num_plants = 100
pp = list(xrange(num_plants))

######### END CONSTANTS #########



#####################################
########        Classes      ########
#####################################

########    Sensitivities   ########
class AQSensitivity:
    def __init__(self,grid,sensitivity):
        self.grid = grid
        self.sensitivity = sensitivity
    def __str__(self):
        return ""
#TODO

######     Range   ##########
class Range:
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def length(self):
        return self.end - self.start
    def overlaps(self, other):
        return not(self.end < other.start or other.end < self.start)

########    GridSquare definition  ########
class GridSquare:
    def __init__(self,lat_range,long_range):
        self.lat_range = lat_range;
        self.long_range = long_range;
    def __str__(self):
        return "Lat: (%s,%s) Long: (%s,%s)" % (self.lat_range.start,self.lat_range.end, self.long_range.start,self.long_rang.end)

########    Load Curve   ########
class LoadCurve:
    def __init__(self,load,date):
        self.load = load
        self.date = date
    def __str__(self):
        load_print = ""
        for i, value in enumerate(self.load):
            load_print += "\n Hour %d: %.3f MW " % (i,value)
        return "Date: %s, Load: %s" % (self.date, load_print)

######## Year-to-year demand ########
class YearlyDemand:
    def __init__(self,demand):
        self.demand = demand
    def __str__(self):
        load_print = ""
        for i, value in enumerate(self.demand):
            load_print += "\n Year %d: %.3f MW " % (i,value)
        return load_print;

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
    def __init__(self,fixed_cap,inc_cap,dec_cap,fuel_cost):
        self.fixed_cap = fixed_cap
        self.inc_cap = inc_cap
        self.dec_cap = dec_cap
        self.fuel_cost = fuel_cost
    def __str__(self):
        return "Fixed (per MW per year): $%.2f, Inc. Cap: $%.2f per MW, Dec. Cap: $%.2f per MW, Fuel Cost: $%.2f per MW," % (self.fixed_cap,self.inc_cap,self.dec_cap,self.fuel_cost)


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
    #made up costs for now
    fixed_cap_cost = random.randrange(300,400)
    inc_cap_cost = random.randrange(5,20)
    dec_cap_cost = random.randrange(0,5)
    fuel_cost = random.randrange(30,40)
    costs = PowerPlantCosts(fixed_cap_cost,inc_cap_cost,dec_cap_cost,fuel_cost)

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
#######  END FAKE DATA CREATION FOR TESTING    #######
######################################################


#########optimize#########
try:
    #########  create model  #########
    m = Model("cap_planning")

    #########  optimization parameters  #########
    #set tolerance
    #m.setParam("OptimalityTol", .000001)


    #########  variables  #########
    #i and
    x = {} #capacity of plant i in year t
    y = {} #increased capacity of plant i in year t
    q = {} #decreased capacity of plant i in year t
    z = {} #electricity generated at plant i in year t, season s, hour h

    #TODO: NEED additional R_t factor for each year
    #TODO: NEED days per season factor

    #capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            x[i,t] = m.addVar(vtype = GRB.CONTINUOUS,
                              obj = p.costs.fixed_cap,
                              name = 'capacity_%s_%s' % (i,t))

    #inc capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            y[i,t] = m.addVar(vtype = GRB.CONTINUOUS,
                              obj = p.costs.inc_cap,
                              name = 'inc_capacity_%s_%s' % (i,t))

    #dec capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            q[i,t] = m.addVar(vtype = GRB.CONTINUOUS,
                              obj = p.costs.dec_cap,
                              name = 'dec_capacity_%s_%s' % (i,t))

    #electricity generated at plant i in year t, season s, hour h
    for t in years:
        for s in seasons:
            for h in hours:
                for i,p in enumerate(pp):
                    z[i,t,s,h] = m.addVar(vtype = GRB.CONTINUOUS,
                                      obj = p.costs.fuel_cost,
                                      name = 'gen_%s_%s_%s_%s' % (i,t,s,h))


    # Integrate new variables
    m.update()

    #########  objective  #########
    #objective
    #NOTE: objective set within variable definitions!
    m.setAttr(GRB.attr.ModelSense, GRB.MINIMIZE)

    #########  constraints  #########

    #yearly change in capacity balance constraints
    for t in years:
        for i,p in enumerate(pp):
            if(t > 0):
                m.addConstr(x[i,t] - x[i,(t-1)] == y[i,t] - q[i,t] , "change_cap_%s_%s" % (i,t))

    #demand must be met with available capacity
    for h in hours:
        for s in seasons:
            for t in years:
                m.addConstr(quicksum([z[i,t,s,h] for i in range(number_plants)]) == lc.load[h], "load_%s_%s_%s" % (h,s,t))

    ##capacity constraints
    #all plants
    for t in years:
        for s in seasons:
            for h in hours:
                for i,p in enumerate(pp):
                        m.addConstr(z[i,t,s,h] <= p.capacity , "plant_cap_%s_%s_%s_%s" % (i,t,s,h))

    #non-wind, non-solar capacity

    #wind capacity

    #solar capacity

    #rewnewable electricity standard

    #non-negativity (implied)

##
##    for h in hours:
##        for i,p in enumerate(pp):
##            #minimum amount of power
##            m.addConstr(z[i,h] >= p.min_p * y[i,h] , "min_power_%s_%s" % (i,h))
##            #maximum amount of power
##            m.addConstr(z[i,h] <= p.capacity * y[i,h] , "max_power_%s_%s" % (i,h))
##            #startup constraint
##            if h > 0 :
##                m.addConstr(y[i,h] <= y[i,h-1] + x[i,h-1] , "start_up_%s_%s" % (i,h))
##
##    for h in hours:
##             m.addConstr(quicksum([z[i,h] for i in range(number_plants)]) == lc.load[h],
##                             "load_%s" % h)



    #########  solve  #########
    m.optimize()

    #########  output  #########
    # Check optimization result
    if m.status != GRB.status.OPTIMAL:
        print 'Relaxation is infeasible'

#   print out all variables > 0
    for v in m.getVars():
        if v.x > 0.0 :
            print "%s\t:\t%.1f " % (v.varName, v.x)

    #gather data for each hour, for each power plant type (coal, nuclear, etc...)
        #inverse the key-value mapping for power plant types
        inv_pp_types = {v:k for k, v in pp_types.items()}

    load_totals = {}
    for t in years:
        for s in seasons:
            for h in hours :
                for j,k in pp_types.items():
                    load_totals[j,t,s,h] = 0.0

    #calculate plant load
    total_plant_load = 0.0

    for t in years:
        for s in seasons:
            for h in hours :
                for i,p in enumerate(pp) :
                    total_plant_load += z[i,t,s,h].getAttr("X")
                    for j,k in pp_types.items():
                        if p.type == k:
                            load_totals[j,t,s,h] += z[i,t,s,h].getAttr("X")

    print "Objective: $%.2f" % m.objVal


    #calculate total load
    total_load = 0.0
    for h in hours:
        for s in seasons:
            for t in years:
                total_load += lc.load[h]
    #these should match...
    print "Total load (MWh): %s, Plant load (MWh): %s" % (total_load, total_plant_load)



############################################
####### make a horizontal bar chart ########
############################################

    #val = 3+10*rand(5)
    # the bar lengths
    val = [0.0]*6 #start at zero


    #print val

    #add up total production across entire planning period
    for t in years:
         for s in seasons:
             for h in hours :
                for j,k in pp_types.items():
                    val[j] += load_totals[j,t,s,h]
             print val
    val = np.asarray(val[0:6]) #convert to a numpy array
    print "Sum check (MWh): %s" % sum(val)
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

    show()


except GurobiError:
    print('Error reported')