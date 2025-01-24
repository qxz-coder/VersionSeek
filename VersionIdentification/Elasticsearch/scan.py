# coding = utf-8
# This Script is used to transform the tree structure to scan script

import os, json, re
import traceback
import sys
sys.path.append('../../ResponseProcessing/Elasticsearch')

from response_process import mask_text, similarity
from greedy import split_version_by_greedy
from local_optima import local_optima

from buildtree import build_tree
from tree2scan import tree2scan

import socket
import traceback
import subprocess
import time
import datetime
from functools import partial
import schedule
import sys

probe_data_fp = 'xx/ElasticSearch/scripts/probe_data.json'
response_dir = ''


def generate_optimal_tree(
    probe_data: dict, distinguished_versions: set, used_probes: list
):
    filter_probe_data = dict()

    keys = list(probe_data.keys())
    for key in keys:
        if key not in used_probes:
            filter_probe_data[key] = probe_data[key]

    not_split_versions = []  

    not_split_all_set_lists = []  

    not_split_all_probes = []  

    
    can_distinguised_data = dict()
    all_can_spilts = dict()
    for v in distinguished_versions:
        selected_probes, not_distinguished_set = split_version_by_greedy(
            filter_probe_data, v
        )
        if len(selected_probes) == 0:  
            not_split_versions.append(v)
            continue
        all_can_spilts[v] = selected_probes

        if len(not_distinguished_set) > 0:
            temp = not_distinguished_set.copy()
            temp.add(v)
            if temp not in not_split_all_set_lists:
                not_split_all_probes.extend(selected_probes)  #
                not_split_all_set_lists.append(temp)
            continue

        can_distinguised_data[v] = selected_probes

    
    split_all_versions = list(can_distinguised_data.keys())

    min_probes = local_optima(all_can_spilts, filter_probe_data)

    distinguished_versions = list(all_can_spilts.keys())
    # min_probes = set(min_probes).union(set(not_split_all_probes))
    
    print("not split all probes:", list(set(not_split_all_probes)))

    

    min_probes = list(min_probes)

    filter_data = {}
    for probe in filter_probe_data:
        if probe in min_probes:
            filter_data[probe] = filter_probe_data[probe]
    if len(min_probes) > 0:
        root = build_tree(
            filter_data,
            set(distinguished_versions),
            min_probes[0],
            set(distinguished_versions),
            {min_probes[0]},
            [],
        )
        return root.to_dict(), min_probes
    else:
        return dict(),list()







