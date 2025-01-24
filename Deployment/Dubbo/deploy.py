

from deploy_command import (
    process_dubbo_commands,
    telnet_dubbo_multiple_commands,
    deploy_2_5_x,
    deploy,
    uninstall_docker,
    pre_install_docker,
)
import os
import time
import subprocess,re
from func_timeout import func_set_timeout
import func_timeout

def generate_modify_dockerfile_templates(workdir:str, version:str, security_flag:str = None):
    def version2dockerFileName(version:str):
        if version.startswith("2.5"):
            return "Dubbo_docker_25"
        elif version.startswith("2.6"):
            return "Dubbo_docker_26"
        else:
            return "Dubbo_docker"
    def version2newmatch(dversion:str):
        if dversion.startswith("3") and dversion not in ['3.0.1','3.0.0']:
            # rm command: ls,ps,cd,pwd,count,invoke,select,shutdown
            new_match = ', "-Ddubbo.provider.telnet=help,trace,status,log,clear,exit" '+',  "exec:java"]'
        else:
            new_match = ', "-Ddubbo.provider.telnet=help,ls,ps,cd,pwd,trace,count,invoke,select,status,log,clear,exit,shutdown" '+',  "exec:java"]'
        return new_match
    dockerFilenmae = version2dockerFileName(version)
    plain_dockerfile = f'{workdir}/dockerfileTemplates/{dockerFilenmae}'
    dst_dockerfile = f'{workdir}/{dockerFilenmae}'
    with open(plain_dockerfile,'r') as f:
        plain_content = f.read()
    if security_flag is None:
        pass    # 不做任何修改
    elif security_flag == 'enabled':
        end_pattern = re.compile(r',\s*"exec:java"\]')
        matches = end_pattern.findall(plain_content)
        for match in matches:
            new_match = version2newmatch(version)
            plain_content = plain_content.replace(match,new_match)
    # elif security_flag == 'disabled':
    #     end_pattern = re.compile(r',\s*"exec:java"\]')
    #     matches = end_pattern.findall(plain_content)
    #     for match in matches:
    #         new_match = ', "-Ddubbo.provider.telnet=disabled" '+',  "exec:java"]'
    #         plain_content = plain_content.replace(match,new_match)        
    
    with open(dst_dockerfile,'w') as f:
        f.write(plain_content)

@func_set_timeout(600)
def safe_deploy(version, zookeeper_ip, work_dir, port = '20880',security_flag:str=None):
    # 判断version
    
    generate_modify_dockerfile_templates(work_dir, version, security_flag)
    
    if version.startswith("2.5"):
        script_path = (
            "deploy_25x.sh"
        )
        out, err = deploy_2_5_x(version, zookeeper_ip, work_dir, script_path, port)
    elif version.startswith("2.6"):
        script_path = (
            "deploy_26x.sh"
        )
        out, err = deploy(version, zookeeper_ip, work_dir, script_path, port)
    else:
        script_path = "deploy.sh"
        out, err = deploy(version, zookeeper_ip, work_dir, script_path, port)
    return out, err


def test_one_newly(version: str, input_commands: list, save_dir: str, host = "127.0.0.1", port = 20880,  security_flag: str = None):
    save_dir = os.path.join(save_dir, version)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)


    zookeeper_ip = "" # ipaddress of zookpeer
    work_dir = ""

    pre_install_docker()  # stop all running docker containers
    try:
        print("Deploying version:", version)
        safe_deploy(version, zookeeper_ip, work_dir, port, security_flag=security_flag)
        time.sleep(20)
    except func_timeout.exceptions.FunctionTimedOut as e:
        print(f"Deploy {version} timeout")
        return
    except Exception as e:
        print(f"Deploy {version} error: {e}")
        return


    # loop until the server is ready
    start_time = time.time()
    while True:
        test_flag = telnet_dubbo_multiple_commands(host, port, ["ls"], save_fp=None)
        # print(test_flag)
        if test_flag:
            break
        current_time = time.time()
        if current_time - start_time > 60:
            print("Server is not ready")
            return

    # test commands
    for index,command in enumerate(input_commands):
        fname = 'index_{}_'.format(index)
        
        save_fp = os.path.join(save_dir, fname + ".txt")
        telnet_dubbo_multiple_commands(host, port, [command], save_fp=save_fp)
        time.sleep(2)
    
    uninstall_commands = uninstall_docker(version)
    
    subprocess.run(uninstall_commands, shell=True)

if __name__ == '__main__':
    test_one_newly("2.7.6", ["ls","ps","cd","pwd","count","invoke","select","shutdown"], "", host = "")
