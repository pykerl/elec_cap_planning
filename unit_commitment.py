#!/opt/python/bin/python2.7
# above line for condor direct execution if need be via condor/isye

#   Electricity Unit Commitment Model including Air Quality Health Impacts
#
#   Author: Paul Kerl (paul.kerl@gatech.edu)
#   
#   Arguments, in order: VSL (in millions of USD2007), 
#                        BETA (in percent per 10 microg / m**3), 
#                        Health_Cost_Included (True/False flag)
#
import datetime #for processing dates
import time #for adding time stamps to files
import gurobipy as gp
#from pylab import * #also includes numpy as np
import csv
from sys import argv #to unpack arguments
#import random #for use on monte-carlo-izing demand load curves, health impacts


#check arguments
def check_arguments(argv):
    script_name, vsl_in, beta_in, true_false_hc_in, start_year_in = argv

    #print "The script is called:", script
    #print "VSL is ", vsl_in
    #print "Beta is ", beta_in
    #print "hc_or_not is", true_false_hc_in
    #True or False hc_or_not
    if true_false_hc_in.strip(" ") not in ('True', 'False'):
        raise Exception("Argument error, health cost included or not is \"" + true_false_hc_in + "\" instead of \"True\" or \"False\"")

    #Beta in range of 0.00 to 0.2
    BETA = float(beta_in)
    if not(BETA > 0.00 and BETA < 0.2):
        raise Exception("Argument error, beta of \"" + beta_in + "\" smaller than 0.00 or larger than 0.2")


    #VSL in range of 0.0 to 30
    VSL = float(vsl_in)
    if not(VSL >= 0.00 and VSL <= 30):
        raise Exception("Argument error, VSL of \"" + vsl_in + "\" smaller than 0.00 or larger than 30")

    if "True" in true_false_hc_in:
        health_cost_included = True
    else :
        health_cost_included = False
    if health_cost_included  :
        print "hc included."
    else :
        print "hc not included."    

    #start year in range of 2004 to 2011
    start_year = int(start_year_in)
    if not(start_year >= 2004 and start_year <= 2011):
        raise Exception("Argument error, start year of \"" + start_year_in + "\" smaller than 2004 or larger than 2011")
   
    return VSL, BETA, health_cost_included, start_year



VSL, BETA, health_cost_included, start_year = check_arguments(argv)
print "VSL is ", str(VSL)
print "Beta is ", str(BETA)
print "hc_or_not is", str(health_cost_included)
print "Start year is", str(start_year)

###############################################################################
#################################  INPUT DATA  ################################
###############################################################################

################################# CONSTANTS ###################################
########## ALWAYS double check constants below when running !!#################

#Note: health_cost_included is now an argument input
#switch to include health costs or not
#health_cost_included = True
#health_cost_included = False

#Note: VSL is now an input argument
VSL = VSL * 1000000 #convert to millions
#VSL
#$7.4MM, USD2006, adjusted to USD2007 via CPI, listed below

#Source:http://yosemite.epa.gov/ee/epa/eerm.nsf/vwAN/EE-0568-22.pdf

#Year    CPI #if needed for 2006 USD VSL
#2006    201.6
#2007    207.342

#VSL = 13.88 * 1000000 #in millions USD 2007 (90th percentile)
#VSL = 1.77 * 1000000 #in millions USD 2007 (10th percentile)
#VSL = 6.22 * 1000000 #in millions USD 2007 (50th percentile, median)
#VSL = 3.46 * 1000000 #in millions USD 2007 (25th percentile)
#VSL = 9.89 * 1000000 #in millions USD 2007 (75th percentile)

#timestamp for files
time_stamp = str(int(time.time())) + "median_HI"
print "Time stamp is: %s" % time_stamp

#Note: BETA is now an input argument
BETA = BETA / 10.0 #convert to 1 micrograms / m**3 PM2.5
#Beta
#BETA = 0.06 / 10.0 #6% per 10 micrograms / m**3 PM2.5

#base_dir = "C:/Users/pyk/Desktop/elec_cap_planning/"
base_dir = ""

#    power plant types    #
pp_types = {0 : 'Coal',
            1 : 'Oil',
            2 : 'Gas',
            3 : 'Hydro',
            4 : 'Nuclear',
            5 : 'Biomass',
            6 : 'Other'}

pp_type_inv = {v.upper():k for k, v in pp_types.items()}

pp_fuel_types = {0 : 'BIT', #coal, bituminous
            1 : 'SUB', #coal, sub-bituminous
            2 : 'NG', #natural gas
            3 : 'WAT', #water/hydro
            4 : 'NUC', #nuclear
            5 : 'WDS', #wood waste
            6 : 'LFG', #landfill gas
            7 : 'MSB', #municipal solid biomass
            8 : 'BLQ', #black liquor -- from paper plants
            9 : 'PC', #petroleum coke
            10 : 'DFO', #distillate fuel oil
            11 : 'RFO', }#residual fuel oil

pp_fuel_type_inv = {v:k for k, v in pp_fuel_types.items()}

#so2 emissions per MWh by fuel type
#Source: http://www.epa.gov/cleanenergy/energy-and-you/affect/air-emissions.html
pp_so2_emissions = {0 : 13, #coal
            1 : 12, #oil
            2 : 0.1, #natural gas
            3 : 0.0, #hydro
            4 : 0.0, #nuclear
            5 : 0.8, #biomass
            6 : 0.0} #other

pp_nox_emissions = {0 : 6, #coal
            1 : 4, #oil
            2 : 1.7, #natural gas
            3 : 0.0, #hydro
            4 : 0.0, #nuclear
            5 : 5.4, #biomass
            6 : 0.0} #other


