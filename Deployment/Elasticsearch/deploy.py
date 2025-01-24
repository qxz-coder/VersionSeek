import os,json,re
import subprocess

def get_docker_file(minor_version:str):
    fp_template1 = 'xx/detail_documents/{}/Setup Elasticsearch/Installing Elasticsearch/docker.html'    # user'guide about docker from es official website
    fp_template2 = 'xx/detail_documents/{}/Set up Elasticsearch/Installing Elasticsearch/docker.html'
    
    fp = ''
    for fp_template in [fp_template1,fp_template2]:
        temp_fp = fp_template.format(minor_version)
        if os.path.exists(temp_fp):
            fp = temp_fp
    
    
    # fp = fp_template.format(minor_version)
    
    pattern = 'docker run -p[^<]+|docker run --name[^<]+'
    with open(fp,'r') as f:
        content = f.read()
        matches = re.findall(pattern,content)
        return matches
    
def get_docker_install_command(version):
    minor_version = '.'.join(version.split('.')[:-1])
    matches = get_docker_file(minor_version)
    commands = ''
    if len(matches) > 1:
        for m in matches:
            if 'elasticsearch' in m:
                new_command = ':'.join(m.split(':')[:-1]) + ':' + version
                commands += new_command
    else:
        commands = ':'.join(matches[0].split(':')[:-1]) + ':' + version
    
    
    # change_names 
    if '--name es01' in commands:
        commands = commands.replace('--name es01','--name es-' + version)
    else:
        commands = commands.replace('docker run','docker run --name es-' + version)
    
    # run in background
    commands = commands.replace('docker run','docker run -d')
    return commands

def get_docker_install_command_with_auth(version,auth_flag:str=None):
    '''
    auth_flag: 1. default, 2.open, 3.closed
    '''
    
    minor_version = '.'.join(version.split('.')[:-1])
    matches = get_docker_file(minor_version)
    commands = ''
    if len(matches) > 1:
        for m in matches:
            if 'elasticsearch' in m:
                new_command = ':'.join(m.split(':')[:-1]) + ':' + version
                commands += new_command
    else:
        commands = ':'.join(matches[0].split(':')[:-1]) + ':' + version
    
    
    # change_names 
    if '--name es01' in commands:
        commands = commands.replace('--name es01','--name es-' + version)
    else:
        commands = commands.replace('docker run','docker run --name es-' + version)
    
    # auth_flag
    if auth_flag is not None and auth_flag in ['open','closed']:
        if auth_flag == 'open':
            if version.startswith('8.'):
                commands = commands.replace('docker run','docker run -e "discovery.type=single-node"  -e "xpack.security.enabled=false" -e "xpack.security.transport.ssl.enabled=false"')
            else:
                commands = commands.replace('docker run','docker run -e "xpack.security.enabled=false" -e "xpack.security.transport.ssl.enabled=false"')
        elif auth_flag == 'closed':
            if version.startswith('6'):
                if version.startswith('6.8'):
                    commands = commands.replace('docker run','docker run -e "xpack.security.enabled=true" -e "xpack.security.transport.ssl.enabled=true" -e "ELASTIC_USERNAME=elastic" -e "ELASTIC_PASSWORD=DkIedPPSCb"')
                else:
                    print(f'{version} has no default x-pack')
                    return None
                commands = commands.replace('docker run','docker run -e "xpack.security.enabled=true" -e "xpack.security.transport.ssl.enabled=true" -e "ELASTIC_USERNAME=elastic" -e "ELASTIC_PASSWORD=DkIedPPSCb"')
            elif version.startswith('7.'):
                if not version.startswith('7.0'):
                    commands = commands.replace('docker run','docker run -e "xpack.security.enabled=true" -e "xpack.security.transport.ssl.enabled=true" -e "ELASTIC_USERNAME=elastic" -e "ELASTIC_PASSWORD=DkIedPPSCb"')
                else:
                    print(f'{version} has no default x-pack')
                    return None
            else:
                # 5.x & 8.x, do nothing
                pass
    # run in background
    commands = commands.replace('docker run','docker run -d')
    return commands




def pre_install_docker():
    # print(123)
    def get_elasticsearch_containers():
        result = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Image}}"], capture_output=True, text=True)
        
        containers = result.stdout.splitlines()
        elasticsearch_containers = [line.split()[0] for line in containers if "elasticsearch" in line.lower()]
        return elasticsearch_containers

    def stop_containers(container_ids):
        for container_id in container_ids:
            print(f"Stopping container: {container_id}")
            subprocess.run(["docker", "stop", container_id])

    elasticsearch_containers = get_elasticsearch_containers()

    if elasticsearch_containers:
        print("Stopping Elasticsearch containers...")
        stop_containers(elasticsearch_containers)
    else:
        print("No Elasticsearch containers found.")
    


def uninstall_docker(version):
    name = 'es-' + version
    commands = 'docker stop {} && docker rm {}'.format(name,name)
    return commands


if __name__ == '__main__':

    print(get_docker_install_command('5.1.0'))

