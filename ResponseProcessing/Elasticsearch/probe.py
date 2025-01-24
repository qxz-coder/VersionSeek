# This script is used to process probe
import os,re,json
from response_process import similarity,mask_text


def compare_versions(version1, version2):
    
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


def errorInContent(content):
    errors = ["curl: (7) Failed to connect to localhost port 9200 after 0 ms: Couldn't connect to server",
            'curl: (56) Recv failure: Connection reset by peer',
            'curl: (3) URL using bad/illegal format or missing URL']
    
    errors = ["curl: (7)",
        'curl: (56)',
        'curl: (3)',
        'curl: (35)',
        'curl: (2)',
        'curl: (52)',]
    
    error_pattern = re.compile(r'curl: \(\d+\)')
    matches = error_pattern.findall(content)
    if matches:
        return True
        
    
    return False

def version2probe(valids:dict,version):
    return valids[version]

def get_parent_directory(path):
    if os.path.isfile(path):
        return os.path.basename(os.path.dirname(path))
    return os.path.basename(os.path.normpath(path))


def version2diffset(version:str, base_dir = 'xx/ElasticSearch/batchTestResultsV2'):
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
            if similarity(resp[v],resp[key]) > 0.9:
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
                
    return resp,differnece_result

def compare_strings(s1, s2):
    
    min_len = min(len(s1), len(s2))
    differences = []
    
    
    for i in range(min_len):
        if s1[i] != s2[i]:
            differences.append((i, s1[i], s2[i]))  

    
    if len(s1) > len(s2):
        differences.extend((i, s1[i], None) for i in range(min_len, len(s1)))
    elif len(s2) > len(s1):
        differences.extend((i, None, s2[i]) for i in range(min_len, len(s2)))
    
    return differences



def version2diffset_multiple(version:str, base_dir = 'xx/ElasticSearch/batchTestResultsV2',threshold = 0.9, one_hundred_flag=False):
    resp = {}
    differnece_result = {}
    for root,ds,fs in os.walk(base_dir):
        for f in fs:
            full_path = os.path.join(root,f)
            if f'{version}.txt' == f:
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
            if not one_hundred_flag:
                if similarity(mask_text(resp[v]),mask_text(resp[key])) > threshold:
                    differnece_result[key] = differnece_result.get(key,[]) + [v]
                    find_flag = True
            
            else:
                if mask_text(resp[v]) == mask_text(resp[key]):
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
    
    if one_hundred_flag:
        if len(multi_version) > 0:
            print('multi_version:',multi_version)
            exit()
    
    else:
        pass
    
    
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
                
    return resp,differnece_result



def comp_set_small(vset,version):
    version = version.split('_')[0] # 6.7.2_1 -> 6.7.2
    
    for v in vset:
        if compare_versions(v,version) > 0:
            return False
    return True


def comp_set_big(vset,version):
    version = version.split('_')[0] # 6.7.2_1 -> 6.7.2
    
    for v in vset:
        if compare_versions(v,version) <= 0:
            return False
    return True


def not_valid_set(vset,version):
    
    version = version.split('_')[0] # 6.7.2_1 -> 6.7.2
    
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
    can_split_probes = {}
    for probe_v in probe2diffsets:
        diffsets = probe2diffsets[probe_v]
        
        if len(diffsets) >=2:
            can_split_probes[probe_v] = diffsets
    return can_split_probes
    

def select_self_probe(probe2diffsets):
    small_probes = {}
    big_probes = {}
    
    
    for probe_v in probe2diffsets:
        # probe_v = key_v.split('_')[0]   # 6.7.2_1 -> 6.7.2
        diffsets = probe2diffsets[probe_v]
        
        if len(diffsets) < 2:
            continue
        
        for diff_list in diffsets:
            # if probe_v == '6.7.2':
            #     pass
            
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
            
            
            
    print('small_probes:',small_probes)
    print('big_probes:',big_probes)
    
    keys = list(small_probes.keys()) + list(big_probes.keys())
    keys = set(keys)
    print('keys:',keys, len(keys))
    return keys

def check_probe_diff_valid(probeSplitData:list):
    for i in range(len(probeSplitData)):
        for j in range(i+1,len(probeSplitData)):
            if len(probeSplitData[i].intersection(probeSplitData[j])) > 0:
                return False
    return True

    
    
    