#load in variable and fuel costs, store via pp_var_costs[year][pp_type]
pp_fuel_types = {0 : 'BIT', #coal, bituminous
            1 : 'SUB', #coal, sub-bituminous
            2 : 'NG', #natural gas
            3 : 'WAT', #water/hydro
            4 : 'NUC', #nuclear
            5 : 'WDS', #wood waste
            6 : 'LFG', #landfill gas
            7 : 'MSB', #municipal solid biomass
            8 : 'BLQ', #black liquor -- from paper plants
            9 : 'PC', #petroleum coke
            10 : 'DFO', #distillate fuel oil
            11 : 'RFO'}#residual fuel oil

#load in variable O&M costs per MW of capacity, store in pp_var_costs
#only charged if the unit is committed, rolled in with committment variable
var_costs_file = base_dir + "data/var_costs.csv"
pp_var_costs = {}

with open(var_costs_file, 'rb') as f:
    reader = csv.reader(f, delimiter=',')
    header = reader.next()
    i = -1
    ## double check the header for consistent header order ##
    for fuel_type in header:
        #check to make sure the header matches the pp_fuel_types dictionary
        if i == -1:
            next
        else:
            if pp_fuel_types[i] not in fuel_type:
                print "Error loading variable costs", \
                       i, fuel_type, pp_fuel_types[i]
        i += 1
    for row in reader:
        year = int(row.pop(0))
        pp_var_costs[year] = map(float, row)

#load in fuel costs per MWh, store in pp_fuel_costs[]
fuel_costs_file = base_dir + "data/fuel_costs.csv"
pp_fuel_costs = {}

with open(fuel_costs_file, 'rb') as f:
    reader = csv.reader(f, delimiter=',')
    header = reader.next()
    i = -1
    ## double check the header for consistent header order ##
    for fuel_type in header:
        #check to make sure the header matches the pp_fuel_types dictionary
        if i == -1:
            next
        else:
            if pp_fuel_types[i] not in fuel_type:
                print "Error loading variable costs", \
                       i, fuel_type, pp_fuel_types[i]
        i += 1
    for row in reader:
        year = int(row.pop(0))
        pp_fuel_costs[year] = map(float, row)

#load in startup costs per MW of capacity, store in startup_costs[]
startup_costs_file = base_dir + "data/startup_costs.csv"
pp_startup_costs = {}

with open(startup_costs_file, 'rb') as f:
    reader = csv.reader(f, delimiter=',')
    header = reader.next()
    i = -1
    ## double check the header for consistent header order ##
    for fuel_type in header:
        #check to make sure the header matches the pp_fuel_types dictionary
        if i == -1:
            next
        else:
            if pp_fuel_types[i] not in fuel_type:
                print "Error loading startup costs", \
                       i, fuel_type, pp_fuel_types[i]
        i += 1
    for row in reader:
        year = int(row.pop(0))
        pp_startup_costs[year] = map(float, row)

#load in fixed yearly per MW costs, store via pp_fixed_costs[year][pp_type]
fixed_costs_file = base_dir + "data/var_costs.csv"
pp_fixed_costs = {}

with open(fixed_costs_file, 'rb') as f:
    reader = csv.reader(f, delimiter=',')
    header = reader.next()
    i = -1
    ## double check the header for consistent header order ##
    for fuel_type in header:
        #check to make sure the header matches the pp_fuel_types dictionary
        if i == -1:
            next
        else:
            if pp_fuel_types[i] not in fuel_type:
                print "Error loading fixed costs", \
                       i, fuel_type, pp_fuel_types[i]
        i += 1
    for row in reader:
        year = int(row.pop(0))
        pp_fixed_costs[year] = map(float, row)

#Note: need to modify "my_color" array to match length of pp_types array above!
num_plant_types = len(pp_types)
#Note: need to modify "my_color" array to match length of pp_types array above!

#reserve margin
R = 0.15 #13.5% within 3 years, and 15% for longer forecasts
# Source: http://pbadupws.nrc.gov/docs/ML0915/ML091540841.pdf
# Note: Georgia Public Service Commission (GPSC)
# "The GPSC approved a 13.5 percent reserve margin for planning within 3
# years and a 15 percent margin for longer forecasts and approved planning that
# identifies the need for new resources beginning in 2009 and continuing
# through 2023."



if health_cost_included == True:
    #PCT emissions rate decrease
    PCT_EMISSIONS = 1 #0.1 #TODO fix emissions rate change

    #PCT emissions rate decrease
    FS_EMISSIONS = 1 #0.01 #TODO fix emissions rate change

    #NONE emissions rate (should be 1.0 except for testing)
    NONE_EMISSIONS_ADJ = 1
else:
    PCT_EMISSIONS, FS_EMISSIONS, NONE_EMISSIONS_ADJ = 0.0, 0.0, 0.0



#Risk-adjusted real discount factor (7%)
int_rate = 0.07 #from dong gu's paper

#Base year for $ discounting ("social discount rate")
base_year = 2007

#max percent change in coal power hour-to-hour
pct_change = 0.25

#running costs / hour
running_cost = 10000


num_years = 1 #number of years in horizon starting at year 2004 through 2012
years = list(xrange(num_years))
#start_year = 2007
real_years = range(start_year, start_year + num_years)

num_days = 31 #31 in July and January
days = list(range(1, num_days+1))

num_hours = 24 #24 hours per day
hours = list(xrange(num_hours))

#months in our case -- july and january here
#months = [1, 7]
months = [7]

################################ END CONSTANTS ################################


######### Decimal/Thousands Formater ##########

def func(num):  # formatter function takes tick value and tick position
    return '{0:,}'.format(int(num))   # change to comma thousands separator and
                                    # truncate decimal

#####################################
########        Classes      ########
#####################################

########    Load Curve   ########
class LoadCurve:
    def __init__(self, in_load, in_date):
        self.load = in_load
        self.date = in_date
    def __str__(self):
        load_print = ""
        for index, value in enumerate(self.load):
            load_print += "\n Hour %d: %.3f MW " % (index, value)
        return "Date: %s, Load: %s" % (self.date, load_print)

