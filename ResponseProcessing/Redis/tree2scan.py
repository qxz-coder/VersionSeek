# coding = utf-8
# This Script is used to transform the tree structure to scan script 
import subprocess
import os,json,re
import sys
sys.path.append('../../ResponseProcessing/Redis')
from difflib import SequenceMatcher
from response_process import mask_text


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
            redis_commands.append(stripped_command.strip())

    return redis_commands

def redis_commands(host, port, commands, save_fp=None,auth_flag = None):
    try:
        with open(save_fp, 'a') as f_output: 
            for command in commands:
                cmd = extract_command(command)
                for single_command in cmd:
                    full_command = f"redis-cli -h {host} -p {port} {single_command}"
                    #print(f"Executing command: {full_command}")
                    try:
                        result = subprocess.run(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
                        f_output.write(f"Command: {full_command}\n")
                        f_output.write(f"Output:\n{result.stdout}\n")
                        f_output.write(f"Error:\n{result.stderr}\n\n")
                    except Exception as e:
                        f_output.write(f"Command: {full_command}\n")
                        f_output.write(f"Error: {str(e)}\n\n")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")  
        return False

def read_file(file_path:str,file_type:str):
    if file_type == 'json':
        with open(file_path,'r') as f:
            return json.load(f)
    else:
        with open(file_path,'r') as f:
            return f.read()

def use(probe_name:str,hostinfo:str,ctype='redis',auth_flag:str=None):
    read_dir = ''
    if not os.path.exists(read_dir):
        os.makedirs(read_dir)
    response = ""
    
    if ctype == 'redis':
        file_path = os.path.join(read_dir,f'{probe_name}.txt')
        json_file_path = f'VersionSeek/Probes/Redis/probes_{auth_flag}.json'
        with open(json_file_path, 'r') as json_file:
            all_cmds = json.load(json_file)
        
        index = int(probe_name.split('_')[1])
        commands = [all_cmds.get(f'index_{index}', '')]  
        if not os.path.exists(file_path):
            host, port = hostinfo.split(':')
            port = int(port)
            flag = redis_commands(host, port, commands, save_fp=file_path,auth_flag=auth_flag)
            if not flag:
                return 'command timeout'
        response = read_file(file_path, 'txt')
    return response


def get_resp(response_category:str,ctype='redis',auth_flag:str=None):
    if ctype == 'es':
        read_dir = ''
        # print(response_category)
        probe,resp = response_category.split('_')
        probe_name = probe.split('p:')[1]
        resp_name = resp.split('r:')[1]
        resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
        resp = read_file(resp_file,'txt')
    
    elif ctype == 'dubbo':
        read_dir = ''
        resp_name = response_category.split('_r:')[1]
        probe_name = response_category.split('_r:')[0][2:]
        # probe_name = '_'.join(probe_name)
        resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
        resp = read_file(resp_file,'txt')

    elif ctype == 'redis':
        read_dir = ''
        resp_name = response_category.split('_r:')[1]
        probe_name = response_category.split('_r:')[0][2:]
        # probe_name = '_'.join(probe_name)
        resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
        resp = read_file(resp_file,'txt')
    return resp


def get_similarity(response1:str,response2:str,auth_flag = None):
    if auth_flag != 'deny':
        response1 = mask_text(response1)
        response2 = mask_text(response2)
 
    return response1 == response2


def extract_p_r_from_path(path:str):
    probe_name = path.split('_r:')[0][2:]
    resp_name = path.split('_r:')[1]
    return probe_name,resp_name



def tree2scan(hostinfo:str,tree:json,ctype='redis',probe_data:dict=None,conflict_relations:dict=None,look_path:list=[],auth_flag:str=None):
    
    if len(look_path) > 0:
        temp = look_path
        for p in tree['path']:
            if p not in temp:
                temp.append(p)
        tree['path'] = temp
    
    
    if 'children' not in tree or len(tree['children']) == 0:
        if tree['type'] == 'version':
            version = tree['name'].split('version_')[1]
            return ['completely matched', tree['path'], [version],auth_flag]
        else:
            return ['completely matched', tree['path'], tree['not_distinguished_versions'],auth_flag]
        
    probe_name = tree['name'].split('_')[1:]
    probe_name = '_'.join(probe_name)
    resp = use(probe_name,hostinfo,ctype,auth_flag=auth_flag)
    
    if resp == 'command timeout' or 'command timeout' in resp:
        reason = 'command timeout in probe: {}'.format(tree['name'])
        path = tree['path']
        remains_version = tree['not_distinguished_versions']
        return [reason,path,remains_version,auth_flag]
    
    
    for child in tree['children']:
        comp_resp = get_resp(child,ctype,auth_flag=auth_flag)
        cmp_sim = get_similarity(resp,comp_resp,auth_flag=auth_flag)
        print(cmp_sim)

        if cmp_sim == 1:
            #print(f'probe: {probe_name} matched with resp: {child}, sim: {cmp_sim}')
            result = tree2scan(hostinfo,tree['children'][child],look_path=tree['path'],auth_flag=auth_flag)
            return result
        else:
  
            pass
   
    
    
    
    if probe_data is not None:
        diff_set_lists = probe_data[probe_name]
        
        for child in tree['children']:
            resp_name = child.split('_r:')[1]
            for v_set in diff_set_lists:
                if resp_name in v_set:
                    diff_set_lists.remove(v_set)    
        

        for v_set in diff_set_lists:
            if len(v_set) == 0:
                continue
            fisrt_resp_name = list(v_set)[0]
            child_name = f'p:{probe_name}_r:{fisrt_resp_name}'
            comp_resp = get_resp(child_name,ctype,auth_flag=auth_flag)
            cmp_sim = get_similarity(resp,comp_resp,auth_flag=auth_flag)
            if cmp_sim:
                #print(f'probe: {probe_name} matched with resp: {child_name}, sim: {cmp_sim}')
                print(f'probe: {probe_name} matched with resp: {child_name}')
                path = tree['path'] 
                for look in path:
                    lprobe_name,lresp_name = extract_p_r_from_path(look)
                    if 'failed_match' == lresp_name:
                        continue
                    if lresp_name not in v_set: # conflict 
                        # print(f'conflict between {probe_name} and {lprobe_name},vset: {v_set}')
                        conflict_relations[probe_name] = conflict_relations.get(probe_name,[])
                        conflict_relations[probe_name].append(lprobe_name)
                        conflict_relations[probe_name] = list(set(conflict_relations[probe_name]))
                        
                        
                        conflict_relations[lprobe_name] = conflict_relations.get(lprobe_name,[])
                        conflict_relations[lprobe_name].append(probe_name)
                        conflict_relations[lprobe_name] = list(set(conflict_relations[lprobe_name])) 
                        
                        
                        # newly add conflict result
                        conflict_relations['conflict_result'] = conflict_relations.get('conflict_result',{})
                        conflict_relations['conflict_result'][probe_name] = v_set
                        
                        for lvset in probe_data[lprobe_name]:
                            # print(lvset)
                            if lresp_name in lvset:
                                conflict_relations['conflict_result'][lprobe_name] = lvset
                                break
                return ["conflict",None,None]
    
    
    reason = 'not matched in probe: {}'.format(tree['name'])
    path = tree['path']
    fail_path = f'p:{probe_name}_r:failed_match'
    if fail_path not in path:
        path.append(fail_path)
    remains_version = tree['not_distinguished_versions']
    return [reason,path,remains_version,auth_flag]


def get_host_infos(save_dir:str):
    hostinfos = os.listdir(save_dir)
    return hostinfos
    
def get_engine_truth(data:dict,hostinfo:str,ctype='redis'):
    if ctype == 'redis':
        for auth_type in data:
            if hostinfo in data[auth_type]:
                return data[auth_type][hostinfo]
        return 'notfound' 
    elif ctype == 'dubbo':
        return 'notfound'


def check_connect_failed(walk_dir:str):
    error_hostinfos = []
    error_counts = dict()
    for root,dirs,files in os.walk(walk_dir):
        for file in files:
            file_path = os.path.join(root,file)
            with open(file_path,'r') as f:
                content = f.read()
                if 'curl: (7) Failed to connect to' in content or 'curl: (56) Recv failure: Connection reset by peer' in content :
                    
                    hostinfo = root.split('/')[-1]
                    error_hostinfos.append(hostinfo)
                    error_counts[hostinfo] = error_counts.get(hostinfo,0) + 1
    print(set(error_hostinfos))
    sorted_counts = sorted(error_counts.items(),key=lambda x:x[1],reverse=True)
    print(sorted_counts)
    return error_hostinfos
        
if __name__ == "__main__":
    check_connect_failed('')
    exit(0)
    