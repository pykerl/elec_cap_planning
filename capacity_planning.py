#!/opt/python/bin/python2.7
# above line for condor direct execution if need be



#   Electricity Capacity Planning Model including Air Quality Controls and
#   Health Effects
#
#   Author: Paul Kerl (paul.kerl@gatech.edu)
#

import datetime
from gurobipy import *
from pylab import *
import csv
#import numpy as np
#import matplotlib.pyplot as plt
#import random

#####################################
#########  input data  ##############
#####################################

#adjust feasibility of randomized load curves
adj_lc = 0.85

######### CONSTANTS #########
########    power plant types    ########
emission_types = {0 : 'OZ',
            1 : 'PM25',
            2 : 'SOX'}

pp_types = {0 : 'Coal',
            1 : 'Oil',
            2 : 'Natural Gas',
            3 : 'Hydro',
            4 : 'Nuclear',
            5 : 'Biomass',
            6 : 'Other'}
#Important Note: need to modify "my_color" array to match length of pp_types array!
num_plant_types = len(pp_types)
#Important Note: need to modify "my_color" array to match length of pp_types array!

#reserve margin
R = 0.15 #13.5% within 3 years, and 15% for longer forecasts
# Source: http://pbadupws.nrc.gov/docs/ML0915/ML091540841.pdf
# Note: Georgia Public Service Commission (GPSC)
# "The GPSC approved a 13.5 percent reserve margin for planning within 3
# years and a 15 percent margin for longer forecasts and approved planning that
# identifies the need for new resources beginning in 2009 and continuing through
# 2023."

############other sub-types required here!!!!#########

num_hours = 1 #24 hours per day
hours = list(xrange(num_hours))

num_years = 20 #number of years in horizonstarting at year 2007
years = list(xrange(num_years))
start_year = 2007

num_seasons = 2 #winter, summer, intermediate
seasons = list(xrange(num_seasons))

days_per_season = 30

######### END CONSTANTS #########


######### Decimal/Thousands Formater ##########

def func(x, pos):  # formatter function takes tick value and tick position
    return '{0:,}'.format(int(x))   # change to comma thousands separator and
                                    # truncate decimal

def plantFuelStringToType(fuel_type):
    pp_type = 0
    #print "debug: fuel type is %s" % fuel_type
    if(fuel_type in 'COAL'): pp_type = 0
    if(fuel_type in 'GAS'): pp_type = 2
    if(fuel_type in 'BIO'): pp_type = 5
    if(fuel_type in 'NUCLEAR'): pp_type = 4
    if(fuel_type in 'HYDRO'): pp_type = 3
    if(fuel_type in 'OIL'): pp_type = 1
    if(fuel_type == ''): pp_type = 6
    return pp_type

#####################################
########        Classes      ########
#####################################

########    Sensitivities   ########
class GridSquareVal:
    def __init__(self,grid,val):
        self.grid = grid
        self.val = val
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
    def __init__(self,fixed_cap_cost,fixed_cap_cost_pct,fixed_cap_cost_fs,inc_cap_cost,dec_cap_cost,fuel_cost,fuel_cost_pct,fuel_cost_fs,health_cost,health_cost_pct,health_cost_fs):
        self.fixed_cap_cost = fixed_cap_cost
        self.fixed_cap_cost_pct = fixed_cap_cost_pct
        self.fixed_cap_cost_fs = fixed_cap_cost_fs
        self.inc_cap_cost = inc_cap_cost
        self.dec_cap_cost = dec_cap_cost
        self.fuel_cost = fuel_cost
        self.health_cost = health_cost
        self.health_cost_pct = health_cost_pct
        self.health_cost_fs = health_cost_fs
    def __str__(self):
        return "Fixed (per MW per year): $%.2f, Inc. Cap: $%.2f per MW, Dec. Cap: $%.2f per MW, Fuel Cost: $%.2f per MW, Health Cost: (array of values)" % (self.fixed_cap,self.inc_cap,self.dec_cap,self.fuel_cost)


########    power plants   ########
class PowerPlant:
    def __init__(self,type,cap_factor,capacity,min_power,name, location, costs):
        self.type = type            #type of plant, in number form see "pp_types"
        self.cap_factor = cap_factor#capacity factor, 0 to 1
        self.capacity = capacity    #capacity in MW
        self.min_power = min_power              #minimum power if started
        self.name = name            #name of the plant
        self.location = location    #location of the plant
        self.costs = costs
    def __str__(self):
        return "%s \n\t Type: %s \n\t Cap Factor: %s \n\t Capacity (MW): %s \n\t Minimum Gen (MW): %s \n\t %s \n\t %s" % (self.name, self.type, self.cap_factor, self.capacity, self.min_power, self.location, self.costs)



######################################################
########   INPUT DATA LOAD ###########################
######################################################

########     power plants creation    ########
#load the power plants

pp = []
pp_file = "C:/Users/pyk/Desktop/elec_cap_planning/data/plant_info.csv"
pp_file = open(pp_file,'rU')
reader = csv.reader(pp_file)

