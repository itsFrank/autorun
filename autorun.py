'''                                                                                                                                                    
    File: autorun.py                                                                                                                              
    Author: Francis O'Brien                                                                                                                           
    Email: francis.obrien@mail.utoronto.ca                                                                                                            
    Create Date: 05-02-2018                                                                                                                             
    -----------------------------------------                                                                                                         
    Description                                                                                                                                              
        A flexible, configurable, autorun script that runs external programs and extracts specific output values using regular expressions
    -----------------------------------------
    Usage
        $ python autorun.py <out_csv> [options]
        
        <out_csv>: the name of the output csv file to be created / appended to (if it already exists, existing data will remain, but new data will be appended to the file)

        options:
            -t <sec>: Timeout; will pre-pend the command with 'timeout <sec>' which will stop the program under test after <sec> seconds and restart it
            -s <offset>: Start Offset; will start at permutation <offset> instead of 0. Useful when autorun doesn't have time to finish, and you want to start where it left off
            -j <alt_json>: Alt JSON; will use the file names <alt_json> instead of the default 'autorun.json' to configure the script
            -r <reps>: Repetitions; will repeat each permutation <reps> times, averaging any extracted value of type 'numerical'. Other extract types will use the value of the last run
            --test: Test config; This will make the script output every command but not execute it. Useful to test a new autorun.json to make sure it is configure properly
            --testf: Same as '--test' but this will also output a sample of the CSV line results, replacing any extract value by the name of the extract
    -----------------------------------------                                                                                                         
    History                                                                                                                                           
        05-02-2018 :    created  
        05-05-2018 :    added timeout & start offset arguments                                                                                                                           
        06-19-2018 :    changed configuration to use external JSON file instead of internal dictionaries
                        changed all parameters except output csv to options instead of positional arguments
                        added repetition option and testing functionality    
'''                                                                                                                                                   
                                                                                                                                                      
import re
import sys
import commands
import json

if len(sys.argv) < 2:
    print("Usage: python autorun.py <output filename>.csv [options]")
    sys.exit(0)

filename = sys.argv[1]

start_perm = -1
timeout = -1
repetitions = 1

json_file = "autorun.json"

test = False
test_full = False

#Add restart on timeout functionality (exit code = 124)

for i in range(0, len(sys.argv)):
    if (sys.argv[i] == "-t"):
        timeout = int(sys.argv[i+1])
        i += 1
    elif (sys.argv[i] == "-s"):
        start_perm = int(sys.argv[i+1])
        i += 1
    elif (sys.argv[i] == "-j"):
        alt_json = sys.argv[i+1]
        i += 1
    elif (sys.argv[i] == "-r"):
        repetitions = int(sys.argv[i+1])
        i += 1
    elif (sys.argv[i] == "--test"):
        test = True
    elif (sys.argv[i] == "--testf"):
        test = True
        test_full = True

json_data = {}

with open(json_file) as f:
    json_data = json.load(f)

def appendFileLine(filename, string):
    with open(filename, "a") as myfile:
        myfile.write(string)
        if (not string.endswith("\n")):
            myfile.write("\n")

def initValues(parameters):
    values = {}
    for i in range(0, len(parameters)):
        param = parameters[i]

        if (param["type"] == "scaling"):
            values[param["name"]] = param["min"]
        elif (param["type"] == "list"):
            values[param["name"]] = param["list"][0]
        elif (param["type"] == "static"):
            values[param["name"]] = param["value"]
        else:
            print('\033[91m' + "Parameter <" + param["name"] + "> has unrecognized type: " + param["type"])
            sys.exit(-1)

    return values

def incrementStepType(param, value):
    if (param["step_type"] == "add"):
        return value + param["step"]
    elif (param["step_type"] == "mult"):
        return value * param["step"]

def incrementValues(parameters, values):
    current_idx = len(parameters) - 1
    current_param = parameters[current_idx]

    while (current_idx >= 0):
        if (current_param["type"] == "scaling"):
            if (values[current_param["name"]] < current_param["max"]):
                values[current_param["name"]] = incrementStepType(current_param, values[current_param["name"]])
                return True
            else:
                values[current_param["name"]] = current_param["min"]

        elif (current_param["type"] == "list"):
            value_idx = -1
            for i in range(0, len(current_param["list"])):
                if (values[current_param["name"]] == current_param["list"][i]):
                    if (i < len(current_param["list"]) - 1):
                        values[current_param["name"]] = current_param["list"][i+1]
                        return True
                    else:
                        values[current_param["name"]] = current_param["list"][0]

        # elif (current_param["type"] == "static"):
            #do nothing

        current_idx -= 1
        current_param = parameters[current_idx]

    return False