########    locations   ########
class Location:
    def __init__(self, lat, lon, state):
        self.lat = lat
        self.lon = lon
        self.state = state
    def __str__(self):
        return "Location: (%f, %f) %s" % (self.lat, self.lon, self.state)

########    power plant costs   ########
class PowerPlantCosts:
    def __init__(self, fixed_cap_cost, fixed_cap_cost_pct, fixed_cap_cost_fs,
                 inc_cap_cost, dec_cap_cost, health_cost, health_cost_pct,
                 health_cost_fs):
        self.fixed_cap_cost = fixed_cap_cost
        self.fixed_cap_cost_pct = fixed_cap_cost_pct
        self.fixed_cap_cost_fs = fixed_cap_cost_fs
        self.inc_cap_cost = inc_cap_cost
        self.dec_cap_cost = dec_cap_cost
        self.health_cost = health_cost
        self.health_cost_pct = health_cost_pct
        self.health_cost_fs = health_cost_fs
    def __str__(self):
        return "Fixed (per MW per year): $%.2f, Inc. Cap: $%.2f per MW, Dec. \
        Cap: $%.2f per MW, Health Cost:  (array of values)" % \
            (self.fixed_cap_cost, self.inc_cap_cost, self.dec_cap_cost)


########    power plants   ########
class PowerPlant:
    def __init__(self, pp_type, pp_fuel_type, cap_factor, capacity,
                 min_power, name, location, costs):
        self.type = pp_type  #type of plant, in number form see "pp_types"
        self.fuel_type = pp_fuel_type #type of plant, as a number, see pp_types
        self.cap_factor = cap_factor#capacity factor, 0 to 1
        self.capacity = capacity    #capacity in MW
        self.min_power = min_power  #minimum power, percentage!
        self.name = name            #name of the plant
        self.location = location    #location of the plant
        self.costs = costs
    def __str__(self):
        return "%s \n\t Type: %s \n\t Cap Factor: %s \n\t Capacity (MW): \
            %s \n\t Minimum Gen (MW): %s \n\t %s \n\t %s" % \
            (self.name, self.type, self.cap_factor, self.capacity, \
             self.min_power, self.location, self.costs)



###############################################################################
#################################  INPUT FILES ################################
###############################################################################

#########################     power plant data    #############################
#load the power plants with extra information
pp = []
# this file has everything in it that doesn't change year-to-year,
# current capacity (2004) etc...
pp_file = base_dir + "data/plant_info.csv"
pp_file = open(pp_file, 'rU')
reader = csv.reader(pp_file)

header = {} #header row store
pp_data = [] #the big set of all the stuff
count = 0
for row in reader:
    #print iter
    if count == 0:
        header = row
    else:
        i = 0
        pp_data_ele = {}
        for h in header:
            pp_data_ele[h] = row[i]
            i = i + 1
        pp_data.append(pp_data_ele)
    count = count + 1
total_capacity_avail = 0 #a check value

emissions_rate_so2 = {} #hourly emissions rate dictionary for output files
emissions_tot_so2 = {} #hourly emissions rate dictionary for output files

