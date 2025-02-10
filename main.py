import json
import sys
import argparse

def parse_task_arguments(task_arguments, entity_type):
    entities = []
    tasks = task_arguments.split(" create|")

    for task in tasks:
        if task.strip():
            details = task.split("|")
            if entity_type == "user":
                if len(details) >= 4:
                    entities.append({
                        "username": details[0],
                        "fullname": details[1],
                        "password": details[2],
                        "groups": details[3].split(",")
                    })
            elif entity_type == "group":
                if len(details) >= 2:
                    entities.append({
                        "groupname": details[0],
                        "description": details[1]
                    })

    return entities

def process_json(json_file, entity_type):
    try:
        with open(json_file, "r") as file:
            data = json.load(file)

        list_of_nodes = data.get("listOfNodes", [])

        for node in list_of_nodes:
            task_arguments = node.get("taskArguments", "")
            entities = parse_task_arguments(task_arguments, entity_type)

            output_file = f"C:\\Scripts\\{entity_type}s.json"
            with open(output_file, "w") as out_file:
                json.dump({f"{entity_type}s": entities}, out_file, indent=4)

        print(f"Processed {entity_type}s successfully.")
        sys.exit(0)

    except Exception as e:
        print(f"Error processing JSON: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonFile", required=True, help="Path to JSON file")
    parser.add_argument("--entityType", required=True, choices=["user", "group"], help="Specify 'user' or 'group'")
    
    args = parser.parse_args()
    process_json(args.jsonFile, args.entityType)