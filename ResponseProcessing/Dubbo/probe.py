# This script is used to get all probes from the LLMResults
import os,re,json
from response_process import similarity,mask_text


def errorInContent(content):
    return False

def compare_versions(version1, version2):
    version1 = version1.split('_')[0]
    version2 = version2.split('_')[0]
    v1_parts = [int(v) for v in version1.split('.')]
    v2_parts = [int(v) for v in version2.split('.')]
    max_length = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_length - len(v1_parts)))
    v2_parts.extend([0] * (max_length - len(v2_parts)))
    
    for v1, v2 in zip(v1_parts, v2_parts):
        if v1 > v2:
            return 1  
        elif v1 < v2:
            return -1  
    
    return 0  

def get_test_command_from_llm(version:str,base_fp:str):
    file_path = os.path.join(base_fp,version)
    
    files = os.listdir(file_path)
    # print(files)
    for file in files:
        if file.endswith('get_interact_command.json'):
            with open(os.path.join(file_path,file),'r') as f:
                data = json.load(f)
            # print(data[-1][0]['content'])
            command = data[-1][0]['content']
            # break
    
    # if not filter_invalid_command(command):
        # return ''
        # return command
        # print(version,command)
    return command

def get_test_command_from_llm_robust(version:str,base_fp:str):
    commands = []
    file_path = os.path.join(base_fp,version)
    
    for root,ds,fs in os.walk(file_path):
        for f in fs:
            if f.endswith('get_interact_command.json'):
                with open(os.path.join(root,f),'r') as rf:
                    data = json.load(rf)
                command = data[-1][0]['content']
                commands.append(command)
    return commands


def select_one_valid_command(commands:list):
    for command in commands:
        if filter_not_valid_command(command):
            return command
    return None

def get_all_valid_commands(commands:list):
    valid_commands = []
    for command in commands:
        if filter_not_valid_command(command):
            valid_commands.append(command)
    return valid_commands



def filter_not_valid_command(content):
    if re.search(r'[\u4e00-\u9fa5]',content):
        return False

    if 'no specific command' in content.lower():
        return False

    if 'the specific command' in content.lower():
        return False

    if '@dependabot rebase' in content:
        return False

    if 'mvn clean install' in content:
        return False

    if 'relevant command' in content:
        return False

    if 'a specific command' in content:
        return False

    if 'direct command' in content:
        return False

    if '-Djava.net.prefer' in content:
        return False
    
    if 'The provided document' in content:
        return False
    
    if 'The provided information' in content:
        return False
    
    if 'No relevant files' in content:
        return False
    
    if '```java' in content:
        return False
    
    return True

def get_parent_directory(path):
    if os.path.isfile(path):
        return os.path.basename(os.path.dirname(path))
    return os.path.basename(os.path.normpath(path))


def version2diffsetV2(index, base_dir = '', threshold = 0.9):
    resp = {}
    differnece_result = {}
    for root,ds,fs in os.walk(base_dir):
        for f in fs:
            full_path = os.path.join(root,f)
            fname = 'index_{}_'.format(index) 
            if fname in f:
                cmp_version = get_parent_directory(full_path)
                
                with open(full_path,'r') as rf:
                    content = rf.read()
                    if not errorInContent(content):
                        resp[cmp_version] = content
    
    for v in resp:
        find_flag = False
        for key in differnece_result:
            resp[v] = mask_text(resp[v])
            resp[key] = mask_text(resp[key])
            
            if threshold < 1:
                sim_flag = (similarity(resp[v],resp[key]) >= threshold)
            else:
                sim_flag = (resp[v] == resp[key])
                
            if sim_flag:
                differnece_result[key] = differnece_result.get(key,[]) + [v]
                find_flag = True
        if not find_flag:
            differnece_result[v] = [v]

    multi_version = {}
    for key1 in differnece_result:
        for key2 in differnece_result:
            if key1 != key2:

                if len(set(differnece_result[key1]).intersection(set(differnece_result[key2]))) > 0:
                    intersection = set(differnece_result[key1]).intersection(set(differnece_result[key2]))
                    for v in intersection:
                        multi_version[v] = multi_version.get(v,[]) + [key1,key2]
    
    
    for v in multi_version:
        multi_version[v] = list(set(multi_version[v]))
    

    if len(multi_version) > 0:
        print('error in multi_version:',multi_version)
        exit(1)

        for v in multi_version:
            key0 = multi_version[v][0]
            for index,keyn in enumerate(multi_version[v]):
                if index == 0:
                    continue
                if key0 in differnece_result and keyn in differnece_result:
                    differnece_result[key0] = differnece_result.get(key0,[]) + differnece_result[keyn]
                    differnece_result.pop(keyn)
        

    for key in differnece_result:
        value_list = differnece_result[key]
        sorted_versions = sorted(value_list, key=lambda v: list(map(int, v.split('.'))))
        differnece_result[key] = sorted_versions
    return resp,differnece_result



