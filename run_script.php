<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Read input data
    $input = json_decode(file_get_contents('php://input'), true);
    $level = $input['level'];
    $scene = $input['scene'];
    $town = $input['town'];

    // Construct the command
    $scene_map = [
        "Scene 1" => "1",
        "Scene 2" => "2"
    ];
    $town_map = [
        "Town 02" => 0,
        "Town 03" => 1,
        "Town 04" => 2,
        "Town 05" => 3,
        "Town 06" => 4
    ];

    $scene_id = $scene_map[$scene];
    $town_id = $town_map[$town];
    $level = strtolower($level);
    
    if ($level == 'easy') {
        $other_params = '--repetitions 1';
    } elseif ($level == 'intermediate' && $scene_id == "1") {
        $other_params = '--spawn_pedestrian --num_walkers 15 --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 10';
    } elseif ($level == 'intermediate' && $scene_id == "2") {
        $other_params = '--spawn_pedestrian --num_walkers 20 --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 15 --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler 5';
    } elseif ($level == 'intermediate' && $scene_id == "3") {
        $other_params = '--spawn_pedestrian --num_walkers 25 --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 25 --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler 10';
    } elseif ($level == 'hard' && $scene_id == "1") {
        $other_params = '--spawn_pedestrian --num_walkers 150 --spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 15 --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle 15 --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler 15';
    } elseif ($level == 'hard' && $scene_id == "2") {
        $other_params = '--spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 25 --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle 10 --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler 15 --spawn_vehicle_Indic_FourWheeler --num_vehicles_Indic_FourWheeler 5';
    } elseif ($level == 'hard' && $scene_id == "3") {
        $other_params = '--spawn_vehicle --spawn_vehicle_Indic_TwoWheeler --num_vehicles_Indic_TwoWheeler 100 --spawn_vehicle_Indic_HeavyVehicle --num_vehicles_Indic_HeavyVehicle 20 --spawn_vehicle_Indic_ThreeWheeler --num_vehicles_Indic_ThreeWheeler 1000 --spawn_vehicle_Indic_FourWheeler --num_vehicles_Indic_FourWheeler 15';
    } else {
        $other_params = '';
    }

    // Change to the directory where the script should be run
    // chdir('/path/to/your/directory');

    // Construct the command
    $command = 'gnome-terminal -- bash -c "python3 scenario_runner.py --route srunner/data/final_routes_loop.xml srunner/data/final_all_towns_traffic_scenarios_loop_'.$level.$scene_id.'.json  '.$town_id.' --agent srunner/autoagents/human_agent.py --output --weather \'Wet Cloudy Noon\' '.$other_params.'; exec bash"';

    // Execute the command
    shell_exec($command);

    // Output a message to indicate the script was executed
    echo "Python script is running in a new terminal.";
}
?>