header = {}
pp_data = []
iter = 0
for row in reader:
    #print iter
    if iter == 0:
        header = row
    else:
        i = 0
        pp_data_ele = {}
        for h in header:
            pp_data_ele[h] = row[i]
            i = i + 1
        pp_data.append(pp_data_ele)
    iter = iter + 1
total_capacity_avail = 0
for pow_plant in pp_data:
    pp_name = pow_plant['PNAME']
    pp_type = plantFuelStringToType(pow_plant['PLFUELCT'])
    #print pp_type
    #costs
    fixed_cap_cost = float(pow_plant['FIXED_COST'])
    fixed_cap_cost_pct = float(pow_plant['FIXED_COST_PCT'])
    fixed_cap_cost_fs = float(pow_plant['FIXED_COST_FS'])
    inc_cap_cost = float(pow_plant['FIXED_COST'])
    dec_cap_cost = float(pow_plant['DEC_COST'])
    fuel_cost = float(pow_plant['FUEL_COST'])
    fuel_cost_pct = float(pow_plant['FUEL_COST_PCT'])
    fuel_cost_fs = float(pow_plant['FUEL_COST_FS'])
    health_cost = {} #TODO call health cost function here!
    health_cost_pct = {} #TODO call health cost function here!
    health_cost_fs = {} #TODO call health cost function here!
    for t in years:
        for s in seasons:
            for h in hours:
                #print "Health no"
                health_cost[h,s,t] = float(pow_plant['HEALTH_COST']) #TODO fix hourly function call
                health_cost_pct[h,s,t] = float(pow_plant['HEALTH_COST_PCT']) #TODO fix hourly function call
                health_cost_fs[h,s,t] = float(pow_plant['HEALTH_COST_FS']) #TODO fix hourly function call
                #print "Health yes"
    costs = PowerPlantCosts(fixed_cap_cost,fixed_cap_cost_pct,fixed_cap_cost_fs,inc_cap_cost,dec_cap_cost,fuel_cost,fuel_cost_pct,fuel_cost_fs,health_cost,health_cost_pct,health_cost_fs)
    total_capacity_avail += float(pow_plant['NAMEPCAP'])*float(pow_plant['CAPFAC'])
    #location
    # Georgia corner coordinates 34.966999,-85.649414
    #                            30.694612,-80.90332

    r_lat = 30.694512 #TODO latitude placeholder (plotting results without using this -- matched by name instead)
    r_lon = -85.649414 #TODO longitude placeholder (plotting results without using this -- matched by name instead)
    loc = Location(r_lat,r_lon,"GA") #random location placeholder

    #add the power plant
    cap_factor = float(pow_plant['CAPFAC'])
    capacity = float(pow_plant['NAMEPCAP'])
    min_power = float(pow_plant['MIN_POW'])

            #         (type, cap_factor, capacity, min_p, name, location, costs):
    ppadd = PowerPlant(pp_type,cap_factor,capacity,min_power,pp_name,loc,costs)

    pp.append(ppadd)

num_plants = len(pp)

#close power plant data file
pp_file.close()

#demand
#make an array of random load curves
lc_array = {}
for t in years:
    for s in seasons:
        year_in= start_year + t
        month_in = s + 1 #months in 1...12
        day_in = 1 #random day
        date = datetime.date(year_in, month_in, day_in)
        #TODO Probabilistic load curve
        #load = [100*(50+random.randint(1,10)) for _ in range(24)] #different randomized load curve
        #load = [int(total_capacity_avail*adj_lc*(random.randint(1,10)/10.0)) for _ in range(24)] #randomized load curve
        load = [int(total_capacity_avail*adj_lc) for _ in range(24)] #TODO load historical load curves function here
        lc_array[t,s] = LoadCurve(load,date)

#print lc


######################################################
####### END INPUT DATA FOR MODEL #####################
######################################################

#########optimize#########
try:
    #########  create model  #########
    m = Model("cap_planning")

    #########  optimization parameters  #########
    #TODO set tolerance
    #m.setParam("OptimalityTol", .000001)


    #########  variables  #########
    #i and
    x = {} #capacity of plant i in year t
    y = {} #increased capacity of plant i in year t
    q = {} #decreased capacity of plant i in year t
    z = {} #electricity generated at plant i in year t, season s, hour h

    #capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            x[i,t] = m.addVar(vtype = GRB.CONTINUOUS,
                              obj = p.costs.fixed_cap_cost,
                              name = 'capacity_%s_%s' % (i,t))

    #inc capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            y[i,t] = m.addVar(vtype = GRB.INTEGER,
                              obj = 100*p.costs.inc_cap_cost,