def version2diffset(version:str, base_dir = '', threshold = 0.9):
    resp = {}
    differnece_result = {}
    for root,ds,fs in os.walk(base_dir):
        for f in fs:
            full_path = os.path.join(root,f)
            if version in f:
                cmp_version = get_parent_directory(full_path)
                with open(full_path,'r') as rf:
                    content = rf.read()

                    if not errorInContent(content):
                        resp[cmp_version] = content
                    else:
                        print(cmp_version,'error content in probe {}'.format(version))

    
    for v in resp:
        find_flag = False
        for key in differnece_result:
            resp[v] = mask_text(resp[v])
            resp[key] = mask_text(resp[key])
            if similarity(resp[v],resp[key]) >= threshold:
                differnece_result[key] = differnece_result.get(key,[]) + [v]
                find_flag = True
        if not find_flag:
            differnece_result[v] = [v]

    multi_version = {}
    for key1 in differnece_result:
        for key2 in differnece_result:
            if key1 != key2:

                if len(set(differnece_result[key1]).intersection(set(differnece_result[key2]))) > 0:
                    intersection = set(differnece_result[key1]).intersection(set(differnece_result[key2]))
                    for v in intersection:
                        multi_version[v] = multi_version.get(v,[]) + [key1,key2]
    
    
    for v in multi_version:
        multi_version[v] = list(set(multi_version[v]))
    
    

    for v in multi_version:
        max_sim = 0
        max_key = ''
        for key in multi_version[v]:
            sim = similarity(resp[v],resp[key])
            if sim > max_sim:
                max_sim = sim
                max_key = key
        
        for key in multi_version[v]:
            if key != max_key:

                differnece_result[key].remove(v)


    for key in differnece_result:
        value_list = differnece_result[key]
        sorted_versions = sorted(value_list, key=lambda v: list(map(int, v.split('.'))))
        differnece_result[key] = sorted_versions
    return resp,differnece_result




def comp_set_small(vset,version):
    version = version.split('_')[0]
    for v in vset:
        if compare_versions(v,version) > 0:
            return False
    return True


def comp_set_big(vset,version):
    version = version.split('_')[0]
    for v in vset:
        if compare_versions(v,version) <= 0:
            return False
    return True


def not_valid_set(vset,version):
    version = version.split('_')[0]

    small_flag = False
    big_flag = False
    for v in vset:
        if compare_versions(v,version) > 0:
            small_flag = True
        if compare_versions(v,version) < 0:
            big_flag = True
    
    if small_flag and big_flag:
        return True
    return False

def select_can_split_probe(probe2diffsets):
    keys = []
    for probe_v in probe2diffsets:
        diffsets = probe2diffsets[probe_v]

        if len(diffsets) < 2:
            continue
        keys.append(probe_v)
    return keys


def select_self_probe(probe2diffsets):
    small_probes = {}
    big_probes = {}
    
    
    for probe_v in probe2diffsets:
        diffsets = probe2diffsets[probe_v]

        if len(diffsets) < 2:
            continue
        
        for diff_list in diffsets:
            if comp_set_small(diff_list,probe_v):
                small_probes[probe_v] = small_probes.get(probe_v,[]) + [diff_list]
                # print(probe_v,diff_list)
                # break
            if comp_set_big(diff_list,probe_v):
                # print(probe_v,diff_list)
                big_probes[probe_v] = big_probes.get(probe_v,[]) + [diff_list]
                # break
            if not_valid_set(diff_list,probe_v):
                # print(probe_v,diff_list)

                if probe_v in small_probes:
                    small_probes.pop(probe_v)
                if probe_v in big_probes:
                    big_probes.pop(probe_v)
                break   
            
            
    print('small_probes:',len(small_probes))
    print('big_probes:',len(big_probes))
    
    keys = list(small_probes.keys()) + list(big_probes.keys())
    keys = set(keys)
    print('keys:',keys, len(keys))
    return keys

def check_probe_diff_valid(probeSplitData:list):

    for i in range(len(probeSplitData)):
        for j in range(i+1,len(probeSplitData)):
            if len(probeSplitData[i].intersection(probeSplitData[j])) > 0:
                # print('error:',probeSplitData[i].intersection(probeSplitData[j]))
                return False
    return True




