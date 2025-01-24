import os,re,json
import sys
import time
import sys
sys.path.append('../../Deployment/Elasticsearch')

from deploy import get_docker_install_command,uninstall_docker,pre_install_docker,get_docker_install_command_with_auth

from greedy import *

from command import get_test_command_from_llm,safe_execute_command_long,safe_execute_command,filter_invalid_command,sanity_command,get_test_command_from_llm_en,get_test_command_from_llm_en_multiple
from probe import select_can_split_probe,version2diffset_multiple
from local_optima import local_optima
from buildtree import *

from command import upgrade_command

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

# global_all_commands = {}
valids = {}

def get_all_version(base_dir = '',limit_versions = []):       # save test versions
    results = {}
    versions = []
    for root,ds,fs in os.walk(base_dir):
        for d in ds:
            versions.append(d)
    
    if len(limit_versions) > 0:
        versions = limit_versions
    
    for version in versions:
        minor_version = '.'.join(version.split('.')[:-1])
        if minor_version not in results:
            results[minor_version] = []
        results[minor_version].append(version)
    return versions,results
    
    

def test_one_prev(version,all_commands): 
    # global_all_commands
    save_dir = 'xx'+version        # 
    if os.path.exists(save_dir):
        return 
    else:
        os.makedirs(save_dir)
    get_docker_install_command(version)

    
    for ver_number in all_commands:
        # if ver_number == version:
        #     continue
        save_fp = f'{save_dir}/{ver_number}.txt'
        
        if os.path.exists(save_fp):
            with open(save_fp,'r') as rrf:
                content = rrf.read()
            if errorInContent(content):
                pass
            else:
                continue
        
        test_command = all_commands[ver_number]
        out,err = safe_execute_command(test_command)
        
        while True:
            if errorInContent(err.decode('utf-8')):
                time.sleep(5)
                out,err = safe_execute_command(test_command)
            
            if 'curl: (3) URL using bad/illegal format or missing URL' in err.decode('utf-8'):
                break
            
            else:
                break
        
        with open(f'{save_dir}/{ver_number}.txt','w') as f:

            content = 'out is:\n' + out.decode('utf-8') + '\n\n\n' + 'error is:\n' + err.decode('utf-8')
            f.write(content)
        
        time.sleep(3)    
        
    uninstall_command = uninstall_docker(version)
    safe_execute_command(uninstall_command)
    
    time.sleep(5)

def test_one_current(version,all_commands,save_fp = '',auth_flag:str=None): 
    
    # global_all_commands
    save_dir = os.path.join(save_fp,version)
    if os.path.exists(save_dir):
        # pass
        # check number of files
        files = os.listdir(save_dir)
        if len(files)<574:
            pass
        else:
            return
    else:
        os.makedirs(save_dir)
    
    info = f'testing:{version}'
    
    pre_install_docker()
    
    
    # install with docker
    install_command = get_docker_install_command_with_auth(version,auth_flag=auth_flag)
    
    if install_command is None:
        print(f'error in install {version}!')
        return
    
    
    # safe_execute_command_long(install_command)
    out,err = safe_execute_command_long(install_command)
    if "See 'docker run --help'" in err.decode('utf-8'):
        return 
    # print(out,err)
    # exit()
    time.sleep(35) 
    try:
        for ver_number in all_commands:
            # if ver_number == version:
            #     continue
            save_fp = f'{save_dir}/{ver_number}.txt'
            
            if os.path.exists(save_fp):
                with open(save_fp,'r') as rrf:
                    content = rrf.read()
                if errorInContent(content):
                    os.remove(save_fp)
                    pass
                else:
                    continue
            
            test_command = all_commands[ver_number]
            
            test_command = upgrade_command(test_command,version,open_flag=auth_flag) 
            
            out,err = safe_execute_command(test_command)
            
            loop_times = 5
            while loop_times > 0:
                if errorInContent(err.decode('utf-8')):
                    if 'curl: (3) URL using bad/illegal format or missing URL' in err.decode('utf-8'):
                        break
                    # print(err.decode('utf-8'))
                    loop_times-=1
                    time.sleep(2)   
                    out,err = safe_execute_command(test_command)
                else:
                    break
            
            if not errorInContent(err.decode('utf-8')):
                with open(f'{save_dir}/{ver_number}.txt','w') as f:

                    content = 'out is:\n' + out.decode('utf-8') + '\n\n\n' + 'error is:\n' + err.decode('utf-8')
                    f.write(content)
            
    except Exception as e:
        pass
    uninstall_command = uninstall_docker(version)
    safe_execute_command(uninstall_command)
    time.sleep(2)
    