for pow_plant in pp_data:
    pp_name = pow_plant['PNAME']
    pp_type = pp_type_inv[pow_plant['PLFUELCT'].upper()]
    pp_oris = pow_plant['ORIS']
    pp_short_name = ""
    if "harllee" in pp_name.lower():
        pp_short_name = "harllee"
    elif "scherer" in pp_name.lower():
        pp_short_name = "scherer"
    elif "bowen" in pp_name.lower():
        pp_short_name = "bowen"
    elif "mcdonough" in pp_name.lower():
        pp_short_name = "mcdonough"
    pp_fuel_type = pp_fuel_type_inv[pow_plant['PLPRMFL']]
    #print pp_type


    #costs
    #fixed_cost currently the same for each year (same real costs)
    #TODO update if needed

    #for 2 months of fixed costs
    fixed_cap_cost = pp_fixed_costs[2007][pp_fuel_type] / 6.0
    fixed_cap_cost_pct = pp_fixed_costs[2007][pp_fuel_type] / 6.0
    fixed_cap_cost_fs = pp_fixed_costs[2007][pp_fuel_type]  / 6.0

    #increase and decrease in capacity costs
    inc_cap_cost = float(pow_plant['INC_COST'])
    dec_cap_cost = float(pow_plant['DEC_COST'])

    health_cost = {}
    health_cost_pct = {}
    health_cost_fs = {}
    text_months = ["01", "07"]
    #first load emissions sensitivities and values for point source plants
    if pp_short_name in ["bowen", "mcdonough", "scherer", "harllee"]:
        print "loading ", pp_short_name
        hc = {}
        if pp_name not in emissions_rate_so2:
            emissions_rate_so2[pp_name] = {}
            emissions_tot_so2[pp_name] = {}
        print "emissions_rate loaded for %s" % pp_name
        for text_month in text_months:
            hc_file_name = base_dir + \
                           "data/hc_data_so4/%s_%s_health_costs.csv" \
                           % (pp_short_name, text_month)
            hc_file = open(hc_file_name, 'rU')
            print hc_file_name
            reader = csv.reader(hc_file)
            header = reader.next()
            for row in reader:
                month = int(row[1])
                day = int(row[2])
                hour = int(row[3])
                val = row[4]
                mwh = row[5]
                emis = row[6]
                emissions_rate_so2[pp_name][month, day, hour] = \
                                                       float(emis) / float(mwh)
                emissions_tot_so2[pp_name][month, day, hour] = float(emis)

                #Calculation        (1/mwh = emissions / mwh * 1 / emissions )
                hc[month, day, hour] = VSL * BETA * float(val) / float(mwh)
                #print month, day, hour


        hc_file.close()
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        health_cost[t, m, d, h] = hc[m, d, h]
                        health_cost_pct[t, m, d, h] = hc[m, d, h]
                        health_cost_fs[t, m, d, h] = hc[m, d, h]
    #next, Load health costs for each emitting (oil, gas, biomass and coal only!)
    elif pp_type in [0, 1, 2, 5, 6]: #for plants in aggregated sources
        #print "loading ", pp_name
        #set the default emissions rate depending on plant type, from eGRID/EPA
        so2_emissions_rate = pp_so2_emissions[pp_type] #lbs / mmbtu * heat rate, converted to per MWh vs. per BTU
        nox_emissions_rate = pp_so2_emissions[pp_type] #lbs / mmbtu * heat rate, converted to per MWh vs. per BTU
        hc = {}
        for text_month in text_months:
            hc_file_name = base_dir + "data/hc_data_so4/%s_%s_health_costs.csv" % (pp_oris, text_month)

            #check if the plants has appeared in CEM files at all
            try:
                with open(hc_file_name):
                    print "Appears in CEM and has HC file"
                    hc_file = open(hc_file_name, 'rU')
                    print hc_file_name
                    reader = csv.reader(hc_file)
                    header = reader.next()
                    if pp_name not in emissions_rate_so2:
                        emissions_rate_so2[pp_name] = {}
                        emissions_tot_so2[pp_name] = {}
                    print "emissions_rate loaded for %s" % pp_name
                    for row in reader:
                        month = int(row[1])
                        day = int(row[2])
                        hour = int(row[3])
                        val = row[4]
                        mwh = row[5]
                        emis = row[6]
                        emis_agg = row[7]
                        if float(mwh) > 0:
                            hc[month, day, hour] = VSL * BETA * float(val) * float(emis) / float(mwh) / float(emis_agg) #val * emissions rate (emis/mwh) / agg emissions
                            emissions_rate_so2[pp_name][month, day, hour] =  float(emis) / float(mwh)
                            emissions_tot_so2[pp_name][month, day, hour] = float(emis_agg)
                        else:
                            hc[month, day, hour] = VSL * BETA * float(val) * so2_emissions_rate / float(emis_agg) #val * emissions rate (emis/mwh) / agg emissions
                            emissions_rate_so2[pp_name][month, day, hour] =  so2_emissions_rate
                            emissions_tot_so2[pp_name][month, day, hour] = float(emis_agg)
                        #print month, day, hour

            except IOError:
                #if the plant doesn't appear in a CEM file, set up the sensitivities, emissions and emissions rates
                print "Does not appear in CEM"
                print "%s|%s|%s" % (pp_name, pp_oris, pp_types[pp_type])

                #use north ga, south ga or wansley depending on plant location
                lat_check = float(pow_plant['LAT'])
                for text_month in text_months:
                    if int(pp_oris) == 55965: #Wansley Combined Cycle doesn't appear in CEM?
                        hc_file_name = base_dir + "data/hc_data_so4/%s_%s_general_health_costs.csv" % ("wansley_comb", text_month)
                    elif lat_check > 33.07: #north georgia for our purposes
                        hc_file_name = base_dir + "data/hc_data_so4/%s_%s_general_health_costs.csv" % ("ga_north", text_month)
                    elif lat_check < 33.07: #south georgia for our purposes
                        hc_file_name = base_dir + "data/hc_data_so4/%s_%s_general_health_costs.csv" % ("ga_south", text_month)
                    else: #plant didn't appear anywhere, that's a problem!
                        print "Fail!"

                   #assign costs for plants without their own CEM file
                    with open(hc_file_name) as hc_file:
                        print "loading from %s" % hc_file_name
                        reader = csv.reader(hc_file)
                        header = reader.next()
                        if pp_name not in emissions_rate_so2:
                            emissions_rate_so2[pp_name] = {}
                            emissions_tot_so2[pp_name] = {}
                        print "emissions_rate loaded for %s" % pp_name
                        for row in reader:
                            month = int(row[1])
                            day = int(row[2])
                            hour = int(row[3])
                            val = row[4]
                            emis_agg = row[7]
                            hc[month, day, hour] = VSL * BETA * float(val) * so2_emissions_rate / float(emis_agg) #val * (emissions rate / total aggregate source emissions)
                            emissions_rate_so2[pp_name][month, day, hour] =  so2_emissions_rate
                            emissions_tot_so2[pp_name][month, day, hour] = float(emis_agg)

        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        health_cost[t, m, d, h] = hc[m, d, h]
                        health_cost_pct[t, m, d, h] = hc[m, d, h]
                        health_cost_fs[t, m, d, h] = hc[m, d, h]



    #else case -- nuclear, other and hydro plants
    else:
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        health_cost[t, m, d, h] = 0.0
                        health_cost_pct[t, m, d, h] = 0.0
                        health_cost_fs[t, m, d, h] = 0.0


    costs = PowerPlantCosts(fixed_cap_cost, fixed_cap_cost_pct, fixed_cap_cost_fs, inc_cap_cost, dec_cap_cost, health_cost, health_cost_pct, health_cost_fs)


    #check value of total capacity available
    total_capacity_avail += float(pow_plant['NAMEPCAP'])*float(pow_plant['CAPFAC_FIXED'])
    #location
    # For reference or testing purposes,
    # Georgia corner coordinates 34.966999, -85.649414
    #                            30.694612, -80.90332

    r_lat = float(pow_plant['LAT'])
    r_lon = float(pow_plant['LON'])
    loc = Location(r_lat, r_lon, "GA")

    #add the power plant
    cap_factor = float(pow_plant['CAPFAC_FIXED'])
    capacity = float(pow_plant['NAMEPCAP'])
    min_power = float(pow_plant['MIN_POW'])

            #         (type, cap_factor, capacity, min_p, name, location, costs):
    ppadd = PowerPlant(pp_type, pp_fuel_type, cap_factor, capacity, min_power, pp_name, loc, costs)

    pp.append(ppadd)

num_plants = len(pp)

#close power plant data file
pp_file.close()

