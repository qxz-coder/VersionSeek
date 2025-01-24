import os
import subprocess
import time
import json
import re
import os

outf = ""
total = 0
failed_docker_versions = []  # To keep track of Docker versions that failed to deploy


def extract_command(content: str):
    """Extract commands that start with curl, ensuring each starts with http://localhost:8081 before /api and handle multi-line commands."""
    content = content.replace('```', '') 
    sub_commands = re.split(r'(?<=\n)\s*curl', content.strip())  
    joomla_commands = []

    for sub_command in sub_commands:
        sub_command = sub_command.strip() 
        if not sub_command.startswith('curl'):
            continue 
        
        stripped_command = sub_command  
        
        match = re.search(r'(https?://\S+)', stripped_command)
        
        if not match:
            if '/api' in stripped_command:
                stripped_command = stripped_command.replace('/api', 'http://localhost:8081/api')
        else:
            stripped_command = stripped_command.replace('https://example.com', 'http://localhost:8081')
            stripped_command = stripped_command.replace('https://example.org', 'http://localhost:8081')
            stripped_command = stripped_command.replace('https://example.tl', 'http://localhost:8081')
    
        if '-d' in stripped_command:
            start_index = stripped_command.find('-d') + 2
            json_data = stripped_command[start_index:].strip() 
            
            json_data = json_data.replace('\n', ' ').replace('\r', '').replace('  ', ' ').strip()
            
            if not json_data.strip().startswith("'") and not json_data.strip().startswith('"') :
                    json_data = f"'{json_data}'"
            
            stripped_command = stripped_command[:start_index] + ' ' + json_data
        
        joomla_commands.append(stripped_command)

    return joomla_commands



def get_commands_from_file(file_path: str):
    """Extract commands from a single file, logging if 'no' is found and returning an empty list."""    
    with open(file_path, 'r') as f:
        data = json.load(f)
        if data and len(data[-1]) > 0:
            content = data[-1]['content']
            if re.search(r'\bno\b', content, re.IGNORECASE) or "not" in content:
            #if "no" in content or 'No' in content:
                return []  # Return an empty list if 'no' is found
            return extract_command(content)
    return []

