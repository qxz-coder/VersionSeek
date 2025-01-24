import os,subprocess
from func_timeout import func_set_timeout
import func_timeout
import telnetlib

# bash example: 'bash ./deployDubbo.sh /home/song/workspace/DubboDir 3.2.0 20880 10.177.83.198'


# 封装一个用于在shell执行命令并保存输出内容的函数
@func_set_timeout(120)
def execute_command(command:str):
    p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = p.communicate()
    return out,err

def safe_execute_command(command:str):
    try:
        out,err = execute_command(command)
        return out,err
    except func_timeout.exceptions.FunctionTimedOut as e:
        return b'command timeout',str(e).encode()
    except Exception as e:
        return b'command error',str(e).encode()

# 大于2.6的版本，可以如此
def deploy(version:str,zookeeper_ip:str,work_dir:str,script_path:str, port = '20880'):
    command = f'bash {script_path} {work_dir} {version} {port} {zookeeper_ip}'
    print(command)
    out,err = safe_execute_command(command)
    print(out,err)
    return out,err


# 2.5.x的版本,可以如此
def deploy_2_5_x(version:str,zookeeper_ip:str,work_dir:str,script_path:str,port = '20880'):
    # 'sources.list'
    sources_lists = '''# deb http://http.debian.net/debian unstable main
deb http://mirrors.ustc.edu.cn/debian stable main contrib non-free
# deb-src http://mirrors.ustc.edu.cn/debian stable main contrib non-free
deb http://mirrors.ustc.edu.cn/debian stable-updates main contrib non-free
# deb-src http://mirrors.ustc.edu.cn/debian stable-updates main contrib non-free
# deb http://mirrors.ustc.edu.cn/debian stable-proposed-updates main contrib non-free
# deb-src http://mirrors.ustc.edu.cn/debian stable-proposed-updates main contrib non-free
# '''
    
    # 'sources.list'
    _version = version.replace('.','_')
    subbo_dir = f'dubbo_{_version}'
    source_dir = os.path.join(work_dir,subbo_dir)
    
    if not os.path.exists(source_dir):
        os.makedirs(source_dir)
    
    source_fp = os.path.join(source_dir,'sources.list')
    with open(source_fp,'w') as f:
        f.write(sources_lists)
    
    command = f'bash {script_path} {work_dir} {version} {port} {zookeeper_ip}'
    print(command)
    out,err = safe_execute_command(command)
    print(out,err)
    
    return out,err



def telnet_dubbo_multiple_commands(host, port, commands, save_fp=None):
    try:
        # 连接到 Dubbo 服务器
        telnet = telnetlib.Telnet(host, port)
        # print(f"Server: {host}:{port}")
        
        for command in commands:
            # 发送每条指令
            # print(f"\ncommand: {command}")
            telnet.write(command.encode('utf-8') + b"\n")

            # 读取响应直到提示符 dubbo>
            response = telnet.read_until(b"dubbo>", timeout=10)
            # print("Server response: ",response.decode('utf-8'))1
            
            if save_fp is not None:
                with open(save_fp,'w') as wf:
                    wf.write(response.decode('utf-8'))
        # 关闭连接
        telnet.close()

        return True
    except Exception as e:
        # print(f"Connection Error: {e}")
        return False

def process_dubbo_commands(text:str):
    # replace '````
    text = text.replace('```','').replace('```bash', '')
    
    
    commands = text.split('\n')
    
    # filter out empty command
    commands = [c.strip() for c in commands if c.strip()]
    
    # filter out telnet command, filter out ```
    for cmd in commands:
        if 'telnet' in cmd:
            commands.remove(cmd)
    
    # print(commands)
    return commands

def uninstall_docker(version):
    name = 'DUBBO_' + version.replace('.','_')
    commands = 'docker stop {} && docker rm {}'.format(name,name)
    # print(commands)
    return commands

def pre_install_docker(port = '20880'):
    # print(123)
    def get_dubbo_containers():
    # 列出所有正在运行的容器
        result = subprocess.run(["docker", "ps", "--format", "{{.ID}} {{.Image}}"], capture_output=True, text=True)
        
        # 获取输出结果并筛选出 dubbo 容器
        containers = result.stdout.splitlines()
        dubbo_containers = [line.split()[0] for line in containers if "dubbo" in line.lower()]
        return dubbo_containers

    def stop_containers(container_ids):
        for container_id in container_ids:
            print(f"Stopping container: {container_id}")
            subprocess.run(["docker", "stop", container_id])

    dubbo_containers = get_dubbo_containers()
    # 如果找到Dubbo容器，则关闭它们
    if dubbo_containers:
        print("Stopping Dubbo containers...")
        stop_containers(dubbo_containers)
    else:
        print("No Dubbo containers found.")



if __name__ == "__main__":
    # script_path = '/home/song/workspace/OSCVersionDetect/Dubbo/scripts/deployDubbo.sh'
    # version ='3.1.6'
    version ='2.5.6'
    zookeeper_ip = '10.177.83.198'
    work_dir = '/home/song/workspace/OSCVersionDetect/Dubbo/scripts/Docker'
    port = '20880'
    
    script_path = '/home/song/workspace/OSCVersionDetect/Dubbo/scripts/deploy_25x.sh'
    deploy_2_5_x(version,zookeeper_ip,work_dir,script_path)
    # deploy(version,zookeeper_ip,work_dir,script_path)