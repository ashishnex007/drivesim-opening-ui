#!/usr/bin/env python

# Copyright (c) 2018-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Welcome to CARLA scenario_runner

This is the main script to be executed when running a scenario.
It loads the scenario configuration, loads the scenario and manager,
and finally triggers the scenario execution.
"""

from __future__ import print_function
import random
import glob
import traceback
import argparse
from argparse import RawTextHelpFormatter
from datetime import datetime
from distutils.version import LooseVersion
import importlib
import inspect
import os
import signal
import sys
import time
import json
import pkg_resources

import carla

from srunner.scenarioconfigs.openscenario_configuration import OpenScenarioConfiguration
from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.scenario_manager import ScenarioManager
from srunner.scenarios.open_scenario import OpenScenario
from srunner.scenarios.route_scenario import RouteScenario
from srunner.tools.scenario_parser import ScenarioConfigurationParser
from srunner.tools.route_parser import RouteParser
from srunner.tools.osc2_helper import OSC2Helper
from srunner.scenarios.osc2_scenario import OSC2Scenario
from srunner.scenarioconfigs.osc2_scenario_configuration import OSC2ScenarioConfiguration

# Version of scenario_runner
VERSION = '0.9.13'

def get_actor_blueprints(world, filter_, generation):
    bps = world.get_blueprint_library().filter(filter_)
    # bps = list(filter(lambda x: x.id in filter_, bps))
    
    if generation.lower() == "all":
        return bps
    # print(bps)
    # If the filter returns only one bp, we assume that this one needed
    # and therefore, we ignore the generation
    if len(bps) == 1:
        return bps

    try:
        int_generation = int(generation)
        # Check if generation is in available generations
        if int_generation in [1, 2]:
            bps = [x for x in bps if int(x.get_attribute('generation')) == int_generation]
            return bps
        else:
            print("   Warning! Actor Generation is not valid. No actor will be spawned.")
            return []
    except:
        print("   Warning! Actor Generation is not valid. No actor will be spawned.")
        return []

class ScenarioRunner(object):

    """
    This is the core scenario runner module. It is responsible for
    running (and repeating) a single scenario or a list of scenarios.

    Usage:
    scenario_runner = ScenarioRunner(args)
    scenario_runner.run()
    del scenario_runner
    """

    ego_vehicles = []

    # Tunable parameters
    client_timeout = 100.0  # in seconds
    wait_for_world = 200.0  # in seconds
    frame_rate = 20.0      # in Hz

    # CARLA world and scenario handlers
    world = None
    manager = None

    finished = False

    additional_scenario_module = None

    agent_instance = None
    module_agent = None

    def __init__(self, args):
        """
        Setup CARLA client and world
        Setup ScenarioManager
        """
        self._args = args

        if args.timeout:
            self.client_timeout = float(args.timeout)

        # First of all, we need to create the client that will send the requests
        # to the simulator. Here we'll assume the simulator is accepting
        # requests in the localhost at port 2000.
        self.client = carla.Client(args.host, int(args.port))
        self.client.set_timeout(self.client_timeout)
        dist = pkg_resources.get_distribution("carla")
        if LooseVersion(dist.version) < LooseVersion('0.9.12'):
            raise ImportError("CARLA version 0.9.12 or newer required. CARLA version found: {}".format(dist))

        # Load agent if requested via command line args
        # If something goes wrong an exception will be thrown by importlib (ok here)
        if self._args.agent is not None:
            module_name = os.path.basename(args.agent).split('.')[0]
            sys.path.insert(0, os.path.dirname(args.agent))
            self.module_agent = importlib.import_module(module_name)

        # Create the ScenarioManager
        self.manager = ScenarioManager(self._args.debug, self._args.sync, self._args.timeout)

        # Create signal handler for SIGINT
        self._shutdown_requested = False
        if sys.platform != 'win32':
            signal.signal(signal.SIGHUP, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._start_wall_time = datetime.now()

    def destroy(self):
        """
        Cleanup and delete actors, ScenarioManager and CARLA world
        """

        self._cleanup()
        if self.manager is not None:
            del self.manager
        if self.world is not None:
            del self.world
        if self.client is not None:
            del self.client

    def _signal_handler(self, signum, frame):
        """
        Terminate scenario ticking when receiving a signal interrupt
        """
        self._shutdown_requested = True
        if self.manager:
            self.manager.stop_scenario()
            self._cleanup()
            if not self.manager.get_running_status():
                raise RuntimeError("Timeout occurred during scenario execution")

    def _get_scenario_class_or_fail(self, scenario):
        """
        Get scenario class by scenario name
        If scenario is not supported or not found, exit script
        """

        # Path of all scenario at "srunner/scenarios" folder + the path of the additional scenario argument
        scenarios_list = glob.glob("{}/srunner/scenarios/*.py".format(os.getenv('SCENARIO_RUNNER_ROOT', "./")))
        scenarios_list.append(self._args.additionalScenario)

        for scenario_file in scenarios_list:

            # Get their module
            module_name = os.path.basename(scenario_file).split('.')[0]
            sys.path.insert(0, os.path.dirname(scenario_file))
            scenario_module = importlib.import_module(module_name)

            # And their members of type class
            for member in inspect.getmembers(scenario_module, inspect.isclass):
                if scenario in member:
                    return member[1]

            # Remove unused Python paths
            sys.path.pop(0)

        print("Scenario '{}' not supported ... Exiting".format(scenario))
        sys.exit(-1)

    def _cleanup(self):
        """
        Remove and destroy all actors
        """
        if self.finished:
            return

        self.finished = True

        # Simulation still running and in synchronous mode?
        if self.world is not None and self._args.sync:
            try:
                # Reset to asynchronous mode
                settings = self.world.get_settings()
                settings.synchronous_mode = False
                settings.fixed_delta_seconds = None
                self.world.apply_settings(settings)
                self.client.get_trafficmanager(int(self._args.trafficManagerPort)).set_synchronous_mode(False)
            except RuntimeError:
                sys.exit(-1)

        self.manager.cleanup()

        CarlaDataProvider.cleanup()

        for i, _ in enumerate(self.ego_vehicles):
           
            if self.ego_vehicles[i]:
                if not self._args.waitForEgo and self.ego_vehicles[i] is not None and self.ego_vehicles[i].is_alive:
                    print("Destroying ego vehicle {}".format(self.ego_vehicles[i].id))
                    self.ego_vehicles[i].destroy()
                self.ego_vehicles[i] = None
        self.ego_vehicles = []

        if self.agent_instance:
            self.agent_instance.destroy()
            self.agent_instance = None

    def _prepare_ego_vehicles(self, ego_vehicles):
        """
        Spawn or update the ego vehicles
        """
        
        if not self._args.waitForEgo:
            # ego_vehicles = ["vehicle.auto02.auto02"]
            for vehicle in ego_vehicles:
                self.ego_vehicles.append(CarlaDataProvider.request_new_actor(vehicle.model,
                                                                             vehicle.transform,
                                                                             vehicle.rolename,
                                                                             random_location=vehicle.random_location,
                                                                             color=vehicle.color,
                                                                             actor_category=vehicle.category))
        else:
            ego_vehicle_missing = True
            while ego_vehicle_missing:
                self.ego_vehicles = []
                ego_vehicle_missing = False
                for ego_vehicle in ego_vehicles:
                    ego_vehicle_found = False
                    carla_vehicles = CarlaDataProvider.get_world().get_actors().filter('vehicle.*')
                    
                    for carla_vehicle in carla_vehicles:
                        if carla_vehicle.attributes['role_name'] == ego_vehicle.rolename:
                            ego_vehicle_found = True
                            self.ego_vehicles.append(carla_vehicle)
                            break
                    if not ego_vehicle_found:
                        ego_vehicle_missing = True
                        break

            for i, _ in enumerate(self.ego_vehicles):
               
                self.ego_vehicles[i].set_transform(ego_vehicles[i].transform)
                CarlaDataProvider.register_actor(self.ego_vehicles[i])

        # sync state
        if CarlaDataProvider.is_sync_mode():
            self.world.tick()
        else:
            self.world.wait_for_tick()

    def _analyze_scenario(self, config):
        """
        Provide feedback about success/failure of a scenario
        """
        print(self.world.get_weather())
        # Create the filename
        current_time = str(datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
        junit_filename = None
        json_filename = None
        config_name = config.name
        # print(os.path.dirname(os.getcwd())

        if self._args.outputDir != '':
            config_name = os.path.join(self._args.outputDir, config_name)

        if self._args.junit:
            junit_filename = config_name + current_time + ".xml"
        if self._args.json:
            json_filename = config_name + current_time + ".json"
        filename = None
        if self._args.file:
            filename = config_name + current_time + ".txt"

        # if not os.path.exists(filename):             
        #     with open(filename, "w") as file:
        #         file.write('\n')
        #         file.close()
        if not self.manager.analyze_scenario(self._args.output, filename, junit_filename, json_filename):
            print("All scenario tests were passed successfully!")
        else:
            print("Not all scenario tests were successful")
            if not (self._args.output or filename or junit_filename):
                print("Please run with --output for further information")

    def _record_criteria(self, criteria, name):
        """
        Filter the JSON serializable attributes of the criterias and
        dumps them into a file. This will be used by the metrics manager,
        in case the user wants specific information about the criterias.
        """
        file_name = name[:-4] + ".json"

        # Filter the attributes that aren't JSON serializable
        with open('temp.json', 'w', encoding='utf-8') as fp:

            criteria_dict = {}
            for criterion in criteria:

                criterion_dict = criterion.__dict__
                criteria_dict[criterion.name] = {}

                for key in criterion_dict:
                    if key != "name":
                        try:
                            key_dict = {key: criterion_dict[key]}
                            json.dump(key_dict, fp, sort_keys=False, indent=4)
                            criteria_dict[criterion.name].update(key_dict)
                        except TypeError:
                            pass

        os.remove('temp.json')

        # Save the criteria dictionary into a .json file
        with open(file_name, 'w', encoding='utf-8') as fp:
            json.dump(criteria_dict, fp, sort_keys=False, indent=4)
    
    
    def set_traffic_light_time(self, duration=5): #traffic light manager
        actor_list = self.world.get_actors()
        for actor_ in actor_list:
            
            if isinstance(actor_, carla.TrafficLight):
                # actor_.set_state(carla.TrafficLightState.Red) 
                # actor_.set_red_time(1.0)
                actor_.set_state(carla.TrafficLightState.Green) 
                actor_.set_green_time(1000.0)

    def set_car_light(self, tm): #traffic light manager
        actor_list = self.world.get_actors()
        for actor_ in actor_list:
            print(actor_)
            if isinstance(actor_, carla.Vehicle):
                # actor_.set_state(carla.TrafficLightState.Red) 
                # actor_.set_red_time(1.0)
                tm.update_vehicle_lights(actor_, True) 
                
    def find_weather_presets(self):
        import re
        rgx = re.compile('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)')
        name = lambda x: ' '.join(m.group(0) for m in rgx.finditer(x))
        presets = [x for x in dir(carla.WeatherParameters) if re.match('[A-Z].+', x)]
        presets_dict={}
        for x in presets:
            presets_dict[name(x)]= getattr(carla.WeatherParameters, x)
        return presets_dict     

    def set_weather_preset(self, weather_name, weather_preset = carla.WeatherParameters.WetCloudySunset):
        presets_dict = self.find_weather_presets()
        weather_preset = presets_dict[weather_name]
        self.world.set_weather(weather_preset)
        print(self.world.get_weather())

    def _load_and_wait_for_world(self, town, ego_vehicles=None):
        """
        Load a new CARLA world and provide data to CarlaDataProvider
        """

        if self._args.reloadWorld:
            self.world = self.client.load_world(town)
        else:
            # if the world should not be reloaded, wait at least until all ego vehicles are ready
            
            ego_vehicle_found = False
            if self._args.waitForEgo:
                while not ego_vehicle_found and not self._shutdown_requested:
                    vehicles = self.client.get_world().get_actors().filter('vehicle.*')
                    for ego_vehicle in ego_vehicles:
                        ego_vehicle_found = False
                        for vehicle in vehicles:
                            if vehicle.attributes['role_name'] == ego_vehicle.rolename:
                                ego_vehicle_found = True
                                break
                        if not ego_vehicle_found:
                            print("Not all ego vehicles ready. Waiting ... ")
                            time.sleep(1)
                            break

        self.world = self.client.get_world()


        if self._args.sync:
            settings = self.world.get_settings()
            settings.synchronous_mode = True
            settings.fixed_delta_seconds = 1.0 / self.frame_rate
            self.world.apply_settings(settings)

        CarlaDataProvider.set_client(self.client)
        CarlaDataProvider.set_world(self.world)

        
        # Wait for the world to be ready
        if CarlaDataProvider.is_sync_mode():
            self.world.tick()
        else:
            self.world.wait_for_tick()

        map_name = CarlaDataProvider.get_map().name.split('/')[-1]
        if map_name not in (town, "OpenDriveMap"):
            print("The CARLA server uses the wrong map: {}".format(map_name))
            print("This scenario requires to use map: {}".format(town))
            return False
        
        return True

    def spawn_specific_vehicle(self, indic_pat, number_of_vehicles, tm, synchronous_master, spawn_points):
        
        SpawnActor = carla.command.SpawnActor
        SetAutopilot = carla.command.SetAutopilot
        FutureActor = carla.command.FutureActor

        blueprints = get_actor_blueprints(self.world, "vehicle.{}.*".format(indic_pat), "All")
        
        number_of_spawn_points = len(spawn_points)

        batch = []
        vehicles_list = []
        # number_of_vehicles = self._args.num_vehicles
        

        for n, transform in enumerate(spawn_points):
            if n >= number_of_vehicles:
                break
            blueprint = random.choice(blueprints)
            if blueprint.has_attribute('color'):
                color = random.choice(blueprint.get_attribute('color').recommended_values)
                blueprint.set_attribute('color', color)
            if blueprint.has_attribute('driver_id'):
                driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
                blueprint.set_attribute('driver_id', driver_id)
            
        

            # spawn the cars and set their autopilot and light state all together
            batch.append(SpawnActor(blueprint, transform)
                .then(SetAutopilot(FutureActor, True, tm.get_port())))
        
        spawn_point_left = spawn_points[n + 1:]

        for response in self.client.apply_batch_sync(batch, synchronous_master):
            if response.error:
                print(response.error)
            else:
                vehicles_list.append(response.actor_id)
        
        # if args.car_lights_on:
        all_vehicle_actors = self.world.get_actors(vehicles_list)
        for actor in all_vehicle_actors:
            # print(actor)
            # actor.set_target_velocity(30)
            tm.update_vehicle_lights(actor, True) 
            self.set_car_light(tm)

        return spawn_point_left

    def _load_and_run_scenario(self, config):
        """
        Load and run the scenario given by config
        """
        result = False
        if not self._load_and_wait_for_world(config.town, config.ego_vehicles):
            self._cleanup()
            return False

        if self._args.agent:
            agent_class_name = self.module_agent.__name__.title().replace('_', '')
            try:
                self.agent_instance = getattr(self.module_agent, agent_class_name)(self._args.agentConfig)
                config.agent = self.agent_instance
            except Exception as e:          # pylint: disable=broad-except
                traceback.print_exc()
                print("Could not setup required agent due to {}".format(e))
                self._cleanup()
                return False

        CarlaDataProvider.set_traffic_manager_port(int(self._args.trafficManagerPort))
        tm = self.client.get_trafficmanager(int(self._args.trafficManagerPort))
        
        tm.set_random_device_seed(int(self._args.trafficManagerSeed))
        

        if self._args.sync:
            tm.set_synchronous_mode(True)
            synchronous_master = True
        else:
            synchronous_master = False

        # Prepare scenario
        print("Preparing scenario: " + config.name)
        try:
            
            self._prepare_ego_vehicles(config.ego_vehicles)
            
            SpawnActor = carla.command.SpawnActor
            SetAutopilot = carla.command.SetAutopilot
            FutureActor = carla.command.FutureActor

            if self._args.spawn_vehicle:
                # blueprints = get_actor_blueprints(self.world, ["vehicle.auto02.auto02", "vehicle.bus01.model1"], "All")
                spawn_points = self.world.get_map().get_spawn_points()
                if self._args.spawn_vehicle_Indic_HeavyVehicle:
                    indic_pat = 'indic_heavyvehicle'
                    spawn_points = self.spawn_specific_vehicle(indic_pat, self._args.num_vehicles_Indic_HeavyVehicle, tm, synchronous_master, spawn_points)
                if self._args.spawn_vehicle_Indic_ThreeWheeler: 
                    indic_pat = 'indic_threewheeler'
                    spawn_points = self.spawn_specific_vehicle(indic_pat, self._args.num_vehicles_Indic_ThreeWheeler, tm, synchronous_master, spawn_points)
                if self._args.spawn_vehicle_Indic_FourWheeler: 
                    indic_pat = 'indic_fourwheeler'
                    spawn_points = self.spawn_specific_vehicle(indic_pat, self._args.num_vehicles_Indic_FourWheeler, tm, synchronous_master, spawn_points)     
                if self._args.spawn_vehicle_Indic_TwoWheeler: 
                    indic_pat = 'indic_twowheeler'
                    spawn_points = self.spawn_specific_vehicle(indic_pat, self._args.num_vehicles_Indic_TwoWheeler, tm, synchronous_master, spawn_points)
            if self._args.spawn_pedestrians:
                blueprintsWalkers = get_actor_blueprints(self.world, "walker.pedestrian.*", "All")
                walkers_list = []
                all_id = []
                number_of_walkers = self._args.num_walkers

                percentagePedestriansRunning = 0.0      # how many pedestrians will run
                percentagePedestriansCrossing = 20.0     # how many pedestrians will walk through the road
                if self._args.trafficManagerSeed:
                    self.world.set_pedestrians_seed(0)
                    random.seed(self._args.trafficManagerSeed)
                # 1. take all the random locations to spawn
                spawn_points = []
                for i in range(number_of_walkers):
                    spawn_point = carla.Transform()
                    loc = self.world.get_random_location_from_navigation()
                    if (loc != None):
                        spawn_point.location = loc
                        spawn_points.append(spawn_point)
                # 2. we spawn the walker object
                batch = []
                walker_speed = []
                for spawn_point in spawn_points:
                    walker_bp = random.choice(blueprintsWalkers)
                    # set as not invincible
                    if walker_bp.has_attribute('is_invincible'):
                        walker_bp.set_attribute('is_invincible', 'false')
                    # set the max speed
                    if walker_bp.has_attribute('speed'):
                        if (random.random() > percentagePedestriansRunning):
                            # walking
                            walker_speed.append(walker_bp.get_attribute('speed').recommended_values[1])
                        else:
                            # running
                            walker_speed.append(walker_bp.get_attribute('speed').recommended_values[2])
                    else:
                        print("Walker has no speed")
                        walker_speed.append(0.0)
                    batch.append(SpawnActor(walker_bp, spawn_point))
                results = self.client.apply_batch_sync(batch, True)
                walker_speed2 = []
                for i in range(len(results)):
                    if results[i].error:
                        print(results[i].error)
                    else:
                        walkers_list.append({"id": results[i].actor_id})
                        walker_speed2.append(walker_speed[i])
                walker_speed = walker_speed2
                # 3. we spawn the walker controller
                batch = []
                walker_controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
                for i in range(len(walkers_list)):
                    batch.append(SpawnActor(walker_controller_bp, carla.Transform(), walkers_list[i]["id"]))
                results = self.client.apply_batch_sync(batch, True)
                for i in range(len(results)):
                    if results[i].error:
                        print(results[i].error)
                    else:
                        walkers_list[i]["con"] = results[i].actor_id
                # 4. we put together the walkers and controllers id to get the objects from their id
                for i in range(len(walkers_list)):
                    all_id.append(walkers_list[i]["con"])
                    all_id.append(walkers_list[i]["id"])
                all_actors = self.world.get_actors(all_id)

                # wait for a tick to ensure client receives the last transform of the walkers we have just created
                if not synchronous_master:
                    self.world.wait_for_tick()
                else:
                    self.world.tick()

                # 5. initialize each controller and set target to walk to (list is [controler, actor, controller, actor ...])
                # set how many pedestrians can cross the road
                self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
                for i in range(0, len(all_id), 2):
                    # start walker
                    all_actors[i].start()
                    # set walk to random point
                    all_actors[i].go_to_location(self.world.get_random_location_from_navigation())
                    # max speed
                    all_actors[i].set_max_speed(float(walker_speed[int(i/2)]))

            actor_list = self.world.get_actors()
            for actor_ in actor_list.filter('vehicle.indic.auto01'):
                print(actor_)
                if isinstance(actor_, carla.Vehicle):
                    # if actor_.type == 'v:
                    # actor_.set_state(carla.TrafficLightState.Red) 
                    # actor_.set_red_time(1.0)
                    
                    # actor_.set_target_velocity(30*(actor_.get_transform().get_forward_vector()) )
                    # actor_.add_force(15*(actor_.get_transform().get_forward_vector()) )

                    actor_.set_target_velocity(20*(actor_.get_transform().get_forward_vector()) )


            if self._args.openscenario:
                scenario = OpenScenario(world=self.world,
                                        ego_vehicles=self.ego_vehicles,
                                        config=config,
                                        config_file=self._args.openscenario,
                                        timeout=100000)
            elif self._args.route:
                scenario = RouteScenario(world=self.world,
                                         config=config,
                                         debug_mode=self._args.debug)
            elif self._args.openscenario2:
                scenario = OSC2Scenario(world=self.world,
                                        ego_vehicles=self.ego_vehicles,
                                        config=config,
                                        osc2_file=self._args.openscenario2,
                                        timeout=100000)
            else:
                scenario_class = self._get_scenario_class_or_fail(config.type)
                scenario = scenario_class(self.world,
                                          self.ego_vehicles,
                                          config,
                                          self._args.randomize,
                                          self._args.debug)
        except Exception as exception:                  # pylint: disable=broad-except
            print("The scenario cannot be loaded")
            traceback.print_exc()
            print(exception)
            self._cleanup()
            return False

        ########### WEATHER ##############
        self.set_weather_preset(self._args.weather)
        
        ####################### SET TRAFFIC LIGHT ####################
        self.set_traffic_light_time()
        
        try:
            if self._args.record:
                recorder_name = "{}/{}/{}.mp4".format(
                    os.getenv('SCENARIO_RUNNER_ROOT', "./"), self._args.record, config.name)
                self.client.start_recorder(recorder_name, True)

            # Load scenario and run it
            self.manager.load_scenario(scenario, self.agent_instance)
            self.manager.run_scenario()

            # Provide outputs if required
            self._analyze_scenario(config)

            # Remove all actors, stop the recorder and save all criterias (if needed)
            scenario.remove_all_actors()
            if self._args.record:
                self.client.stop_recorder()
                self._record_criteria(self.manager.scenario.get_criteria(), recorder_name)

            result = True

        except Exception as e:              # pylint: disable=broad-except
            traceback.print_exc()
            print(e)
            result = False

        self._cleanup()
        return result

    def _run_scenarios(self):
        """
        Run conventional scenarios (e.g. implemented using the Python API of ScenarioRunner)
        """
        result = False

        # Load the scenario configurations provided in the config file
        scenario_configurations = ScenarioConfigurationParser.parse_scenario_configuration(
            self._args.scenario,
            self._args.configFile)
        if not scenario_configurations:
            print("Configuration for scenario {} cannot be found!".format(self._args.scenario))
            return result

        # Execute each configuration
        for config in scenario_configurations:
            for _ in range(self._args.repetitions):
                self.finished = False
                result = self._load_and_run_scenario(config)

            self._cleanup()
        return result

    def _run_route(self):
        """
        Run the route scenario
        """
        result = False

        if self._args.route:
            routes = self._args.route[0]
            scenario_file = self._args.route[1]
            single_route = None
            if len(self._args.route) > 2:
                single_route = self._args.route[2]

        # retrieve routes
        route_configurations = RouteParser.parse_routes_file(routes, scenario_file, single_route)
        for config in route_configurations:
            print(config)
            for _ in range(self._args.repetitions):
                result = self._load_and_run_scenario(config)

                self._cleanup()
        return result

    def _run_openscenario(self):
        """
        Run a scenario based on OpenSCENARIO
        """

        # Load the scenario configurations provided in the config file
        if not os.path.isfile(self._args.openscenario):
            print("File does not exist")
            self._cleanup()
            return False

        openscenario_params = {}
        if self._args.openscenarioparams is not None:
            for entry in self._args.openscenarioparams.split(','):
                [key, val] = [m.strip() for m in entry.split(':')]
                openscenario_params[key] = val
        config = OpenScenarioConfiguration(self._args.openscenario, self.client, openscenario_params)

        result = self._load_and_run_scenario(config)
        self._cleanup()
        return result

    def _run_osc2(self):
        """
        Run a scenario based on ASAM OpenSCENARIO 2.0.
        https://www.asam.net/static_downloads/public/asam-openscenario/2.0.0/welcome.html
        """
        # Load the scenario configurations provided in the config file
        if not os.path.isfile(self._args.openscenario2):
            print("File does not exist")
            self._cleanup()
            return False

        config = OSC2ScenarioConfiguration(self._args.openscenario2, self.client)

        result = self._load_and_run_scenario(config)
        self._cleanup()

        return result

    def run(self):
        """
        Run all scenarios according to provided commandline args
        """
                
        result = True
        if self._args.openscenario:
            result = self._run_openscenario()
        elif self._args.route:
            result = self._run_route()
        elif self._args.openscenario2:
            result = self._run_osc2()
        else:
            result = self._run_scenarios()

        print("No more scenarios .... Exiting")
        return result


def main():
    """
    main function
    """
    description = ("CARLA Scenario Runner: Setup, Run and Evaluate scenarios using CARLA\n"
                   "Current version: " + VERSION)

    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + VERSION)
    parser.add_argument('--host', default='127.0.0.1',
                        help='IP of the host server (default: localhost)')
    parser.add_argument('--port', default='2000',
                        help='TCP port to listen to (default: 2000)')
    parser.add_argument('--timeout', default="10.0",
                        help='Set the CARLA client timeout value in seconds')
    parser.add_argument('--trafficManagerPort', default='8000',
                        help='Port to use for the TrafficManager (default: 8000)')
    parser.add_argument('--trafficManagerSeed', default='0',
                        help='Seed used by the TrafficManager (default: 0)')
    parser.add_argument('--sync', action='store_true',
                        help='Forces the simulation to run synchronously')
    parser.add_argument('--list', action="store_true", help='List all supported scenarios and exit')

    parser.add_argument(
        '--scenario', help='Name of the scenario to be executed. Use the preposition \'group:\' to run all scenarios of one class, e.g. ControlLoss or FollowLeadingVehicle')
    parser.add_argument('--openscenario', help='Provide an OpenSCENARIO definition')
    parser.add_argument('--openscenarioparams', help='Overwrited for OpenSCENARIO ParameterDeclaration')
    parser.add_argument('--openscenario2', help='Provide an openscenario2 definition')
    parser.add_argument(
        '--route', help='Run a route as a scenario (input: (route_file,scenario_file,[route id]))', nargs='+', type=str)

    parser.add_argument(
        '--agent', help="Agent used to execute the scenario. Currently only compatible with route-based scenarios.")
    parser.add_argument('--agentConfig', type=str, help="Path to Agent's configuration file", default="")

    parser.add_argument('--output', action="store_true", help='Provide results on stdout')
    parser.add_argument('--file', action="store_true", help='Write results into a txt file')
    parser.add_argument('--junit', action="store_true", help='Write results into a junit file')
    parser.add_argument('--json', action="store_true", help='Write results into a JSON file')
    parser.add_argument('--outputDir', default='feedback', help='Directory for output files (default: this directory)')

    parser.add_argument('--configFile', default='', help='Provide an additional scenario configuration file (*.xml)')
    parser.add_argument('--additionalScenario', default='', help='Provide additional scenario implementations (*.py)')

    parser.add_argument('--debug', action="store_true", help='Run with debug output')
    parser.add_argument('--reloadWorld', action="store_true",
                        help='Reload the CARLA world before starting a scenario (default=True)')
    parser.add_argument('--record', type=str, default='',
                        help='Path were the files will be saved, relative to SCENARIO_RUNNER_ROOT.\nActivates the CARLA recording feature and saves to file all the criteria information.')
    parser.add_argument('--randomize', action="store_true", help='Scenario parameters are randomized')
    parser.add_argument('--repetitions', default=1, type=int, help='Number of scenario executions')
    parser.add_argument('--waitForEgo', action="store_true", help='Connect the scenario to an existing ego vehicle')
    parser.add_argument('--spawn_vehicle', action="store_true", help='Spawn extra vehicles')
    parser.add_argument('--spawn_pedestrians', action="store_true", help='Spawn extra pedestrians')


    parser.add_argument('--num_walkers', metavar='W',
        default=50,
        type=int,
        help='Number of walkers (default: 5)')
    # parser.add_argument('--num_vehicles', metavar='W',
    #     default=15,
    #     type=int,
    #     help='Number of vehicles (default: 5)')
    parser.add_argument('--spawn_vehicle_Indic_TwoWheeler', action="store_true", help='Spawn Two-Wheelers')
    parser.add_argument('--num_vehicles_Indic_TwoWheeler', metavar='W',
        default=15,
        type=int,
        help='Number of Two-Wheelers (default: 15)')

    parser.add_argument('--spawn_vehicle_Indic_HeavyVehicle', action="store_true", help='Spawn Bus')
    parser.add_argument('--num_vehicles_Indic_HeavyVehicle', metavar='W',
        default=2,
        type=int,
        help='Number of Buses (default: 2)')

    parser.add_argument('--spawn_vehicle_Indic_ThreeWheeler', action="store_true", help='Spawn Auto')
    parser.add_argument('--num_vehicles_Indic_ThreeWheeler', metavar='W',
        default=5,
        type=int,
        help='Number of Autos (default: 15)')

    parser.add_argument('--spawn_vehicle_Indic_FourWheeler', action="store_true", help='Spawn Nano')
    parser.add_argument('--num_vehicles_Indic_FourWheeler', metavar='W',
        default=5,
        type=int,
        help='Number of Nanos (default: 5)')



    parser.add_argument('--weather', default='Wet Cloudy Sunset',
                        help='Choose a weather preset setting', choices=['Clear Night', 'Clear Noon', 'Clear Sunset', 'Cloudy Night', 'Cloudy Noon', 'Cloudy Sunset', 'Default', 
                        'Hard Rain Night', 'Hard Rain Noon', 'Hard Rain Sunset', 'Mid Rain Sunset', 'Mid Rainy Night', 'Mid Rainy Noon', 
                        'Soft Rain Night', 'Soft Rain Noon', 'Soft Rain Sunset', 'Wet Cloudy Night', 'Wet Cloudy Noon', 'Wet Cloudy Sunset', 'Wet Night', 'Wet Noon', 'Wet Sunset'])
    arguments = parser.parse_args()
    # pylint: enable=line-too-long

    OSC2Helper.wait_for_ego = arguments.waitForEgo

    if arguments.list:
        print("Currently the following scenarios are supported:")
        print(*ScenarioConfigurationParser.get_list_of_scenarios(arguments.configFile), sep='\n')
        return 1

    if not arguments.scenario and not arguments.openscenario and not arguments.route and not arguments.openscenario2:
        print("Please specify either a scenario or use the route mode\n\n")
        parser.print_help(sys.stdout)
        return 1

    if arguments.route and (arguments.openscenario or arguments.scenario):
        print("The route mode cannot be used together with a scenario (incl. OpenSCENARIO)'\n\n")
        parser.print_help(sys.stdout)
        return 1

    if arguments.agent and (arguments.openscenario or arguments.scenario):
        print("Agents are currently only compatible with route scenarios'\n\n")
        parser.print_help(sys.stdout)
        return 1

    if arguments.openscenarioparams and not arguments.openscenario:
        print("WARN: Ignoring --openscenarioparams when --openscenario is not specified")

    if arguments.route:
        arguments.reloadWorld = True

    if arguments.agent:
        arguments.sync = True

    scenario_runner = None
    result = True
    try:
        scenario_runner = ScenarioRunner(arguments)
        result = scenario_runner.run()
    except Exception:   # pylint: disable=broad-except
        traceback.print_exc()

    finally:
        if scenario_runner is not None:
            scenario_runner.destroy()
            del scenario_runner
    return not result


if __name__ == "__main__":
    sys.exit(main())