def full_scan(hostinfo,init_tree,probe_data, ctype="es",es_versions=None,auth_flag:str=None,one_hundred_flag=False):
    debug = False   
    conflict_number = 0
    conflict_relations = dict()
    conflict_limit = 3
    init_versions = es_versions
    
    
    used_probes = []
    limit_number= 20    
    scan_results = tree2scan(hostinfo,init_tree,ctype = ctype, probe_data=probe_data, conflict_relations=conflict_relations,look_path= [],auth_flag=auth_flag,one_hundred_flag=one_hundred_flag)
    
    
    
    if not debug:
        while True:
            
            if len(scan_results) > 0:
                
                if "command timeout" in scan_results[0]:
                    return scan_results
                

                if "conflict" in scan_results[0]:
                    
                    if len(conflict_relations) > conflict_number:
                        conflict_number = len(conflict_relations)
                    break  

                
                if "not matched" not in scan_results[0]:
                    return scan_results  

                
                
                temp_used_probes = [x.split("_r")[0][2:] for x in scan_results[1]]
                # temp_used_probes.append(invalid_probe_name)
                used_probes.extend(temp_used_probes)
                used_probes = list(set(used_probes))
                remains_versions = scan_results[2]
                look_path = scan_results[1]
                
                if len(used_probes) < limit_number:
                    new_tree, min_probes = generate_optimal_tree(
                        probe_data, remains_versions, used_probes
                    )
                    if len(min_probes) > 0:
                        scan_results = tree2scan(
                            hostinfo,
                            new_tree,
                            ctype,
                            probe_data=probe_data,
                            conflict_relations=conflict_relations,
                            look_path=look_path,
                            auth_flag=auth_flag,
                            one_hundred_flag=one_hundred_flag
                        )
                    else:
                        return [
                            "no new probe can used to distinguisded",
                            look_path,
                            remains_versions,
                        ]
                else:  
                    return ["probe number exceed limit", look_path, remains_versions]

            else:
                return ["unknown error"]

    if debug:
        conflict_number = 2
        conflict_relations['7.4.0_6'] = ['6.1.0_14']
        conflict_relations['6.1.0_14'] = ['7.4.0_6']


    
    limit_number = 10 if conflict_number == 2 else 8

    print('start conflict!!!')

    vote_results = dict()
    print(conflict_relations)
    
    ckeys = [x for x in conflict_relations.keys() if 'conflict_result' not in x]
    for head in ckeys[:conflict_limit]:
        used_probes = []  
        filter_conflict_probe = {
            x:probe_data[x] for x in probe_data if x not in conflict_relations[head]
        }
        remain_vsets = list(conflict_relations['conflict_result'][head])
        newly_init_versions = set(remain_vsets)
        
        init_tree, min_probes = generate_optimal_tree(
            filter_conflict_probe, newly_init_versions, [head]
        )
        init_path = f'p:{head}_r:{remain_vsets[0]}'
        
        scan_results = tree2scan(hostinfo, init_tree, probe_data=None, conflict_relations=None, look_path=[init_path],auth_flag=auth_flag,one_hundred_flag=one_hundred_flag)  
        while len(scan_results) > 0:
            if "not matched" not in scan_results[0]:
                vote_results[head] = scan_results
                break
            else:
                temp_used_probes = [x.split("_r")[0][2:] for x in scan_results[1]]
                used_probes.extend(temp_used_probes)
                used_probes = list(set(used_probes))
                look_path = scan_results[1]
                remains_versions = scan_results[2]
                
                if len(used_probes) < limit_number:
                    new_tree, min_probes = generate_optimal_tree(
                        probe_data, remains_versions, used_probes
                    )
                    if len(min_probes) > 0:
                        scan_results = tree2scan(
                            hostinfo,
                            new_tree,
                            ctype,
                            probe_data=None,
                            conflict_relations=None,
                            look_path=look_path,
                            auth_flag=auth_flag,
                            one_hundred_flag=one_hundred_flag
                        )
                    else:
                        vote_results[head] = [
                            "no new probe can used to distinguisded",
                            look_path,
                            remains_versions,
                        ]
                        break
                else:  
                    vote_results[head] = [
                        "probe number exceed limit",
                        look_path,
                        remains_versions,
                    ]
                    break
    print(vote_results)
    return major_vote_algorithm(vote_results)


def merge_not_failed_path(path1, path2):
    intersection = set(path1).intersection(set(path2))
    results = {v for v in intersection if 'failed_match' not in v}
    return results

def get_valid_length_of_probes(path: list):
    set_path = set(path)
    
    return len([x for x in set_path if 'failed_match' not in x])



def major_vote_algorithm(vote_results): 
    heads = list(vote_results.keys())
    if len(heads) == 2:
        length1 = get_valid_length_of_probes(vote_results[heads[0]][1])
        length2 = get_valid_length_of_probes(vote_results[heads[1]][1])
        if length1 > length2:
            return vote_results[heads[0]]
        else:
            return vote_results[heads[1]]

    max_votes = 0
    max_results = []

    
    for i in range(len(heads)):
        for j in range(i + 1, len(heads)):
            head1 = heads[i]
            head2 = heads[j]
            path1 = vote_results[head1][1]
            path2 = vote_results[head2][1]
            
            path1 = [x for x in path1 if 'failed_match' not in x]
            path2 = [x for x in path2 if 'failed_match' not in x]
            
            
            v1 = vote_results[head1][2]
            v2 = vote_results[head2][2]
            intersection = list(set(v1).intersection(set(v2)))
            # sort by version
            intersection = sorted(intersection, key=lambda x: tuple(map(int, x.split("."))))

            if len(intersection) > 0:
                new_path = path1 + path2
                new_path = list(set(new_path))
                new_results = ["merge two conflict", new_path, intersection]
                if max_votes < len(new_path):
                    max_votes = len(new_path)
                    max_results = new_results
            else:
                
                if len(path1) > len(path2):
                    if max_votes < len(path1):
                        max_votes = len(path1)
                        max_results = vote_results[head1]
                elif len(path1) < len(path2):
                    if max_votes < len(path2):
                        max_votes = len(path2)
                        max_results = vote_results[head2]
                else:  
                    versions1 = vote_results[head1][2]
                    versions2 = vote_results[head2][2]
                    if len(versions1) <= len(versions2):
                        if max_votes < len(path1):
                            max_votes = len(path1)
                            max_results = vote_results[head1]
                    else:
                        if max_votes < len(path2):
                            max_votes = len(path2)
                            max_results = vote_results[head2]

    new_reason = "conflict_major_vote"
    max_results[0] = new_reason
    return max_results


