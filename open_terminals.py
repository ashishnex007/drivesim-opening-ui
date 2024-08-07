import subprocess

def open_terminals(level, scene, town):
    scene_map = {
        "Scene 1": "1",
        "Scene 2": "2",
        "Scene 3": "3"
    }
    town_map = {
        "Town 02": 0,
        "Town 03": 1,
        "Town 04": 2,
        "Town 05": 3,
        "Town 06": 4
    }
    print(scene)
    print(town)
    print(level)

    # Validate scene and town
    # scene_id = scene_map.get(scene)
    # town_id = town_map.get(town)

    scene_id = scene
    town_id = town

    print(scene_id)
    if scene_id is None:
        raise ValueError("Unknown scene")
    if town_id is None:
        raise ValueError("Unknown town")

    level = level.lower()

    # Default parameters
    weather_param = '\'Wet Cloudy Noon\''
    display_caution_param = '--display_caution'

    # Initialize other_params
    other_params = ''

    if level == 'easy':
        repetitions = 1
        other_params = f'--repetitions {repetitions}'
    elif level == 'intermediate':
        if scene_id == '1':
            num_walkers = 15
            num_vehicles_Indic_TwoWheeler = 10
            other_params = f'--spawn_pedestrian --num_walkers {num_walkers} --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler}'
        elif scene_id == '2':
            num_walkers = 15
            num_vehicles_Indic_TwoWheeler = 5
            num_vehicles_Indic_ThreeWheeler = 5
            other_params = f'--spawn_pedestrian --num_walkers {num_walkers} --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler} --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler {num_vehicles_Indic_ThreeWheeler}'
        elif scene_id == '3':
            num_walkers = 15
            num_vehicles_Indic_TwoWheeler = 5
            num_vehicles_Indic_ThreeWheeler = 5
            other_params = f'--spawn_pedestrian --num_walkers {num_walkers} --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler} --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler {num_vehicles_Indic_ThreeWheeler}'
    elif level == 'hard':
        if scene_id == '1':
            num_walkers = 150
            num_vehicles_Indic_TwoWheeler = 15
            num_vehicles_Indic_HeavyVehicle = 10
            num_vehicles_Indic_ThreeWheeler = 10
            other_params = f'--spawn_pedestrian --num_walkers {num_walkers} --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler} --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle {num_vehicles_Indic_HeavyVehicle} --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler {num_vehicles_Indic_ThreeWheeler}'
        elif scene_id == '2':
            num_vehicles_Indic_TwoWheeler = 10
            num_vehicles_Indic_HeavyVehicle = 10
            num_vehicles_Indic_ThreeWheeler = 10
            num_vehicles_Indic_FourWheeler = 5
            other_params = f'--spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler} --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle {num_vehicles_Indic_HeavyVehicle} --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler {num_vehicles_Indic_ThreeWheeler} --spawn_vehicle_Indic_FourWheeler --num_vehicles_Indic_FourWheeler {num_vehicles_Indic_FourWheeler}'
        elif scene_id == '3':
            num_vehicles_Indic_TwoWheeler = 10
            num_vehicles_Indic_HeavyVehicle = 10
            num_vehicles_Indic_ThreeWheeler = 10
            num_vehicles_Indic_FourWheeler = 5
            other_params = f'--spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler {num_vehicles_Indic_TwoWheeler} --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle {num_vehicles_Indic_HeavyVehicle} --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler {num_vehicles_Indic_ThreeWheeler} --spawn_vehicle_Indic_FourWheeler --num_vehicles_Indic_FourWheeler {num_vehicles_Indic_FourWheeler}'

    # Construct the command
    # command = (f"python3 scenario_runner.py --route srunner/data/final_routes_loop.xml srunner/data/final_all_towns_traffic_scenarios_loop_{level}{scene_id}.json {town_id} --agent srunner/autoagents/human_agent.py --output --weather {weather_param} {other_params}")
    command = (f"python3 scenario_runner.py --route srunner/data/final_routes_loop.xml srunner/data/final_all_towns_traffic_scenarios_loop_{level}{scene_id}.json {town_id} --agent srunner/autoagents/steering_agent.py --output --weather {weather_param} {other_params}")
    # command = (f"python3 scenario_runner.py --route srunner/data/final_routes_loop.xml srunner/data/final_all_towns_traffic_scenarios_loop_{level}{scene_id}.json {town_id} --output --weather {weather_param} {other_params}")


    print(command)

    # Open terminals
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{command}; exec bash'])
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'python3 manual_control_steeringwheel_trials_copy.py {display_caution_param}; exec bash'])

