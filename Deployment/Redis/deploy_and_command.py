import os
import json
import re
import subprocess
import time

def extract_command(content: str):
    """Extract commands, ensuring each starts with redis-cli and handle multi-line commands."""    
    content = content.replace('```', '')
    sub_commands = re.split(r'\s*;\s*|\s*\n\s*', content.strip())
    redis_commands = []

    for sub_command in sub_commands:
        stripped_command = sub_command.strip()
        if stripped_command:
            if stripped_command.startswith('./redis-cli'):
                stripped_command = stripped_command.replace('./redis-cli', '', 1)
            if stripped_command.startswith('redis-cli'):
                stripped_command = stripped_command.replace('redis-cli', '', 1)
            elif stripped_command.startswith('src/redis-cli'):
                stripped_command = stripped_command.replace('src/redis-cli', '', 1)
            elif not stripped_command.startswith('redis'):
                stripped_command = f"{stripped_command}"
            redis_commands.append(stripped_command)

    return redis_commands

def get_commands_from_file(file_path: str):
    """Extract commands from a single file, logging if 'no' is found and returning an empty list."""    
    with open(file_path, 'r') as f:
        data = json.load(f)
        if data and len(data[-1]) > 0:
            content = data[-1]['content']
            #if re.search(r'\bno\b', content, re.IGNORECASE) or "not" in content:
            if "no" in content or 'No' in content:
                return []  # Return an empty list if 'no' is found
            return extract_command(content)
    return []

def run_redis_container(probe: str, version: str, commands_list: list, subdir: str):
    """Start a Redis Docker container for the specified version and execute commands, saving output to file."""
    docker_run_command = f"docker run --name redis-{version} -d -p 6379:6379 redis:{version} --requirepass mypassword"
    try:
        subprocess.run(docker_run_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run Docker command: {docker_run_command}. Error: {e}")
        return

    output_file = os.path.join(f'./{probe}', f'{subdir}', f'{version}')
    if os.path.exists(output_file):  
        print(f"Output directory already exists for {output_file}, skipping...")  
        return  
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    print(probe,subdir,version)
    with open(output_file, 'w') as f_output:
        for command in commands_list:
            full_command = f"redis-cli -h 127.0.0.1 -p 6379 {command}"
            print(f"Executing command: {full_command}")

            # Initialize retry parameters
            retries = 3
            for attempt in range(retries):
                try:
                    result = subprocess.run(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
                    
                    # Log error only if not "Connection reset by peer"
                    if "Connection reset by peer" not in result.stderr:
                        f_output.write(f"Command: {full_command}\n")
                        f_output.write(f"Output:\n{result.stdout}\n")
                        f_output.write(f"Error:\n{result.stderr}\n\n")
                        break
                except subprocess.TimeoutExpired:
                    f_output.write(f"Command: {full_command}\n")
                    f_output.write("Error: Command timed out\n\n")
                    continue
                except Exception as e:
                    # Log other errors
                    f_output.write(f"Command: {full_command}\n")
                    f_output.write(f"Error: {str(e)}\n\n")
                    break
                
                # Check for specific error message and retry if needed
                if "Connection reset by peer" in result.stderr:
                    print(f"Attempt {attempt + 1} failed due to 'Connection reset by peer'. Retrying...")
                    time.sleep(1)  # Wait before retrying
                    if attempt == retries - 1:
                        f_output.write(f"Command: {full_command}\n")
                        f_output.write("Error: Connection reset by peer after multiple attempts\n\n")




def stop_and_remove_redis_container(version: str):
    """Stop and remove Redis Docker container."""
    stop_container_command = f"docker stop redis-{version}"
    rm_container_command = f"docker rm redis-{version}"

    print(f"Stopping container: redis-{version}")
    try:
        subprocess.run(stop_container_command, shell=True, check=True)
        print(f"Removing container: redis-{version}")
        subprocess.run(rm_container_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return

def deploy_versions(probe,versions):
    """Iterate over version list, deploy each version's Redis container, and log skipped subdirectories missing get_interact_command.json."""
    base_fp = ''
    probe_path = os.path.join(base_fp, probe)
    if not os.path.exists(probe_path):
        print(f"Directory does not exist: {probe_path}")
    
    for subdir in os.listdir(probe_path):
        subdir_path = os.path.join(probe_path, subdir)
        if not os.path.isdir(subdir_path):
            continue

        json_files = [file for file in os.listdir(subdir_path) if file.endswith('get_interact_command.json')]
        if not json_files:
            print(f"Skipping {subdir_path} - No get_interact_command.json found")
            continue

        output_file_path = os.path.join(f'{probe}', subdir)
        if os.path.exists(output_file_path):  
            print(f"Output directory already exists for {probe}/{subdir}, skipping...")  
            continue  

        for file in json_files:
            file_path = os.path.join(subdir_path, file)           
            commands = get_commands_from_file(file_path)
            for version in versions:
                print(f"Deploying Redis version: {version}")
                if commands:
                    run_redis_container(probe, version, commands, subdir)
                    stop_and_remove_redis_container(version)

# Example invocation
if __name__ == "__main__":
    probe = ''
    versions = ''
    with open(versions, 'r') as file:
        versions = file.read().splitlines()
    deploy_versions(probe,versions)