def merge_host_info(host_info: dict):
    all_host_infos = []
    for key in host_info:
        all_host_infos.extend(host_info[key].keys())
    all_host_infos = list(set(all_host_infos))
    return all_host_infos


def get_data_from_json(json_file: str):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data


def extract_all_ip_info_from_data(data: dict):
    matches = data["matches"]
    results = []
    for match in matches:
        ip = match["ip_str"]
        port = match["port"]
        results.append(f"{ip}:{port}")
    return results



def is_port_open(ip, port, timeout=3):
    try:
        
        result = subprocess.run(
            ["nc", "-zv", "-w", str(timeout), ip, str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        if result.returncode == 0:
            # print(f"Port {port} on {ip} is open.")
            return True
        else:
            # print(f"Port {port} on {ip} is closed or unreachable.")
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def fetch_content(ip, port):
    protocols = ['http', 'https']
    supported_protocol = None
    content = None
    auth_required = False
    for protocol in protocols:
        try:
            content = ''
            
            full_url = f"{protocol}://{ip}:{port}/?pretty=true&format=json"

            curl_command = ["curl", "-k", full_url] 
            
            result = subprocess.run(
                curl_command,
                text=True,
                capture_output=True,
                timeout=5
            )
            
            content = result.stdout + result.stderr
            curl_error_pattern = re.compile(r"curl: \(\d+\)")
            if curl_error_pattern.search(content):
                continue    
            else:
                supported_protocol = protocol
                mask_content = mask_text(content)   
                json_str = json.loads(mask_content)
                if 'error' in json_str and 'type' in json_str['error']:
                    if json_str['error']['type'] == 'security_exception':
                        auth_required = True             
                break
        except subprocess.TimeoutExpired:
            print(f"Timeout occurred for {protocol}")
        except Exception as e:
            print(f"Content format is Error,may be a honeypot")
            content = 'none' if content is None else content
            return 'unkonwn error', content, None
    return supported_protocol, content, auth_required

def check_port_status(ip, port):
    if is_port_open(ip, port):
        supported_protocol, content, auth_required = fetch_content(ip, port)
        if supported_protocol is not None:
            return supported_protocol, content, auth_required
        else:
            return 'unknown error', content, None
    else:
        return 'offline', None, None



def get_multi_results(dir_: str):
    filenames = os.listdir(dir_)
    results = []
    for filename in filenames:
        fp = os.path.join(dir_, filename)
        host_infos = get_data_from_json(fp)
        all_hosts = extract_all_ip_info_from_data(host_infos)
        results.extend(all_hosts)
    results = list(set(results))
    return results


def traverse_dir(dir_: str):
    results = []
    for root, dirs, files in os.walk(dir_):
        for filename in files:
            fp = os.path.join(root, filename)
            hostinfo = get_data_from_json(fp)
            all_host = extract_all_ip_info_from_data(hostinfo)
            results.extend(all_host)
    results = list(set(results))
    return results

def ctype2service(ctype):
    if ctype == "dubbo":
        return "Dubbo"
    elif ctype == "es":
        return "Elastic"
    elif ctype == 'redis':
        return 'Redis'

def traverse_dir(dir_: str):
    results = []
    for root, dirs, files in os.walk(dir_):
        for filename in files:
            fp = os.path.join(root, filename)
            hostinfo = get_data_from_json(fp)
            all_host = extract_all_ip_info_from_data(hostinfo)
            results.extend(all_host)
    results = list(set(results))
    return results


def prepare_data(auth_required):
    auth_flag = 'open' if not auth_required else 'closed'
    
    open_filter_probes = ['8.12.0_29']
    es_probe_fp = f'xx/es_probe_sets_{auth_flag}.json'
    probe_data_fp = f'xx/probe_data_{auth_flag}.json'
    response_base_dir = f'xx/batchTestOutput/{auth_flag}'
    
    es_versions = os.listdir(response_base_dir)
    
    es_versions = [x for x in es_versions if not x =='5.1.0']    
    
    if auth_flag == 'closed':
        filter_versions = ['6.1.0', '6.2.3', '6.5.4', '6.0.0', '6.3.2', '6.4.3', '6.2.1', '6.7.0', '6.1.3', '7.0.1', '6.1.4', '6.2.0', '6.6.2', '6.5.1', '6.0.1', '6.3.0', '7.0.0', '6.6.1', '6.7.2', '6.2.4', '6.5.3', '6.4.2', '6.5.0', '6.2.2', '6.6.0', '6.3.1', '6.1.2', '6.7.1', '6.4.1', '6.1.1', '6.4.0', '6.5.2']  
        es_versions = [x for x in es_versions if x not in filter_versions]
    
    
    es_probe_data = get_data_from_json(es_probe_fp)
    
    probe_data = get_data_from_json(probe_data_fp)
    
    new_probe_data = dict()
    
    for key in es_probe_data.keys():
        if auth_flag == 'open' and key in open_filter_probes:
            continue
        new_list = []
        for v_list in probe_data[key]:
            v_set = set(v_list)
            new_list.append(v_set)
        new_probe_data[key] = new_list
            
    return new_probe_data,es_versions



def replan(hostinfo, auth_required, ctype="es", debug=True, limit_probe=[]):
    
    service = ctype2service(ctype)
    basedir = f"xx/RealWorld/records/Shodan/peroid/{service}" 
    save_file_path = f"xx/RealWorld/results/es_final"
    if len(limit_probe):
        save_file_path = f"xx/RealWorld/results/es_timeout"
    
    
    try:    
        if not debug:
            base_dir = os.path.join(save_file_path, hostinfo)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            print(f"start scan {hostinfo}")
        probe_data,es_versions = prepare_data(auth_required)
        if len(limit_probe):
            probe_data = {x:probe_data[x] for x in limit_probe if x in probe_data}
            
        init_versions = es_versions
        init_tree, min_probes = generate_optimal_tree(probe_data, set(init_versions), [])
        auth_flag = 'closed' if auth_required else 'open'
        
        results = full_scan(hostinfo, init_tree, probe_data, ctype, es_versions=es_versions, auth_flag=auth_flag, one_hundred_flag=True) 
        
        if len(results) > 2 and len(results[2]) > 0:
            try:
                results[2] = sorted(
                    results[2], key=lambda x: tuple(map(int, x.split(".")))
                )
            except ValueError as e:
                traceback.print_exc()
                # 
            
            
            results.append(auth_flag)
            
            if debug:
                # pass
                print(results)
            else:
                # pass
                # print(results)
                with open(os.path.join(base_dir, "result.json"), "w") as f:
                    json.dump(results, f)
    except Exception as e:
        traceback.print_exc()
        # 
     
     




def job_one(hostinfo:str):
    ctype = "es"
    service = ctype2service(ctype)
    offline_file_path = f"xx/RealWorld/offline"
    unknown_file_path = f"xx/RealWorld/unknown"
    results_file_path = f'xx/RealWorld/results/es_final/'
    
    off_fp = os.path.join(offline_file_path, hostinfo)
    unknown_full_fp = os.path.join(unknown_file_path, hostinfo, 'error_content.txt')
    
    save_fp = os.path.join(results_file_path, hostinfo, 'result.json')
    
    if os.path.exists(off_fp) or os.path.exists(unknown_full_fp) or os.path.exists(save_fp):
        return 
    
    # print(unknown_full_fp)
    
    ip, port = hostinfo.split(":")
    supported_protocol, content, auth_required = check_port_status(ip, int(port))
    # print(supported_protocol)
    if supported_protocol in ['http', 'https']:
        
        replan(hostinfo, auth_required, 'es', False, [])
    elif supported_protocol == 'offline':
        
        os.makedirs(off_fp)
    elif supported_protocol == 'unkonwn error':
        # print(111)
        unknown_fp = os.path.join(unknown_file_path, hostinfo)  
        os.makedirs(unknown_fp)
        error_content = content
        save_fp = os.path.join(unknown_fp, 'error_content.txt')
        with open(save_fp, 'w') as f:
            f.write(error_content)
        # print('save fp', save_fp)
            
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan.py hostinfo")
        exit()
    para = sys.argv[1]
    print(123)
    # job_one(para)