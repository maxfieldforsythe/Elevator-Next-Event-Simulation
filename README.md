# Elevator-Next-Event-Simulation
This is a program which simulates an elevator bringing employees to work in the morning. The program takes 4 arguments: floors, elevators, a uniform random number file, and the number of days to run the sim. The sim takes into account time to load elevators, time for each elevator to reach the next floor and unload, and time to descend. Groups arrive to the queue in random sizes of 1-8 (geo) and arrive 2-90 seconds (exp) apart. The times of people arrival and when they arrive on the floor where they work are used to calculate average and standard delays per person.  
