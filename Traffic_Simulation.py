# -*- coding: utf-8 -*-
"""
Created on Thu May 20 01:50:10 2021

@author: Albert

#Equations used for this program is from the research paper"Traffic Flow Optimization Using a Quantum Annealer", source: https://www.researchgate.net/publication/321945163_Traffic_Flow_Optimization_Using_a_Quantum_Annealer


NOTICE: You are not allowed to use any instance of this code for commercial purposes


Grabs all simple routes from one destination to another.
For this first iteration of code all cars are sharing the same starting point
& destination for simplicity and educational purposes.
The cost function takes in consideration of all cars and routes that share the same 
road segment.
Distributes cars to certain routes after turning the traffic problem into a QUBO problem.

The number of routes and cars can scale up depending on what you enter into the Simulation() class function
"""
import random
import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
from pyqubo import Array, Binary,Spin
import neal


class Simulation():
    car_database : {
        }
    
    #Below inside __init__ are just defualt parameters just encase nothing is specified
    def __init__(self, cars=10, max_routes = 3, shared_destinations = 1):
        #initiating global variables for the Simulation class
        self.cars = cars
        self.max_routes = max_routes
        self.car_database = {
        }
        self.shared_destinations = shared_destinations
        self.G = G = ox.graph_from_place('Morgantown, WV, USA', network_type='all')
        self.route_list = []
        self.edges = []
        self.colors = ['r', 'y', 'c','b','g','y']
        self.filtered=[]
        #running the methods
        self.initiate()
        self.create_binary_equation()
        self.plot_graph()
        
        
    def initiate(self):
        #adds list of routes for generator
        routes = self.Generate_routes()
        print("Number of routes:", len(routes))
        #generating empty dictionaries that will be filled
        self.car_database["routes"] = {}
        self.car_database["cars"] = {}
        for j in range(len(routes)):
            #self.car_database["routes"][("route_" + str(j))] =[routes[j]]
            self.car_database["routes"][("route_" + str(j))]  = {"Path":[routes[j]],"street_segments":self.get_street_segments(routes[j])} 
            #self.car_database["routes"][("route_" + str(j))][routes]
        for x in range(self.cars):
            if (self.shared_destinations > 1) & (x > self.cars/self.shared_destinations):
                #create a new destination point
                print("not implemented yet")
            else:
                #self.car_database[("car_" + str(x))] = routes
                #help for indexing for quantum optimization
                route_list = []
                for z in range(len(routes)):
                    route_list.append("route_" + str(z))
                self.car_database["cars"][("car_" + str(x))] = {"routes": route_list}
        return
    
    
    def route_filter(self, routes, max_routes=3):
        filtered_routes = []
        #removes duplicate lists
        routes = [list(t) for t in set(tuple(element) for element in routes)]
        if len(routes)>max_routes:
            for x in range(max_routes):
            #gets the smallest paths
                filtered_routes.append(routes.pop( routes.index(min(routes))))
                
            return filtered_routes
        else:
            return routes
        
    def Generate_routes(self):
       
        #creating the origin and destination points
        orig_node = list(self.G.nodes())[random.randint(0,len(self.G.nodes())-1)]
        dest_node = list(self.G.nodes())[random.randint(0,len(self.G.nodes())-2)]
        
        #below are two different algorithms used to help collect a list of routes
        try:
            for path in nx.all_shortest_paths(self.G, orig_node, dest_node,weight = "travel_time" ):
                self.route_list.append(path)
        except:
            print("Couldn't find a path to destination, please run the program again.")

        for path in nx.all_shortest_paths(self.G, orig_node, dest_node, weight = 'length' ):
            self.route_list.append(path)
        
        #print("Number of routes:", len(self.route_list))
        self.filtered = self.route_filter(self.route_list,self.max_routes)
        return self.filtered
    
    def plot_graph(self):
        if len(self.route_list) > 1:
            try:
                fig, ax = ox.plot_graph_routes(self.G, self.filtered, node_size=0, )
            except:
                print("Error with the routes, number of routes:", len(self.route_list))
        else:
            fig, ax = ox.plot_graph_route(self.G, self.route_list[0], node_size=0, )
            
    def create_binary_equation(self):
        #matrix will be created to help make the binary equation
        V_matrix = Array.create('q', shape=(self.cars, len(self.car_database["routes"])) , vartype='BINARY')
        
        #only elements used in the array will be added to the equation
        #Ex. car_4 with route_5, routes_6, & route_7 will have elements
        #V_matrix[3][4], V_matrix[3][5], V_matrix[3][6]
        
        #looping through the car_database to create the equation
        V = 0
        Q = 0
        #Right side equation of the summation of individual cars and route options
        for i in range(self.cars):
            for j in range(len(self.car_database["routes"])):
                #Creating the summation of qij's routes Ex. q11 + q12 + q13
                Q = (V_matrix[i][self.grab_number(self.car_database["cars"]["car_"+str(i)]["routes"][j])] - 1) + Q
            V = Q**2 + V
            Q = 0
        
        #Cost function will be dinamic, updating depending on what car is taking what route that moment
        Objective_function = self.cost_function(V_matrix) + V
        
        model = Objective_function.compile()
        bqm = model.to_bqm()
        sa = neal.SimulatedAnnealingSampler()
        sampleset = sa.sample(bqm, num_reads=10)
        samples = model.decode_sampleset(sampleset)
        best_sample = max(samples, key=lambda s: s.energy)
        #print(best_sample.sample)
        Solution = [k for k,v in best_sample.sample.items() if v == 0]
        
        print("\nSolution:", Solution)
        
        #translate the QUBO solution matrix into commands that show the routes assigned to cars
        self.translate_solution(Solution)
        
        return Objective_function
    
    def cost_function(self, V_matrix):
        print("Creating the cost function....")
        #check and compare street segments 
        #adding all selected route road segments together
        all_segments = []
        for i in range(len(self.car_database["routes"])):
            #all_segments.append(self.car_database["routes"][("route_" + str(i))]["street_segments"])
            all_segments = all_segments + self.car_database["routes"][("route_" + str(i))]["street_segments"]
        #removes all duplicates
        all_segments = list(set().union( all_segments))
        
        #randomly assign a route to a car for cost function then updates on each iteration (in future improvements to this code)
        self.car_database["route_assignments"] = {}
        for j in range(self.cars):
            #print("Number of Cars:",self.cars)
            #print("Cost_function:",self.car_database["cars"]["car_" + str(j)]["routes"][0])
            self.car_database["route_assignments"]["car_" + str(j)] = {}
            self.car_database["route_assignments"]["car_" + str(j)] = self.car_database["cars"]["car_" + str(j)]["routes"][random.randint(0,len(self.car_database["cars"]["car_" + str(j)]["routes"])-1)] 
        
        #Total Cost
        Cost = 0
        #Cost for a particular street segment
        Cost_s = 0
        #loop through street segments
        for s in all_segments:
            for k in range(len(self.car_database["route_assignments"])):
                if s in self.car_database["routes"][(self.car_database["route_assignments"]["car_" + str(k)])]["street_segments"]:
                    #add the element of the car and the element of the route, using grab_number method
                    Cost_s = V_matrix[k][self.grab_number(self.car_database["route_assignments"]["car_" + str(k)])] + Cost_s
                    #print("Cost Function testing:", self.grab_number(self.car_database["route_assignments"]["car_" + str(k)])+Cost_s)
                    
            Cost = (Cost_s)**2  + Cost
            Cost_s = 0
            #if any(map(lambda each: each in all_segments[z], all_segments + self.car_database["routes"][("route_" + str(i))]["street_segments"] )) 
        print("Creating the Objective function....")
        return Cost
        
    def get_street_segments(self, path):
        list1 = path
        list2 = list1
        #creates a list of road segments by using a list of intersections
        road_segments = [(list1[i], list2[i+1]) for i in range(0, len(list1)-1)]
        
        return road_segments
    
    def grab_number(self, string):
        #grabs all number in a string
        #print("grab_number:", int(''.join(char for char in string if char.isdigit())))
        try:
            return int(' '.join(char for char in string if char.isdigit()))
        except:
            # to just return the string if there is more than one number
            return ' '.join(char for char in string if char.isdigit())
        
        
    def translate_solution(self, Solution):
        #translate the QUBO solution matrix into commands that show the routes assigned to cars
        translation = ''
        for assignment in Solution:
            temp = self.grab_number(assignment)
            translation = translation + "Car " + temp[0] + " Take Route '" + temp[2] + "'\n"
        print("\nQUBO solution translation:")
        print(translation)
        return
        
    def print_max_routes(self):
        print(self.max_routes)
        return
    
    def print_car_database(self):
        print(self.car_database)
        return
    
    def print_car_database_keys(self):
        print("Keys of the database:", self.car_database.keys())
        return
        
    def print_car_route_names(self):
        print(self.car_database["cars"])
        return
    def print_routes_info(self):
        print(self.car_database["routes"])
        return
    def return_car_database(self):
        return self.car_database

#below are just examples to run certain commands
#Simulation(5, 5).print_car_database()
#Simulation(5, 5).print_car_database_keys()
#Simulation(5,5).print_routes_info()
#Simulation(5, 5).print_car_route_names()
#print(Simulation(10,5).return_car_database()["route_assignments"])
Simulation(10, 5)