def generate_valid_command(versions:list):
    # global valids
    # versions,responses = get_all_version()
    for v in versions:
        command = get_test_command_from_llm(v)
        if filter_invalid_command(command):
            command = sanity_command(command)
            valids[v] = command
    
    return valids


def generate_valid_command_en(versions:list,base_fp = ''):
    # global valids
    # versions,responses = get_all_version()
    for v in versions:
        command = get_test_command_from_llm_en(v,base_fp)
        if filter_invalid_command(command):
            command = sanity_command(command)
            valids[v] = command
    
    return valids




def read_file(file_path:str,file_type:str):
    if file_type == 'json':
        with open(file_path,'r') as f:
            return json.load(f)
    else:
        with open(file_path,'r') as f:
            return f.read()

def generate_valid_command_en_new(versions:list,base_fp = ''):
    not_valid_comand_count = 0
    
    all_command_file_count = 0
    
    valid_commands = {}
    for v in versions:
        index_comands = get_test_command_from_llm_en_multiple(v,base_fp)
        
        all_command_file_count += len(index_comands)
        
        for probe_index in index_comands:
            command = index_comands[probe_index]
            if filter_invalid_command(command):
                command = sanity_command(command)
                valid_commands[probe_index] = command
            else:
                not_valid_comand_count+=1
    print(f'not valid command count:{not_valid_comand_count}')
    print(f'all command file count:{all_command_file_count}')
    
    return valid_commands



