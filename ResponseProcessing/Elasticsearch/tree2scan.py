# coding = utf-8
# This Script is used to transform the tree structure to scan script 

from response_process import mask_text,similarity
import os, re, sys, json
from func_timeout import func_set_timeout
import subprocess
import func_timeout


def get_threshold(ctype:str,probe_name):
    if ctype == 'es':
        if probe_name in ['6.0.0_72','5.6.0_15']:
            threshold = 0.95
        else:
            threshold = 0.9
    else:
        threshold = 1        
    
    # print(probe_name,threshold)
    
    return threshold

def read_file(file_path:str,file_type:str):
    if file_type == 'json':
        with open(file_path,'r') as f:
            return json.load(f)
    else:
        with open(file_path,'r') as f:
            return f.read()


@func_set_timeout(10)
def execute_command(command: str):
    p = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, err = p.communicate()
    return out, err


def safe_execute_command(command: str):
    try:
        out, err = execute_command(command)
        return out, err
    except func_timeout.exceptions.FunctionTimedOut as e:
        return b"command timeout", str(e).encode()
    except Exception as e:
        return b"command error", str(e).encode()
    

def test_command_in_one_server(version: str, command: str, hostinfo: str):
    host_pattern = re.compile(r"http[s]{0,1}://localhost:9200")
    matches = host_pattern.findall(command)
    if len(matches) == 0:
        if 'localhost:9200' in command:
            command = command.replace('localhost:9200','http://localhost:9200')
            matches = host_pattern.findall(command)
            
            if len(matches) == 0:
                print("no hostinfo in command",command)
                return None
            
        else:
            print("no hostinfo in command",command)
            return None
    http_command_patch = command
    https_command_patch = command
    
    for match in matches:
        match_string = match
        http_command_patch = http_command_patch.replace(
            match_string, f"http://{hostinfo}"
        )
        https_command_patch = https_command_patch.replace(
            match_string, f"https:/{hostinfo}"
        )
        if '-k ' not in https_command_patch:
            https_command_patch = https_command_patch.replace("curl",'curl -k') 

    
    save_dir = os.path.join(
        "xx/RealWorld/Response", hostinfo
    )
    if os.path.exists(save_dir) == False:
        os.makedirs(save_dir)

    results = {'http':'','https':''}
    save_fp = os.path.join(save_dir, f"{version}.json")
    if not os.path.exists(save_fp):
        out, err = safe_execute_command(http_command_patch)
        http_content =  (
                "out is:\n"
                + out.decode("utf-8")
                + "\n\n\n"
                + "error is:\n"
                + err.decode("utf-8")
            )
        out, err = safe_execute_command(https_command_patch)
        https_content = (
                "out is:\n"
                + out.decode("utf-8")
                + "\n\n\n"
                + "error is:\n"
                + err.decode("utf-8")
            )
        results['http'] = http_content
        results["https"] = https_content
        
        with open(save_fp, "w") as fp:
            json.dump(results, fp)
    with open(save_fp,'r') as fp:
        results = json.load(fp)
    return results
        
    


def use(probe_name:str,hostinfo:str,ctype='es',auth_flag:str=None):
    if ctype == 'es':
        all_es_probes = read_file(f'xx/es_probe_sets_{auth_flag}.json','json')
        results = test_command_in_one_server(probe_name,all_es_probes[probe_name],hostinfo)
        http_content = results["http"]
        https_content = results["https"]
        response = https_content
        if 'curl: (35)' in https_content:
            response = http_content
    return response


def get_resp(response_category:str,ctype='es',auth_flag:str=None):
    read_dir = f'xx/{auth_flag}'
    resp_name = response_category.split('_r:')[1]
    probe_name = response_category.split('_r:')[0][2:]
    resp_file = os.path.join(read_dir,f'{resp_name}/{probe_name}.txt')
    resp = read_file(resp_file,'txt')
    return resp


def get_similarity(response1:str,response2:str):
    response1 = mask_text(response1)
    response2 = mask_text(response2)
    return similarity(response1,response2)



def compare_by_similarity(response1:str,response2:str):
    response1 = mask_text(response1)
    response2 = mask_text(response2)
    sim = similarity(response1,response2)
    return sim



def extract_p_r_from_path(path:str):
    probe_name = path.split('_r:')[0][2:]
    resp_name = path.split('_r:')[1]
    return probe_name,resp_name

def tree2scan(hostinfo:str,tree:json,ctype='es',probe_data:dict=None,conflict_relations:dict=None,look_path:list=[],auth_flag:str=None,one_hundred_flag=False):

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
    resp = use(probe_name,hostinfo,ctype,auth_flag=auth_flag)
    
    if resp == 'command timeout' or 'command timeout' in resp:
        reason = 'command timeout in probe: {}'.format(tree['name'])
        path = tree['path']
        remains_version = tree['not_distinguished_versions']
        return [reason,path,remains_version]
    
    
    for child in tree['children']:
        comp_resp = get_resp(child,ctype,auth_flag=auth_flag)
        
        if not one_hundred_flag:
            cmp_sim = compare_by_similarity(resp,comp_resp)
            threshold = get_threshold(ctype,probe_name)
            flag= cmp_sim > threshold
            
        else:
            response1 = mask_text(resp)
            response2 = mask_text(comp_resp)
            flag= (response1 == response2)
            
        if flag:
            print(f'probe: {probe_name} matched with resp: {child}')
            # print(f'probe: {probe_name} matched with resp: {child}, sim: {cmp_sim}')
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
            
            
            if not one_hundred_flag:
                cmp_sim = compare_by_similarity(resp,comp_resp)
                threshold = get_threshold(ctype,probe_name)
                flag = cmp_sim > threshold
            else:
                response1 = mask_text(resp)
                response2 = mask_text(comp_resp)
                flag = (response1==response2)
                
                
            if flag:
                # print(f'probe: {probe_name} matched with resp: {child_name}, sim: {cmp_sim}, sim: {cmp_sim}')
                print(f'probe: {probe_name} matched with resp: {child_name}')
                path = tree['path'] 
                for look in path:
                    lprobe_name,lresp_name = extract_p_r_from_path(look)
                    if 'failed_match' == lresp_name:
                        continue
                    if lresp_name not in v_set: 
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
        