#load up array of load curves for use here 2004-2010 (or for years less than 2010)
lc_data = []
lc_dict = {}
lc_file = base_dir + "data/lc_data/load_curves_2004_2013.csv"
lc_file = open(lc_file, 'rU')
reader = csv.reader(lc_file)
count = 0
for row in reader:
    if count == 0:
        header = row
    else:
        i = 0
        lc_data_ele = {}
        #load up a quick dictionary based on the headers (probably a better way to do this?)
        for h in header:
            lc_data_ele[h] = row[i]
            i = i + 1
        #construct a date
        date = datetime.date(int(lc_data_ele["YEAR"]), int(lc_data_ele["MONTH"]), int(lc_data_ele["DAY"]))

        #get the load from this row
        load = lc_data_ele["LOAD"]

        #get the hour from this row
        hour = int(lc_data_ele["HOUR"])

        #store the load in a load curve dictionary for a given date, hour combo
        if date in lc_dict:
            lc_dict[date][hour] = float(load)
        else:
            lc_dict[date] = {}
            lc_dict[date][hour] = float(load)
    count = count + 1

#next, load the load_curve into LoadCurve objects (better way to do this?)
lc_array = {}
for t in years:
    for m in months:
        for d in days:
            load_new = []
            for hour in hours:
                year_in= start_year + t
                date = datetime.date(year_in, m, d)
                load_new.append(lc_dict[date][hour])
                #print load_new
            lc_array[t, m, d] = LoadCurve(load_new, date)
#print lc

#close load curve file
lc_file.close()


#interest rate adjustments year to year
cost_adj = {}

for y in real_years:
    t = y - base_year
    v = 1 / (1 + int_rate)**t
    cost_adj[y] = v
#print cost_adj

###############################################################################
############################ END INPUT FILES FOR MODEL ########################
###############################################################################