#                              obj = 10,
                              name = 'inc_capacity_%s_%s' % (i,t))

    #dec capacity of plant i in year t
    for t in years:
        for i,p in enumerate(pp):
            q[i,t] = m.addVar(vtype = GRB.INTEGER,
                              obj = 10*p.costs.dec_cap_cost,
                              name = 'dec_capacity_%s_%s' % (i,t))

    #electricity generated at plant i in year t, season s, hour h
    for t in years:
        for s in seasons:
            for h in hours:
                for i,p in enumerate(pp):
                    z[i,t,s,h] = m.addVar(vtype = GRB.CONTINUOUS,
                                      obj = (p.costs.fuel_cost + p.costs.health_cost[h,s,t])*days_per_season,
                                      name = 'gen_%s_%s_%s_%s' % (i,t,s,h))


    # Integrate new variables
    m.update()

    #########  objective  #########
    #objective
    #NOTE: objective set within variable definitions!
    m.setAttr(GRB.attr.ModelSense, GRB.MINIMIZE)

    #########  constraints  #########
    cap_constr = {}
    #yearly change in capacity balance constraints
    for t in years:
        for i,p in enumerate(pp):
            if(t > 0):
                #m.addConstr(x[i,t] - x[i,(t-1)] == y[i,t] - q[i,t] , "change_cap_%s_%s" % (i,t))
                cap_constr[i,t] = m.addConstr(x[i,t] - x[i,(t-1)] == y[i,t] - q[i,t] , "change_cap_%s_%s" % (i,t))

    #demand must be met with available capacity
    for h in hours:
        for s in seasons:
            for t in years:
                m.addConstr(quicksum([z[i,t,s,h] for i in range(num_plants)]) == lc_array[t,s].load[h]*(1+R), "load_%s_%s_%s" % (h,s,t))

    ##capacity constraints
    #all plants
    for t in years:
        for s in seasons:
            for h in hours:
                for i,p in enumerate(pp):
                        m.addConstr(z[i,t,s,h] <= p.cap_factor*x[i,t], "plant_cap_%s_%s_%s_%s" % (i,t,s,h))

    #all plants final max capacity
    for t in years:
        for i,p in enumerate(pp):
            m.addConstr(x[i,t] <= p.capacity , "plant_cap_%s_%s" % (i,t))

    #non-wind, non-solar capacity

    #wind capacity

    #solar capacity

    #rewnewable electricity standard

    #non-negativity (implied)

##
##    for h in hours:
##        for i,p in enumerate(pp):
##            #minimum amount of power
##            m.addConstr(z[i,h] >= p.min_power * y[i,h] , "min_power_%s_%s" % (i,h))
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

#   print out all variables > 0
    for v in m.getVars():
        #gather data for each hour, for each power plant type (coal, nuclear, etc...)
        #inverse the key-value mapping for power plant types
        inv_pp_types = {v:k for k, v in pp_types.items()}
        #print if larger than 0
        #if v.x > 0.0 :
            ##
            #print "%s\t:\t%.1f " % (v.varName, v.x)


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
                        if p.type == j:
                            load_totals[j,t,s,h] += z[i,t,s,h].getAttr("X")

    print "Objective: $" + '{0:,.2f}'.format(m.objVal)


    #calculate total load
    total_load = 0.0
    for h in hours:
        for s in seasons:
            for t in years:
                total_load += lc_array[t,s].load[h]
    #these should match...
    print "Total load (MWh): %s (no reserve margin)\nPlant load (MWh): %s (w/ reserve margin)" % ('{0:,.2f}'.format(total_load), '{0:,.2f}'.format(total_plant_load))


    #check constraints
    for t in years:
            for i,p in enumerate(pp):
                if(t > 0 and x[i,t].getAttr("X") > 0):
                    #print "x: %s , y: %s , q %s" % (x[i,t].getAttr("X"),y[i,t].getAttr("X"),q[i,t].getAttr("X"))
                    blank = 0
    # Check optimization result
    if m.status != GRB.status.OPTIMAL:
        print 'Relaxation is infeasible'
    else:
        print "Optimal Solution Found."
############################################
####### make a horizontal bar chart ########
############################################


    #val = 3+10*rand(5)
    # the bar lengths
    val = [0.0]*num_plant_types #start at zero


    #print val

    #add up total production across entire planning period
    for t in years:
         for s in seasons:
             for h in hours :
                for j,k in pp_types.items():
                    val[j] += load_totals[j,t,s,h]

    for v in val:
        print v
    val = np.asarray(val[0:num_plant_types]) #convert to a numpy array
    print "Sum check (MWh):  %s" % '{0:,.2f}'.format(sum(val))
    pos = arange(num_plant_types)+.5    # the bar centers on the y axis

    ######design elements#######
    #font.set_family('sans-serif')

    # Make a list by cycling through the colors you care about
    # to match the length of your data.
    my_colors = ['k', '#660000', '#FF9900', 'b', 'y',  'g', '0.75']

    x_format = FuncFormatter(func)
    fig, ax = plt.subplots()
    ax.xaxis.set_major_formatter(x_format)

    #labels
    labels = [None]*num_plant_types
    for j,t in pp_types.items():
        labels[j] = pp_types[j]

    labels = array(labels)
    figure(1)
    barh(pos,val, align='center', color = my_colors)
    yticks(pos, labels)
    xlabel('MWh')
    title('Power plant fuel use')
    grid(True)

    show()


except GurobiError:
    print('Error reported')