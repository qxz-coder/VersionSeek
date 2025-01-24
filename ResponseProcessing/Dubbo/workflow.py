import os, json, requests, time, re
from func_timeout import func_set_timeout
import func_timeout, subprocess
from probe import (
    version2diffsetV2,
    select_can_split_probe
)
from greedy import split_version_by_greedy
from buildtree import *
from local_optima import local_optima

from buildtree import build_tree, save_tree_to_json

import sys
sys.path.append('../../Deployment/Dubbo')
from deploy import test_one_newly

# step0: get_all_probe
# step1 : deploy
# step2 : test
# step3 : diff results
# step4 : mini probes
# step5 :

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

def get_valid_versions():
    base_dir = "" # path for save release
    versions = []
    for root, ds, fs in os.walk(base_dir):
        for f in fs:
            v = f[6:-5]
            if v.count(".") == 2:
                if compare_versions(v, "2.5.4") > 0:    
                    versions.append(v)

    return versions

validCommands = {}
def simplify_probe_data(probe_data:dict,all_versions:set):
    new_probe_data = dict()
    for probe,version_sets in probe_data.items():
        new_version_sets = []
        for version_set in version_sets:
            new_version_set = version_set.intersection(all_versions)
            if new_version_set:
                new_version_sets.append(new_version_set)
        if new_version_sets:
            new_probe_data[probe] = new_version_sets
    return new_probe_data


def newly_workflow(deploy_flag = False):
    versions = get_valid_versions()
    filtered_versions = ['2.6.0','2.7.0', '2.7.1', '2.7.2', '2.7.3', '2.7.4', '2.7.5','3.2.14', '3.2.15'] # not deployable versions
    
    probe_save_fp = 'xx'
    
    # security_flag = 'enabled'
    security_flag = 'default'
    
    with open(probe_save_fp,'r') as f:
        valid_commands = json.load(f)
    
    base_save_fp = f"xx/{security_flag}"
    
    if deploy_flag:
    # '''
        for version in versions:
            if version in filtered_versions:    
                continue
            test_one_newly(version,valid_commands,base_save_fp,little_flag=False,security_flag=security_flag)
    # exit()
    # '''
    # versions = ['3.2.6','3.2.7']
    
    # 100% need to filter
    f_probes = ['index_22_','index_14_']
    
    
    start_time = time.time()
    probe2diffsets = {}
    base_fp = base_save_fp
    for index,command in enumerate(valid_commands):
        resp, diff = version2diffsetV2(index, base_fp, threshold=1)
        fname = 'index_{}_'.format(index)
        # print(resp)
        # print(diff)
        # diff -> set list
        diff_set_list = []
        for k in diff:
            diff_set_list.append(set(diff[k]))
            
        # sort diff_set_list
        # compare_versions = lambda x: tuple(map(int, x.split(".")))
        # diff_set_list = sorted(diff_set_list, key=lambda x: compare_versions(list(x)[0]))
        
        probe2diffsets[fname] = diff_set_list
        # break
    # print(probe2diffsets)
    # print(probe2diffsets)

    # self_probe = select_self_probe(probe2diffsets)
    
    self_probe = select_can_split_probe(probe2diffsets)


    probe_data = dict()
    for version in self_probe:
        if version in f_probes:
            continue
        
        probe_data[version] = probe2diffsets[version]
        # print(version,probe2diffsets[version])
        # valid_flag = check_probe_diff_valid(probe2diffsets[version])
        # if not valid_flag:
        #     print('invalid:',version, probe2diffsets[version])
        # exit()
    # exit()

    save_data = {}
    for probe in probe_data:
        save_data[probe] = []
        for v_sets in probe_data[probe]:
            list_ = list(v_sets)
            sort_list = sorted(list_, key=lambda x: tuple(map(int, x.split("."))))
            save_data[probe].append(sort_list)


    with open(f'{probe_save_fp}/dubbo_probe_data_{security_flag}.json','w') as f:
        json.dump(save_data,f)

    not_distinguished_set_list = []

    not_split_versions = []  # not split versions

    can_distinguised_data = dict()
    not_split_all_probes = []

    all_split_data = dict()

    filtered_versions = ['2.6.0','2.7.0', '2.7.1', '2.7.2', '2.7.3', '2.7.4', '2.7.5','3.2.14', '3.2.15', '3.1.1','3.1.2']
    

    versions = [v for v in versions if v not in filtered_versions]
    for v in versions:
        selected_probes, not_distinguished_set = split_version_by_greedy(probe_data, v)
        if len(selected_probes) == 0:  # 
            not_split_versions.append(v)
            continue
        all_split_data[v] = selected_probes
        if len(not_distinguished_set) > 0:
            temp = not_distinguished_set.copy()
            temp.add(v)
            temp = temp.difference(set(filtered_versions))
            
            if temp not in not_distinguished_set_list:
                not_distinguished_set_list.append(temp)
                not_split_all_probes.extend(selected_probes)
            continue

        can_distinguised_data[v] = selected_probes

    print(
        "not distinguished set lists:",
        not_distinguished_set_list,
        len(not_distinguished_set_list),
        len(versions)
    )

    # sort by compare_versions

    not_split_versions = sorted(
        not_split_versions, key=lambda v: tuple(map(int, v.split(".")))
    )

    print("not_split_versions: ", not_split_versions, len(not_split_versions))

    print('can_distinguised_data:',can_distinguised_data)
    split_results = []


    not_distinguished_lists = []
    for not_dis_set in not_distinguished_set_list:
        not_dis_list = list(not_dis_set)
        
        sorted_lists = sorted(not_dis_list, key=lambda v: tuple(map(int, v.split("."))))
        split_results.append(sorted_lists)
        
        not_distinguished_lists.extend(sorted_lists)

    print("split results: ", split_results, len(split_results))


    distinguished_lists = []
    for v in versions:
        if v not in not_distinguished_lists and v not in not_split_versions:
            distinguished_lists.append(v)

    
    start_time = time.time()
    
    print('all_split_data:',all_split_data)
    
    # min_probes.extend(not_split_all_probes)
    
    min_probes = local_optima(all_split_data,probe_data)
    
    min_probes = list(set(min_probes))
    # print(not_split_all_probes)
    
    print('not split all probes:',list(set(not_split_all_probes)))
    # exit()
    
    
    distinguished_lists = list(all_split_data.keys())
    probe_sets = dict()
    for v in min_probes:
        index = int(v.split('_')[1])
        probe_sets[v] = valid_commands[index]        
    # probe_sets = {v:new_valids[v] for v in min_probes}
    
    with open(f'xx/real_used_probes_{security_flag}.json','w') as f:
        json.dump(probe_sets,f)
    
    # '''
    filter_data = {}
    for probe in probe_data:
        if probe in min_probes:
            filter_data[probe] = probe_data[probe]
    
    filter_data = simplify_probe_data(filter_data, set(distinguished_lists))
    # print(distinguished_lists)
    # print(filter_data)
    # exit()
    root = build_tree(filter_data, set(distinguished_lists), min_probes[0], set(distinguished_lists), {min_probes[0]}, [])
    save_tree_to_json(root, f'tree_all_dubbo_{security_flag}.json')


if __name__ == "__main__":
    newly_workflow(False)

    



