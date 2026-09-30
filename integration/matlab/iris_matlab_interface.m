% =========================================================================
% IRIS MATLAB Automated Driving Toolbox Interface Blueprint (Phase 16)
% Reads serialized IRIS Python JSON telemetry, imports actors into Automated
% Driving Toolbox actor pose array, and executes MATLAB vehicle control.
% =========================================================================

classdef iris_matlab_interface < handle
    properties
        IPCFilePath = 'iris_matlab_ipc.json'
        EgoState
        ActorPoses
        RoadWidth = 10.0
    end
    
    methods
        function obj = iris_matlab_interface(ipc_file)
            if nargin > 0
                obj.IPCFilePath = ipc_file;
            end
        end
        
        function stateData = read_python_state(obj)
            % Reads serialized JSON state from Python IRIS engine
            if ~exist(obj.IPCFilePath, 'file')
                error('IPC file %s does not exist.', obj.IPCFilePath);
            end
            fid = fopen(obj.IPCFilePath, 'r');
            rawText = fread(fid, '*char')';
            fclose(fid);
            stateData = jsondecode(rawText);
            obj.EgoState = stateData.ego_vehicle;
        end
        
        function actorPoses = convert_to_automated_driving_toolbox(obj, stateData)
            % Convert IRIS actors to Automated Driving Toolbox actor pose struct array
            numActors = length(stateData.traffic_actors);
            actorPoses = struct('ActorID', cell(1, numActors), ...
                                'Position', cell(1, numActors), ...
                                'Velocity', cell(1, numActors), ...
                                'Yaw', cell(1, numActors));
            for i = 1:numActors
                act = stateData.traffic_actors(i);
                actorPoses(i).ActorID = act.actor_id;
                actorPoses(i).Position = [act.position(1), act.position(2), 0.0];
                actorPoses(i).Velocity = [act.velocity(1), act.velocity(2), 0.0];
                actorPoses(i).Yaw = rad2deg(act.heading_rad);
            end
            obj.ActorPoses = actorPoses;
        end
        
        function controlResp = compute_matlab_control(obj, stateData)
            % Sample MATLAB control calculation (Target Speed & Pure Pursuit)
            ego = stateData.ego_vehicle;
            
            % Scale target speed according to decision state
            switch ego.decision_state
                case 'STOP'
                    targetSpeedKmh = 0.0;
                case 'SLOW_DOWN'
                    targetSpeedKmh = 12.0;
                case 'CAUTION'
                    targetSpeedKmh = 18.0;
                otherwise
                    targetSpeedKmh = 25.0;
            end
            
            controlResp = struct();
            controlResp.steering_angle_deg = ego.steering_angle_deg;
            controlResp.target_speed_kmh = targetSpeedKmh;
            controlResp.throttle = 0.4;
            controlResp.brake = 0.0;
        end
        
        function write_matlab_response(obj, controlResp)
            % Write control response back to Python IPC
            jsonTxt = jsonencode(controlResp);
            fid = fopen(obj.IPCFilePath, 'w');
            fwrite(fid, jsonTxt, 'char');
            fclose(fid);
        end
    end
end