def run_joomla_container(docker_version: str, version: str, commands_list: list, subdir: str):
    """Run Joomla Docker container, execute commands, and log outputs."""    
    output_file = os.path.join(f'{outf}/{version}', f'{subdir}', f'{docker_version}')
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Run the commands for this version
    with open(output_file, 'w') as f_output:
        for command in commands_list:
            full_command = command
            #print(full_command)

            try:
                result = subprocess.run(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
                f_output.write(f"Command: {full_command}\n")
                f_output.write(f"Output:\n{result.stdout}\n")
                f_output.write(f"Error:\n{result.stderr}\n\n")
            except subprocess.TimeoutExpired:
                f_output.write(f"Command: {full_command}\n")
                f_output.write("Error: Command timed out\n\n")
                continue
            except Exception as e:
                # Log other errors
                f_output.write(f"Command: {full_command}\n")
                f_output.write(f"Error: {str(e)}\n\n")
                break


def deploy_versions(version_list, docker_versions):
    """Iterate over version list, deploy each version's Joomla container, and log skipped subdirectories missing get_interact_command.json."""    
    base_fp = ''
    container_name = f"some-joomla"
    network_name = "joomla_network"
            

    for docker_version in docker_versions:
        network_name = f"joomla_network"

        # Check if docker_version is < 3.8.0 or > 3.9.28
        version_parts = docker_version.split(".")
        major, minor, patch = int(version_parts[0]), int(version_parts[1]), int(version_parts[2])

        if major < 3 or (major == 3 and (minor < 8 or (minor == 8 and patch == 0))) or major > 3 or (major == 3 and (minor > 9 or (minor == 9 and patch > 28))):
            # Use Docker Compose for versions < 3.8.0 or > 3.9.28
            print(f"Deploying Joomla version {docker_version} using Docker Compose...")

            compose_file = f"Dockerfiles/{docker_version}/docker-compose.yml"
            
            try:
                subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d"], check=True)
            except subprocess.CalledProcessError as e:
                error_message = f"Failed to deploy Joomla version {docker_version}: {e}\n"
                print(error_message)
                subprocess.run(["docker", "compose", "-f", compose_file, "down"], check=True)
                failed_docker_versions.append(docker_version)
                continue  # Skip this version and continue with the next one

        else:
            # Use `docker run` for versions between 3.8.0 and 3.9.28
            run_command = [
                "docker", "run", "--name", container_name,
                "--network", network_name,
                "-e", "JOOMLA_ADMIN_EMAIL=joomla@example.com",
                "-e", "JOOMLA_ADMIN_PASSWORD=joomla@secured",
                "-e", "JOOMLA_ADMIN_USER=Joomla Hero",
                "-e", "JOOMLA_ADMIN_USERNAME=joomla",
                "-e", "JOOMLA_DB_HOST=some-mysql",
                "-e", "JOOMLA_DB_NAME=joomla_db",
                "-e", "JOOMLA_DB_PASSWORD=a",
                "-e", "JOOMLA_DB_USER=joomla",
                "-e", "JOOMLA_SITE_NAME=Joomla",
                "-e", "JOOMLA_DB_TYPE=mysqli",
                "-e", "JOOMLA_EXTENSIONS_URLS=https://example.com/extensions1;https://example.com/extensions2",
                "-e", "JOOMLA_EXTENSIONS_PATHS=/path/to/extension1.zip;/path/to/extension2.zip",
                "-e", "JOOMLA_SMTP_HOST=smtp.example.com",
                "-e", "JOOMLA_SMTP_HOST_PORT=587",
                "-p", "8081:80",  # Expose port 8081 on the host to 80 on the container
                "-v", "joomla_data:/var/www/html1",
                "-d", f"joomla:{docker_version}"
            ]
            
            try:
                print(f"Deploying Joomla version {docker_version} using Docker Run...")
                subprocess.run(run_command, check=True)
            except subprocess.CalledProcessError as e:
                error_message = f"Failed to deploy Joomla version {docker_version}: {e}\n"
                print(error_message)
                subprocess.run(["docker", "rm", "-f", container_name], check=True)
                failed_docker_versions.append(docker_version)
                continue  # Skip this version and continue with the next one
        print(docker_version)

        for version in version_list:
            version_path = os.path.join(base_fp, version)
            if not os.path.exists(version_path):
                continue

            for subdir in os.listdir(version_path):
                subdir_path = os.path.join(version_path, subdir)
                if not os.path.isdir(subdir_path):
                    continue

                json_files = [file for file in os.listdir(subdir_path) if file.endswith('get_interact_command.json')]
                if not json_files:
                    continue

                output_file_path = os.path.join(f'{outf}/{docker_version}', subdir)

                for file in json_files:
                    file_path = os.path.join(subdir_path, file)           
                    commands = get_commands_from_file(file_path)
                    global total
                    total += len(commands)
                    if commands:
                        run_joomla_container(docker_version, version, commands, subdir)
                        time.sleep(0.1)


        # After processing all versions, stop and remove the Joomla container
        if major < 3 or (major == 3 and (minor < 8 or (minor == 8 and patch == 0))) or major > 3 or (major == 3 and (minor > 9 or (minor == 9 and patch > 28))):
            subprocess.run(["docker", "compose", "-f", compose_file, "down"], check=True)
        else:
            subprocess.run(["docker", "rm", "-f", container_name], check=True)
        print(f"Removed Joomla version {docker_version} container")


# Example invocation
if __name__ == "__main__":
    versions_file = ''
    with open(versions_file, 'r') as file:
        versions = file.read().splitlines()
    versions_file2 = ''
    with open(versions_file2, 'r') as file:
        docker_versions = file.read().splitlines()
    deploy_versions(versions, docker_versions)
    print(f"Total commands processed: {total}")

