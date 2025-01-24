# coding = utf-8
# This Script is used to transform the tree structure to scan script 
import telnetlib
import os,json,re
from response_process import mask_text,similarity

def telnet_dubbo_multiple_commands(host, port, commands, save_fp=None):
    try:
        telnet = telnetlib.Telnet(host, port)
        
        for command in commands:
            telnet.write(command.encode('utf-8') + b"\n")

            response = telnet.read_until(b"dubbo>", timeout=10)
            
            if save_fp is not None:
                with open(save_fp,'w') as wf:
                    wf.write(response.decode('utf-8'))
        telnet.close()

        return True
    except Exception as e:
        return False


def read_file(file_path:str,file_type:str):
    if file_type == 'json':
        with open(file_path,'r') as f:
            return json.load(f)
    else:
        with open(file_path,'r') as f:
            return f.read()

def use(probe_name:str,hostinfo:str,ctype='es'):

    read_dir = f'{hostinfo}'
    if os.path.exists(read_dir) == False:
        os.makedirs(read_dir)
    
    if ctype == 'es':
        http_content = read_file(os.path.join(read_dir,f'http_{probe_name}.txt'),'txt')
        https_content = read_file(os.path.join(read_dir,f'https_{probe_name}.txt'),'txt')
        response = https_content
        if 'curl: (35)' in https_content:
            response = http_content
    elif ctype == 'dubbo':
        file_path = os.path.join(read_dir,f'{probe_name}.txt')
        all_cmds = ''   # save commands fp
        index = int(probe_name.split('_')[1])
        commands = [all_cmds[index]]
        print('use commands:',commands)
        if not os.path.exists(file_path):
            host,port = hostinfo.split(':')
            port = int(port)
            flag = telnet_dubbo_multiple_commands(host, port, commands, save_fp=file_path)
            if not flag:
                return 'command timeout'
        response = read_file(file_path,'txt')
    return response


def get_resp(response_category:str,ctype='es'):
    if ctype == 'es':
        read_dir = ''   # save response
        # print(response_category)
        probe,resp = response_category.split('_')
        probe_name = probe.split('p:')[1]
        resp_name = resp.split('r:')[1]
        resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
        resp = read_file(resp_file,'txt')
    
    elif ctype == 'dubbo':
        read_dir = '' # save response
        resp_name = response_category.split('_r:')[1]
        probe_name = response_category.split('_r:')[0][2:]
        # probe_name = '_'.join(probe_name)
        resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
        resp = read_file(resp_file,'txt')
    return resp


def get_similarity(response1:str,response2:str):
    response1 = mask_text(response1)
    response2 = mask_text(response2)
    return similarity(response1,response2)


def compare(response1:str,response2:str,ctype='es'):
    response1 = mask_text(response1)
    response2 = mask_text(response2)
    
    # 
    if ctype == 'dubbo':
        return similarity(response1,response2) > 0.97
    
    elif ctype == 'es':
        flag = similarity(response1,response2) > 0.9

        return similarity(response1,response2) > 0.85

def extract_p_r_from_path(path:str):
    probe_name = path.split('_r:')[0][2:]
    resp_name = path.split('_r:')[1]
    return probe_name,resp_name



def tree2scan(hostinfo:str,tree:json,ctype='dubbo',probe_data:dict=None,conflict_relations:dict=None,look_path:list=[]):

    if len(look_path) > 0:
        temp = look_path
        for p in tree['path']:
            if p not in temp:
                temp.append(p)
        tree['path'] = temp

    if 'children' not in tree or len(tree['children']) == 0:
        if tree['type'] == 'version':
            version = tree['name'].split('version_')[1]
            return ['completely matched', tree['path'], [version]]
        else:
            return ['completely matched', tree['path'], tree['not_distinguished_versions']]

    probe_name = tree['name'].split('_')[1:]
    probe_name = '_'.join(probe_name)
    resp = use(probe_name,hostinfo,ctype)
    
    if resp == 'command timeout':
        reason = 'command timeout in probe: {}'.format(tree['name'])
        path = tree['path']
        remains_version = tree['not_distinguished_versions']
        return [reason,path,remains_version]
    

    pass    # just for debug!!!
    
    for child in tree['children']:
        comp_resp = get_resp(child,ctype)
        if compare(resp,comp_resp,ctype):
            result = tree2scan(hostinfo,tree['children'][child],look_path=tree['path'])
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
            comp_resp = get_resp(child_name,ctype)
            if compare(resp,comp_resp,ctype):   # 
                path = tree['path'] # 
                for look in path:
                    lprobe_name,lresp_name = extract_p_r_from_path(look)
                    if 'failed_match' == lresp_name:
                        continue
                    
                    if lresp_name not in v_set: 
                        conflict_relations[probe_name] = conflict_relations.get(probe_name,[])
                        conflict_relations[probe_name].append(lprobe_name)
                        conflict_relations[probe_name] = list(set(conflict_relations[probe_name]))

                        conflict_relations[lprobe_name] = conflict_relations.get(lprobe_name,[])
                        conflict_relations[lprobe_name].append(probe_name)
                        conflict_relations[lprobe_name] = list(set(conflict_relations[lprobe_name]))
                        
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
    # path.append(fail_path)
    remains_version = tree['not_distinguished_versions']
    return [reason,path,remains_version]

def get_host_infos(save_dir:str):
    hostinfos = os.listdir(save_dir)
    return hostinfos
    
def get_engine_truth(data:dict,hostinfo:str,ctype='es'):
    if ctype == 'es':
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
        