def genCommandString(command, parameters, values):
    cstr = command

    for i in range(0, len(parameters)):
        cstr += " " + str(values[parameters[i]["name"]])
    
    return cstr

def regexSearch(buffer, regex):
    m = re.search(regex, buffer)
    if m:
        return m.group(1)
    else:
        return None

def genCSVHeader(parameters, extract):
    hstr = parameters[0]["name"]

    for i in range(1, len(parameters)):
        if (not ("output" in parameters[i]) or parameters[i]["output"]):
            hstr += ", " + parameters[i]["name"]
    
    for i in range(0, len(extract)):
        hstr += ", " + str(extract[i]["name"])

    return hstr

def genVarCSVLine(parameters, values):
    vstr = str(values[parameters[0]["name"]])
    for i in range(1, len(parameters)):
        vstr += ", " + str(values[parameters[i]["name"]])
    
    return vstr

def permCount(parameters):
    values = initValues(parameters)

    count = 0

    condition = True
    while condition:
        count += 1
        condition = incrementValues(parameters, values)
    
    return count


if (not test):
    values = initValues(json_data["parameters"])
    condition = True
    appendFileLine(filename, genCSVHeader(json_data["parameters"], json_data["extract"]))
    total_permutations = permCount(json_data["parameters"])
    run_count = 1


    if (start_perm != -1):
        while run_count < start_perm:
            condition = incrementValues(parameters, values, order)
            run_count += 1

    while condition:
        
        command = genCommandString(json_data["command"], json_data["parameters"], values)

        if (timeout != -1):
            command = "timeout " + str(timeout) + " " + command
        print("[" + str(run_count) + "/" + str(total_permutations) + "]:   " + command)
        run_count += 1
        
        csv_line = genVarCSVLine(json_data["parameters"], values)


        extract_values = []
        for e in range(0, len(json_data["extract"])):
            extract_values.append({"value": 0})

        if (repetitions > 1):
            sys.stdout.write("\tComputing repetitions ")
            sys.stdout.flush()

        for r in range(0, repetitions):
            if (repetitions > 1):
                sys.stdout.write(".")
                sys.stdout.flush()

            out = commands.getstatusoutput(command)[1]

            for i in range(0, len(json_data["extract"])):
                found = regexSearch(out, json_data["extract"][i]["regex"])
                if (found == None):
                    extract_values[i]["value"] = "NOT FOUND"
                elif (not json_data["extract"][i]["type"] == "numerical"):
                    extract_values[i]["value"] = found
                else:
                    if (type(extract_values[i]["value"]) == type(1)):
                        extract_values[i]["value"] += int(found)
        
        if (repetitions > 1):
            sys.stdout.write("\n")
            sys.stdout.flush()

        for i in range(0, len(json_data["extract"])):
            if (type(extract_values[i]["value"]) == type(1)):
                csv_line += ", " + str(extract_values[i]["value"] / repetitions)
            else:
                csv_line += ", " + extract_values[i]["value"]

        appendFileLine(filename, csv_line)

        condition = incrementValues(json_data["parameters"], values)

else:
    values = initValues(json_data["parameters"])
    condition = True
    total_permutations = permCount(json_data["parameters"])
    run_count = 1

    if (test_full):
        print("HEADER:\t" + genCSVHeader(json_data["parameters"], json_data["extract"]))

    if (start_perm != -1):
        while run_count < start_perm:
            condition = incrementValues(parameters, values, order)
            run_count += 1

    while condition:
        
        command = genCommandString(json_data["command"], json_data["parameters"], values)

        if (timeout != -1):
            command = "timeout " + str(timeout) + " " + command
        print("[" + str(run_count) + "/" + str(total_permutations) + "]:   " + command)
        run_count += 1
        
        csv_line = genVarCSVLine(json_data["parameters"], values)

        for i in range(0, len(json_data["extract"])):
            csv_line += ", <" + json_data["extract"][i]["name"] + ">"
                
        if (test_full):
            print("\t" + csv_line)

        condition = incrementValues(json_data["parameters"], values)
