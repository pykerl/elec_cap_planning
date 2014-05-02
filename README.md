## Electricity Generation Unit Commitment Including Air Quality
=================

An electricity generation unit commitment model including air quality for the state of Georgia. The model is a mixed integer linear program (MIP), and was written in python using the gurobipy interface for the Gurobi solver. The model is a proof-of-concept that runs unit commitment and hourly generation dispatch decisions on a little under 100 power plants for the state of Georgia, over a one month time frame. The model newly includes monetized health impacts in addition to fuel, operations and maintenance and plant unit commitment startup costs.

General Necessary Inputs
* Hourly air quality emissions-concentration sensitivities
* Unit commitment and generation costs for each power plant
* Fuel cost estimates
* Plant heat rate estimates
* Health impact concentration-response functions
* Electricity hourly demand curves

For more information, contact [Paul Kerl](http://www2.isye.gatech.edu/~pkerl3)