############################ OPTIMIZE #########################################
try:
    #########  create model  #########
    mod = gp.Model("cap_planning")

    #########  optimization parameters  #########
    #Set tolerance if need be, default is 10^-04
    #mod.setParam("MIPGap", .000001)
    #mod.setParam("MIPGap", .001) #0.1% -- to ensure finishing
    mod.setParam("MIPGap", .0025) #0.25% -- to ensure finishing
    mod.setParam("LogFile", base_dir + "logs/gurobi_logs/" + time_stamp + str(health_cost_included) + ".log")


    #########  variables  #########
    #i and
    #x = {} #capacity of plant i in year t
    #y = {} #increased capacity of plant i in year t
    #q = {} #decreased capacity of plant i in year t
    #pi_non = {} #decreased capacity of plant i in year t
    #pi_pct = {} #decreased capacity of plant i in year t
    #pi_fs = {} #decreased capacity of plant i in year t
    z = {} #electricity generated at plant i in year t, month m, day d, hour h
    #z_pct = {} #PCT electricity generated at plant i in year t, month m, day d, hour h
    #z_fs = {} #FS electricity generated at plant i in year t, month m, day d, hour h
    #z_non = {} #non-FS, non-PCT electricity generated at plant i in year t, month m, day d, hour h
    hc = {} #health costs, used to output calculated health costs
    on_u = {} #variable indicating if a plant is on or off, year t, month m, day d, hour h
    start_v = {} #variable indicating if a plant was started on year t, month m, day d, hour h
    shutdown_w = {} #variable indicating if a plant was shut down on year t, month m, day d, hour h

    #capacity of plant i in year t
    # for t in years:
    #     disc = cost_adj[start_year + t] #discounting factor
    #     for i, p in enumerate(pp):
    #         x[i, t] = mod.addVar(vtype = gp.GRB.CONTINUOUS,
    #                           obj = disc * p.costs.fixed_cap_cost,
    #                           name = 'capacity_%s_%s' % (i, t))

    # #inc capacity of plant i in year t
    # for t in years:
    #     disc = cost_adj[start_year + t] #discounting factor
    #     for i, p in enumerate(pp):
    #         y[i, t] = mod.addVar(vtype = gp.GRB.INTEGER,
    #                           obj = disc * p.costs.inc_cap_cost,
    #                           name = 'inc_capacity_%s_%s' % (i, t))

    # #dec capacity of plant i in year t
    # for t in years:
    #     disc = cost_adj[start_year + t] #discounting factor
    #     for i, p in enumerate(pp):
    #         q[i, t] = mod.addVar(vtype = gp.GRB.INTEGER,
    #                           obj = disc * p.costs.dec_cap_cost,
    #                           name = 'dec_capacity_%s_%s' % (i, t))

    #generation type of plant i in year t (binary)
    # for t in years:
    #     for i, p in enumerate(pp):
    #         pi_non[i, t] = mod.addVar(vtype = gp.GRB.BINARY,
    #                           obj = 0.0,
    #                           name = 'pi_non_%s_%s' % (i, t))
    #         pi_pct[i, t] = mod.addVar(vtype = gp.GRB.BINARY,
    #                           obj = 0.0,
    #                           name = 'pi_pct_%s_%s' % (i, t))
    #         pi_fs[i, t] = mod.addVar(vtype = gp.GRB.BINARY,
    #                           obj = 0.0,
    #                           name = 'pi_fs_%s_%s' % (i, t))

    #electricity generated at plant i in year t, month m, day d, hour h
    #also unit commitment variables at plant i in year t, month m, day d, hour h
    for t in years:
        disc = cost_adj[start_year + t] #discounting factor
        for m in months:
            for d in days:
                for h in hours:
                    for i, p in enumerate(pp):
                        fuel_cost = float(pp_fuel_costs[start_year+t][p.fuel_type])
                        startup_cost = float(pp_startup_costs[start_year+t][p.fuel_type] * p.capacity)
                        var_om_cost = float(pp_var_costs[start_year+t][p.fuel_type] * p.capacity * p.cap_factor)
                        #variable indicating if a plant is on during an hour
                        on_u[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.BINARY,
                                          obj = var_om_cost,
                                          name = 'on_or_off_%s_%s_%s_%s_%s' % (i, t, m, d, h))                                                                                    
                        #variable indicating if a plant started in an hour
                        start_v[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.BINARY,
                                          obj = startup_cost,  #TODO add real startup cost here!
                                          name = 'start_%s_%s_%s_%s_%s' % (i, t, m, d, h),
                                          lb = 0.0,
                                          ub = 1.0)                                          
                        #variable indicating if a plant shut down in an hour
                        shutdown_w[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.BINARY,
                                          obj = 0.0,  #TODO add real shutdown cost here!
                                          name = 'shutdown_%s_%s_%s_%s_%s' % (i, t, m, d, h),
                                          lb = 0.0,
                                          ub = 1.0)
                        # z_non[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.CONTINUOUS,
                        #                   obj = disc * (var_cost + p.costs.health_cost[t, m, d, h] * NONE_EMISSIONS_ADJ ),
                        #                   name = 'gen_%s_%s_%s_%s_%s' % (i, t, m, d, h))
                        # z_pct[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.CONTINUOUS,
                        #                   obj = disc * (var_cost + p.costs.health_cost_pct[t, m, d, h] * PCT_EMISSIONS ),
                        #                   name = 'gen_pct_%s_%s_%s_%s_%s' % (i, t, m, d, h))
                        # z_fs[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.CONTINUOUS,
                        #                   obj = disc * (var_cost + p.costs.health_cost_fs[t, m, d, h] * FS_EMISSIONS ),
                        #                   name = 'gen_fs_%s_%s_%s_%s_%s' % (i, t, m, d, h))
                        z[i, t, m, d, h] = mod.addVar(vtype = gp.GRB.CONTINUOUS,
                        #                 obj = 0.0,
                                          obj = disc * (fuel_cost + p.costs.health_cost[t, m, d, h] * FS_EMISSIONS ),
                                          name = 'gen_total_%s_%s_%s_%s_%s' % (i, t, m, d, h))

    # Integrate new variables
    mod.update()

    #########  objective  #########
    #objective
    #NOTE: objective set within variable definitions!
    mod.setAttr(gp.GRB.attr.ModelSense, gp.GRB.MINIMIZE)

    #########  constraints  #########
    cap_constr = {}

    #yearly change in capacity balance constraints
    #for t in years:
        #for i, p in enumerate(pp):
            #if(t > 0):
                #mod.addConstr(x[i, t] - x[i, (t-1)] == y[i, t] - q[i, t] , "change_cap_%s_%s" % (i, t))
                #cap_constr[i, t] = mod.addConstr(x[i, t] - x[i, (t-1)] == y[i, t] - q[i, t] , "change_cap_%s_%s" % (i, t))

    ##starting capacity, year 0
    #for i, p in enumerate(pp):
    #    cap_constr[i, 0] = mod.addConstr(x[i, t] == p.capacity , "change_cap_%s_%s" % (i, t))


    #constraints on pi vars
    #for i, p in enumerate(pp):
    #    for t in years:
    #        if(t > 0):
    #            cap_constr[i, t] = mod.addConstr(x[i, t] - x[i, (t-1)] == y[i, t] - q[i, t] , "change_cap_%s_%s" % (i, t))


    #demand must be met with available capacity
    for h in hours:
        for m in months:
            for d in days:
                for t in years:
                    mod.addConstr(gp.quicksum([z[i, t, m, d, h] for i in range(num_plants)]) == lc_array[t, m, d].load[h], "load_%s_%s_%s_%s" % (h, m, d, t))

    # #reserve must be available if need be -- R = % above load needed on reserve
    # for h in hours:
    #     for m in months:
    #         for d in days:
    #             for t in years:
    #                 #TODO could just change this to >= max(lc_array) for the year t... but for now just leave it since it's easier
    #                 mod.addConstr(gp.quicksum([x[i, t] for i in range(num_plants)]) >= lc_array[t, m, d].load[h] * (1+R), "reserve_%s_%s_%s_%s" % (h, m, d, t))

    ##capacity constraints
    #all plants
    for h in hours:
        for m in months:
            for d in days:
                for t in years:
                    for i, p in enumerate(pp):
                        #capacity of a plant (based on capacity factor and nameplate capacity)
                        #mod.addConstr(z[i, t, m, d, h] <= p.cap_factor * x[i, t], "plant_cap_%s_%s_%s_%s_%s" % (i, t, m, d, h))

                        #constraint indicating if a plant is on or not
                        mod.addConstr(z[i, t, m, d, h] <= p.capacity * p.cap_factor * on_u[i, t, m, d, h], "plant_on_const_%s_%s_%s_%s_%s" % (i, t, m, d, h))                        
                        
                        #baseload capacity (% of minimum capacities) if plant is on
                        mod.addConstr(z[i, t, m, d, h] >= p.min_power * p.capacity * on_u[i, t, m, d, h], "plant_min_cap_%s_%s_%s_%s_%s" % (i, t, m, d, h))

                        #generation must be one of three different types of generation at a plant -- FS, PCT or neither
                        #mod.addConstr(z[i, t, m, d, h] == z_non[i, t, m, d, h] + z_fs[i, t, m, d, h] + z_pct[i, t, m, d, h], "plant_gen_types_%s_%s_%s_%s_%s" % (i, t, m, d, h))

                        #must choose exactly one generation type, but no more! (big-M constraints using p.capacity as "M")
                        #mod.addConstr(z_pct[i, t, m, d, h] <= pi_pct[i, t]*p.capacity, "plant_gen_pct_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        #mod.addConstr(z_non[i, t, m, d, h] <= pi_non[i, t]*p.capacity, "plant_gen_non_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        #mod.addConstr(z_fs[i, t, m, d, h] <= pi_fs[i, t]*p.capacity, "plant_gen_fs_%s_%s_%s_%s_%s" % (i, t, m, d, h))


    #all plants final max capacity
    #for t in years:
    #    for i, p in enumerate(pp):
            #all plants final max capacity
            #mod.addConstr(x[i, t] <= p.capacity , "plant_cap_%s_%s" % (i, t))

            #generation type choice
            #mod.addConstr(pi_pct[i, t] + pi_fs[i, t] + pi_non[i, t] == 1.0, "plant_gen_type_%s_%s" % (i, t))

    #TODO TESTING
    #all plants set to no pct, no fs
    #for t in years:
    #    for i, p in enumerate(pp):
    #        #generation type choice
    #        mod.addConstr(pi_pct[i, t] == 1.0, "plant_gen_set_type_%s_%s" % (i, t))

    #TODO TESTING
    #change in power usage constraint
    for t in years:
        for m in months:
            for d in days:
                for h in hours:
                    for i, p in enumerate(pp):
                        #baseload capacity (just % minimum capacities)
                        if (h > 0 and p.type == 0): #coal plants only
                            mod.addConstr(z[i, t, m, d, h] - z[i, t, m, d, (h-1)] <= pct_change * p.capacity * p.cap_factor, "plant_change_usage_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                            mod.addConstr(z[i, t, m, d, h-1] - z[i, t, m, d, h] <= pct_change * p.capacity * p.cap_factor, "plant_change_usage_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        elif h == 0 and p.type == 0 and d != 1:
                            #0th hour change vs. 23rd hour of the previous day
                            mod.addConstr(z[i, t, m, d, h] - z[i, t, m, d-1, 23] <= pct_change * p.capacity * p.cap_factor, "plant_change_usage_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                            mod.addConstr(z[i, t, m, d-1, 23] - z[i, t, m, d, h] <= pct_change * p.capacity * p.cap_factor, "plant_change_usage_%s_%s_%s_%s_%s" % (i, t, m, d, h))

    #shutdown startup constraints
    for t in years:
        for m in months:
            for d in days:
                for h in hours:
                    for i, p in enumerate(pp):
                        mod.addConstr(start_v[i, t, m, d, h] <= on_u[i, t, m, d, h], "plant_startup_2_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        mod.addConstr(shutdown_w[i, t, m, d, h] <= 1.0 - on_u[i, t, m, d, h], "plant_shutdown_%s_%s_%s_%s_%s" % (i, t, m, d, h))                        
                        
                        ##the following are needed for the strongest valid inequalities for unit commitment
                        if (h > 0) :
                            mod.addConstr(start_v[i, t, m, d, h] - shutdown_w[i, t, m, d, h] == on_u[i, t, m, d, h] - on_u[i, t, m, d, h-1] , "plant_startup_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        elif h == 0 and d != 1 :
                            #0th hour change vs. 23rd hour of the previous day
                            mod.addConstr(start_v[i, t, m, d, h] - shutdown_w[i, t, m, d, h] == on_u[i, t, m, d, h] - on_u[i, t, m, d-1, 23] , "plant_startup_%s_%s_%s_%s_%s" % (i, t, m, d, h))
                        #elif h == 0 and d == 1 : #initial startup costs for that month
                        #    mod.addConstr(start_v[i, t, m, d, h] - shutdown_w[i, t, m, d, h] == on_u[i, t, m, d, h] , "plant_startup_%s_%s_%s_%s_%s" % (i, t, m, d, h))



    #TODO redo these constraints --
    # set certain variables to values for a given scenario

    #PCT at plant bowen in year 2009
    #check if year including 2009 is in this scenario
    #add binary var set = 1.0 (pi_pct[i, t])

    #Fuel Switch (FS) at plant mcdonough in year 2009
    #check if year including 2009 is in this scenario
    #add binary var set = 1.0 (pi_fs[i, t])

    #TODO new constraints not yet written or used yet

    #TODO Monthly Capacity Factor Constraint

    #TODO renewables
    #non-wind, non-solar capacity

    #wind capacity

    #solar capacity

    #renewable electricity standard

    #########  solve  #########
    mod.optimize()

    #########  output  #########

    #calculate health costs

    #health cost total
    hc = 0.0 #calculate total health cost
    for t in years:
        disc = cost_adj[start_year + t] #discount factor
        for m in months:
            for d in days:
                for h in hours:
                    for i, p in enumerate(pp):
                        hc = hc + z[i, t, m, d, h].getAttr("X") * disc * p.costs.health_cost[t, m, d, h]

    #health cost plant total
    hc_arr = {}
    for i, p in enumerate(pp):
        hc_arr[i] = 0.0
        for t in years:
            disc = cost_adj[start_year + t] #discounting factor
            for m in months:
                for d in days:
                    for h in hours:
                        hc_arr[i] = hc_arr[i] + z[i, t, m, d, h].getAttr("X") * disc * p.costs.health_cost[t, m, d, h]

    for var in mod.getVars():
        #gather data for each hour, for each power plant type (coal, nuclear, etc...)
        #inverse the key-value mapping for power plant types
        inv_pp_types = {var:k for k, v in pp_types.items()}
        #print if larger than 0
        #if v.x > 0.0:
            #print "%s\t:\t%.1f " % (v.varName, v.x)


    load_totals = {}
    for t in years:
        for m in months:
            for d in days:
                for h in hours:
                    for j, k in pp_types.items():
                        load_totals[j, t, m, d, h] = 0.0

    #calculate plant load and output results to output.csv
    total_plant_load = 0.0


    years_days_hours = str(num_years) + str(num_days) + str(num_hours)
    if health_cost_included:
        hc_or_not = "_UC_"+ str(start_year) + "_hc_" + years_days_hours + "_" + time_stamp + "_so4"
    else:
        hc_or_not = "_UC_" + str(start_year) + "_no_hc_"  + years_days_hours + "_" + time_stamp + "_so4"

    #turn off writing of huge file
    with open(base_dir + 'data/output/output' + hc_or_not + 'test.csv', 'wb') as csvfile:
        w = csv.writer(csvfile)
        w.writerow(("Name", "Lat", "Lon", "Year", "Month", "Day", "Hour", "Load", "SO2_EMISSIONS_RATE", "SO2_EMISSIONS_TOT", "HEALTH_COST"))
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        for i, p in enumerate(pp):
                            total_plant_load += z[i, t, m, d, h].getAttr("X")
                            for j, k in pp_types.items():
                                if p.type == j:
                                    load_totals[j, t, m, d, h] += z[i, t, m, d, h].getAttr("X")
                            if p.type in [0, 1, 2, 5, 6]:
                                emissions_rate_so2_hour = emissions_rate_so2[p.name][m, d, h]
                                emissions_tot_so2_hour = emissions_tot_so2[p.name][m, d, h]
                                health_cost_hour = p.costs.health_cost[t, m, d, h]
                            else:
                                emissions_rate_so2_hour = 0.0
                                emissions_tot_so2_hour = 0.0
                                health_cost_hour = 0.0
                            #print (p.name, p.location.lat, p.location.lon, t, m, d, h, z[i, t, m, d, h].getAttr("X"), emissions_rate_so2_hour, emissions_tot_so2_hour, health_cost_hour)
                            w.writerow((p.name, p.location.lat, p.location.lon, t, m, d, h, z[i, t, m, d, h].getAttr("X"), emissions_rate_so2_hour, emissions_tot_so2_hour, health_cost_hour))


        print "--------------------------------------------"
        if health_cost_included == True:
            print "Objective (with health costs): $" + '{0:,.2f}'.format(mod.objVal)
            print "Health cost: $%s" % func(hc)

        else:
            print "Objective (no health costs): $" + '{0:,.2f}'.format(mod.objVal)
            print "Health cost: $%s" % func(hc)
        print "--------------------------------------------"
    
    #calculate individual plant load and output total results for each plant
    with open(base_dir + 'data/output/output_plant_test' + hc_or_not + '.csv', 'wb') as csvfile:
        w = csv.writer(csvfile)
        w.writerow(("Name", "Type", "Lat", "Lon", "Load", "Health_Impact", "Var_Cost_2004", "Var_Cost_2011", "Capacity", "Fuel_Type"))
        for i, p in enumerate(pp):
            plant_load = 0.0
            for t in years:
                for m in months:
                    for d in days:
                        for h in hours:
                            plant_load += z[i, t, m, d, h].getAttr("X")
            w.writerow((p.name, pp_types[p.type], p.location.lat, p.location.lon, plant_load, hc_arr[i], pp_var_costs[2004][p.fuel_type], pp_var_costs[2011][p.fuel_type], p.capacity, pp_fuel_types[p.fuel_type]))

    #calculate plant type load and output total results for each plant type
    with open(base_dir + 'data/output/output_plant_type_test' + hc_or_not + '.csv', 'wb') as csvfile:
        w = csv.writer(csvfile)
        w.writerow(("Type", "Year", "Month", "Day", "Hour", "Load"))
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        for j, pp_type in pp_types.items():
                            w.writerow((pp_type, t, m, d, h, load_totals[j, t, m, d, h]))

    #calculate individual plant commitment and output 0,1 matrix for each plant
    with open(base_dir + 'data/output/output_plant_UC_test' + hc_or_not + '.csv', 'wb') as csvfile:
        w = csv.writer(csvfile)
        plant_arr = []
        plant_arr.append("Year")
        plant_arr.append("Month")
        plant_arr.append("Day")
        plant_arr.append("Hour")        
        for i, p in enumerate(pp):
            plant_arr.append(p.name)
        w.writerow(plant_arr)
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        row_write = []
                        row_write.append(str(t+start_year)) #year                        
                        row_write.append(str(m)) #month
                        row_write.append(str(d)) #day
                        row_write.append(str(h)) #hour
                        for i, p in enumerate(pp):
                            row_write.append(str(on_u[i, t, m, d, h].getAttr("X")+start_v[i, t, m, d, h].getAttr("X")))
                        w.writerow(row_write)

    #calculate individual plant generation and output generation for each plant
    with open(base_dir + 'data/output/output_plant_GEN_test' + hc_or_not + '.csv', 'wb') as csvfile:
        w = csv.writer(csvfile)
        plant_arr = []
        plant_arr.append("Year")
        plant_arr.append("Month")
        plant_arr.append("Day")
        plant_arr.append("Hour")        
        for i, p in enumerate(pp):
            plant_arr.append(p.name)
        w.writerow(plant_arr)
        for t in years:
            for m in months:
                for d in days:
                    for h in hours:
                        row_write = []
                        row_write.append(str(t+start_year)) #year                        
                        row_write.append(str(m)) #month
                        row_write.append(str(d)) #day
                        row_write.append(str(h)) #hour
                        for i, p in enumerate(pp):
                            row_write.append(str(z[i, t, m, d, h].getAttr("X")))
                        w.writerow(row_write)

    #add up total production across entire planning period
    total_load = 0.0
    for h in hours:
        for m in months:
            for d in days:
                for t in years:
                    total_load += lc_array[t, m, d].load[h]
    #these should match...
    print "Total load (MWh): %s (generated)\nPlant load (MWh): %s (demanded)" % ('{0:,.2f}'.format(total_load), '{0:,.2f}'.format(total_plant_load))


    #check constraints
#==============================================================================
#     for t in years:
#             for i, p in enumerate(pp):
#                 if(t > 0 and x[i, t].getAttr("X") > 0):
#                     #print "x: %s , y: %s , q %s" % (x[i, t].getAttr("X"), y[i, t].getAttr("X"), q[i, t].getAttr("X"))
#                     blank = 0
#==============================================================================

    # Check optimization result
    if mod.status != gp.GRB.status.OPTIMAL:
        print 'Relaxation is infeasible'
    else:
        print "Optimal Solution Found."

except gp.GurobiError as e:
    print "Oops, gurobi error! \"%s, \" a.k.a. error #%s " % (e.message, e.errno)