def workflow(test_type):

    test_flag = 'real_world'
    probe_versions,valid_commands = test_large_case()
    test_versions = read_file('','json')
    not_curl_commands = dict()
    
    new_valids = dict()
    for key in valid_commands:
        if test_flag!='local':  
            put_pattern = re.compile(r'-X\s*PUT|DELETE')
            if put_pattern.search(valid_commands[key]):
                continue
        
        if 'curl' not in valid_commands[key]:
            not_curl_commands[key] = valid_commands[key]
        else:
            new_valids[key] = valid_commands[key]
    
    special_commands = dict()
    for key in new_valids:
        if 'curl' not in new_valids[key][:4]:
            special_commands[key] = new_valids[key]
    
    
    
    need_filter_probe = ['8.14.0_20', '8.10.0_1', '8.14.0_35', '5.4.1_1', '8.6.0_9', '8.4.0_11', '6.6.0_18', '8.13.0_80', '8.8.0_8', '8.1.2_1', '8.7.0_22', '7.6.2_6']
    not_valid_probes = ['8.11.4_3']
    
    post_probes = ['8.13.3_1', '8.13.3_4', '7.11.0_8', '8.0.0_39', '8.0.0_42', '8.0.0_44', '8.0.0_45', '7.7.1_10', '7.17.10_1', '7.6.2_1', '6.7.0_24', '6.7.0_29', '6.7.0_60', '8.6.0_2', '8.12.0_17', '8.12.0_30', '8.12.0_32', '8.12.0_3', '8.12.0_42', '8.12.0_48', '8.12.0_52', '8.12.0_55', '8.12.0_61', '8.12.0_9', '7.0.1_0', '7.0.1_12', '8.4.0_10', '8.4.0_6', '6.2.0_7', '7.17.6_0', '7.17.6_1', '8.1.1_0', '8.1.0_3', '8.2.0_25', '8.2.0_26', '8.7.0_34', '8.7.0_5', '8.7.1_0', '8.11.0_23', '8.11.0_39', '8.11.0_4', '8.11.0_59', '8.11.0_64', '8.11.0_70', '8.11.0_7', '7.0.0_13', '7.0.0_140', '7.0.0_19', '7.0.0_23', '7.0.0_37', '7.0.0_61', '7.0.0_87', '8.14.0_0', '8.14.0_12', '8.14.0_18', '8.14.0_28', '8.14.0_29', '8.14.0_33', '8.14.0_34', '8.14.0_3', '8.14.0_45', '8.14.0_46', '8.14.0_55', '8.14.0_63', '8.14.0_64', '8.14.0_65', '8.14.0_6', '8.14.0_7', '7.7.0_38', '7.7.0_39', '7.7.0_6', '7.9.3_3', '7.4.0_1', '7.13.0_10', '7.13.0_4', '8.11.3_1', '7.14.0_0', '7.14.0_8', '8.8.0_14', '8.8.0_16', '8.10.0_0', '8.10.0_12', '8.10.0_3', '8.13.0_22', '8.13.0_23', '8.13.0_25', '8.13.0_43', '8.13.0_46', '8.13.0_52', '8.13.0_54', '8.13.0_71', '8.13.0_73', '7.9.0_0', '7.9.0_14', '7.9.0_17', '6.5.0_37', '6.5.0_50', '6.6.0_100', '6.6.0_73', '6.6.0_84', '7.12.1_5', '7.6.0_37']
    
    
    keys = list(new_valids.keys())
    
    for command in keys:
        if command in need_filter_probe or command in not_valid_probes or command in post_probes or '/_cat/indices' in new_valids[command] or '_search_shards' in new_valids[command]:
            del new_valids[command]
    
    
    
    if test_type == 'deploy':
        command_results_fp = ''  
        start_time = time.time()
        for version in test_versions:


            test_one_current(version,new_valids,command_results_fp,auth_flag='closed')
        
        end_time = time.time()
        test_length = len(test_versions)
        command_length = len(new_valids)
        print(len(new_valids))
        
        exit()
    
    elif test_type == 'probe':
        # auth_flag = 'open'
        # auth_flag = 'default'
        auth_flag = 'closed'
        command_results_fp = 'xx/{}'.format(auth_flag)
    
    else:
        print('error test_type!')
        exit(1)
    
    start_time = time.time()
    
    
    one_hundred_flag = True
    
    filter_probe_lists = ['8.7.0_13']
    debug = False
    if debug:
        probe2diffsets = {}
        base_fp = command_results_fp
        for probe_v in new_valids:
            threshold = 0.9
            print('current_probe is ',probe_v)        
            resp,diff = version2diffset_multiple(probe_v,base_fp, threshold, one_hundred_flag)
            # print(resp)
            # print(diff)
            # diff -> set list
            diff_set_list = []
            for k in diff:
                diff_set_list.append(set(diff[k]))
            probe2diffsets[probe_v] = diff_set_list
            # break
        # print(probe2diffsets)

        self_probe = select_can_split_probe(probe2diffsets) 
        
        probe_data = dict()
        for probe_version in self_probe:
            probe_data[probe_version] = probe2diffsets[probe_version]

    
        save_data = {}
        for probe in probe_data:
            save_data[probe] = []
            for v_sets in probe_data[probe]:
                list_ = list(v_sets)
                sort_list = sorted(list_, key=lambda x: tuple(map(int, x.split("."))))
                
                save_data[probe].append(sort_list)
        
        
        with open(f'xx/probe_data_{auth_flag}.json','w') as f:  # save probe_data_info to json
            json.dump(save_data,f)
        
        exit()
    
    
    if debug:
        exit()
    
    with open(f'xx/probe_data_{auth_flag}.json','r') as f:
        probe_data = json.load(f)
    

    
    
    open_neeed_filter_probes = ['6.6.0_96','6.5.0_60','8.2.0_7','5.6.0_11','7.16.0_8','6.5.0_79','6.6.0_39','7.3.0_26','7.0.0_46','5.0.1_3','6.6.0_28','8.14.0_19','7.7.0_24','6.2.4_0']
    closed_need_filter_probes = ['5.2.0_16','8.7.0_3','7.17.1_3','7.0.0_169','6.7.0_39','7.4.1_3','8.12.0_29','7.5.2_2'] 
    
    
    filter_probes = []
    if auth_flag == 'open':
        filter_probes = open_neeed_filter_probes
        for probe_v in probe_data:
            length = len(probe_data[probe_v])
            if length>16 or length in [10,12]:
                filter_probes.append(probe_v)
        
    elif auth_flag == 'closed':
        filter_probes = closed_need_filter_probes
        for probe_v in probe_data:
            length = len(probe_data[probe_v])
            if length<=2 or length>=7:
                filter_probes.append(probe_v)
    
    
    for key in probe_data.keys():
        new_list = []
        for v_list in probe_data[key]:
            v_set = set(v_list)
            new_list.append(v_set)
        probe_data[key] = new_list
    
    need_filter_probe = ['8.14.0_20', '8.10.0_1', '8.14.0_35', '5.4.1_1', '8.6.0_9', '8.4.0_11', '6.6.0_18', '8.13.0_80', '8.8.0_8', '8.1.2_1', '8.7.0_22', '7.6.2_6']
    not_valid_probes = ['8.11.4_3']
    
    
    post_probes = ['8.13.3_1', '8.13.3_4', '7.11.0_8', '8.0.0_39', '8.0.0_42', '8.0.0_44', '8.0.0_45', '7.7.1_10', '7.17.10_1', '7.6.2_1', '6.7.0_24', '6.7.0_29', '6.7.0_60', '8.6.0_2', '8.12.0_17', '8.12.0_30', '8.12.0_32', '8.12.0_3', '8.12.0_42', '8.12.0_48', '8.12.0_52', '8.12.0_55', '8.12.0_61', '8.12.0_9', '7.0.1_0', '7.0.1_12', '8.4.0_10', '8.4.0_6', '6.2.0_7', '7.17.6_0', '7.17.6_1', '8.1.1_0', '8.1.0_3', '8.2.0_25', '8.2.0_26', '8.7.0_34', '8.7.0_5', '8.7.1_0', '8.11.0_23', '8.11.0_39', '8.11.0_4', '8.11.0_59', '8.11.0_64', '8.11.0_70', '8.11.0_7', '7.0.0_13', '7.0.0_140', '7.0.0_19', '7.0.0_23', '7.0.0_37', '7.0.0_61', '7.0.0_87', '8.14.0_0', '8.14.0_12', '8.14.0_18', '8.14.0_28', '8.14.0_29', '8.14.0_33', '8.14.0_34', '8.14.0_3', '8.14.0_45', '8.14.0_46', '8.14.0_55', '8.14.0_63', '8.14.0_64', '8.14.0_65', '8.14.0_6', '8.14.0_7', '7.7.0_38', '7.7.0_39', '7.7.0_6', '7.9.3_3', '7.4.0_1', '7.13.0_10', '7.13.0_4', '8.11.3_1', '7.14.0_0', '7.14.0_8', '8.8.0_14', '8.8.0_16', '8.10.0_0', '8.10.0_12', '8.10.0_3', '8.13.0_22', '8.13.0_23', '8.13.0_25', '8.13.0_43', '8.13.0_46', '8.13.0_52', '8.13.0_54', '8.13.0_71', '8.13.0_73', '7.9.0_0', '7.9.0_14', '7.9.0_17', '6.5.0_37', '6.5.0_50', '6.6.0_100', '6.6.0_73', '6.6.0_84', '7.12.1_5', '7.6.0_37']
    
    need_to_filter_probes = ['7.11.0_11','7.7.1_14']
    

    need_filter_versions = []
    
    new_probe_data = dict()
    for probe in probe_data:
        if probe not in need_filter_probe and probe not in not_valid_probes and probe not in need_to_filter_probes and probe not in filter_probes and probe in new_valids:
            new_probe_data[probe] = probe_data[probe]
    probe_data = new_probe_data
    
    
    save_data = {}
    for probe in probe_data:
        save_data[probe] = []
        for v_sets in probe_data[probe]:
            list_ = list(v_sets)
            sort_list = sorted(list_, key=lambda x: tuple(map(int, x.split("."))))
            
            save_data[probe].append(list(v_sets))
    
    with open(f'xx/probe_data_{test_type}.json','w') as f:  # save probe_data_info to json
        json.dump(save_data,f)
    
    
    
    # save probe to json
    probe_dicts = dict()
    for key in probe_data.keys():
        probe_dicts[key] = new_valids[key]
        
    with open(f"xx/es_probe_sets_{auth_flag}.json", "w") as wf:
        json.dump(probe_dicts,wf)
    
    not_distinguished_set_list = []
    
    not_split_versions = [] 
    
    can_distinguised_data = dict()
    
    all_split_data = dict()

    
    not_split_all_probes = []
    

    
    print('probe_data:',len(probe_data))
    keys = list(probe_data.keys())
    for version in keys:
        if version not in new_valids:
            del probe_data[version]
    
    comp_versions = os.listdir(command_results_fp)
    other_versions = []
    for v in comp_versions:
        selected_probes,not_distinguished_set = split_version_by_greedy(probe_data,v)
        if len(selected_probes) == 0:   
            not_split_versions.append(v)
            continue
        all_split_data[v] = selected_probes
        
        if len(not_distinguished_set) > 0:
            temp = not_distinguished_set.copy()
            temp.add(v)
            temp = temp.difference(set(need_filter_versions))
            other_versions.append(v)
            
            if temp not in not_distinguished_set_list:
                not_split_all_probes.extend(selected_probes)    # 
                not_distinguished_set_list.append(temp)
            continue
        else:
            can_distinguised_data[v] = selected_probes
    
    print('len of other_versions:',len(other_versions))
    print('len of all_split_data:',len(all_split_data))
    

    all_split_data = dict(sorted(all_split_data.items(), key=lambda v: tuple(map(int, v[0].split(".")))))
    print('all_split_data',all_split_data)
    
    
    print(can_distinguised_data)

    all_split_keys = list(all_split_data.keys())
    all_split_keys = sorted(all_split_keys, key=lambda x: tuple(map(int, x.split("."))))
    sort_split_data = dict()
    for k in all_split_keys:
        sort_split_data[k] = all_split_data[k]

    
    temp_results = []
    for sets in not_distinguished_set_list:
        temp_results.extend(list(sets))
        
    temp_results = list(set(temp_results))
    
    print('not distinguished set lists:',not_distinguished_set_list,len(not_distinguished_set_list),len(temp_results))
    
    print('not_split_versions: ',not_split_versions,len(not_split_versions))
    
    
    split_results = []
    not_distinguished_lists = []
    for not_dis_set in not_distinguished_set_list:
        not_dis_list = list(not_dis_set)
        sorted_lists = sorted(not_dis_list, key=lambda v: tuple(map(int, v.split("."))))
        split_results.append(sorted_lists)
        
        not_distinguished_lists.extend(sorted_lists)
    
    print("split results: ", split_results, len(split_results))
    
    distinguished_lists = list(can_distinguised_data.keys())

            
    print('can completely distinguised versions is: ',len(distinguished_lists))
    

    min_probes = local_optima(all_split_data,probe_data)

    min_probes = list(set(min_probes))
    print('not split all probes:',list(set(not_split_all_probes)))
    
    end_time = time.time()
    



if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python workflow.py test_type')
        exit()
    
    test_type = sys.argv[1]
    print(123)
    # workflow(test_type)
    
    
    
