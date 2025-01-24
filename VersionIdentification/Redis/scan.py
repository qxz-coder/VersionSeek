# coding = utf-8
# This Script is used to transform the tree structure to scan script

import os, json, re
import traceback
import sys
sys.path.append('../../ResponseProcessing/Redis')
from buildtree import build_tree
from tree2scan import tree2scan
from greedy import split_version_by_greedy
from local_optima import local_optima
import socket
import traceback
import subprocess
import time
import datetime
from functools import partial
import schedule
import random

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



def full_scan(hostinfo, init_tree, probe_data, ctype="redis",auth_flag:str=None):

    filter_versions = ['6.2.9', '6.2.15', '3.2.13', '4.0.3']
    versions_file = 'versions'
    with open(versions_file, 'r') as file:
        init_versions = file.read().splitlines()
    init_versions = [x for x in init_versions if x not in filter_versions]

    conflict_number = 0
    conflict_relations = dict()
    conflict_limit = 3

    used_probes = []
    limit_number = 20
    scan_results = tree2scan(hostinfo,init_tree,ctype = ctype, probe_data=probe_data, conflict_relations=conflict_relations,look_path= [],auth_flag=auth_flag)


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
                    )
                else:
                    return [
                        "no new probe can used to distinguisded",
                        look_path,
                        remains_versions,
                        auth_flag
                    ]
            else:  
                return ["probe number exceed limit", look_path, remains_versions,auth_flag]

        else:
            return ["unknown error"]

    limit_number = 10 if conflict_number == 2 else 8

    vote_results = dict()
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
        
        scan_results = tree2scan(hostinfo, init_tree, probe_data=None, conflict_relations=None, look_path=[init_path],auth_flag=auth_flag)  
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
                            auth_flag=auth_flag
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


def schedule_job():
    plain_job()
    # schedule.every(6).hours.do(job, ctype)
    schedule.every(1).hours.do(partial(plain_job))

    while True:
        schedule.run_pending()
        time.sleep(1)  


def plain_job(debug=False):
    ctype = "redis"
    multi_hosts = ""
    save_file_path = ""
    offline_file_path = ""
    not_exist_hosts = []
    auth_flag = ""
    import time
    start_time = time.time()
    idx = 0
    for hostinfo in multi_hosts[:]:
        if hostinfo.count(":") > 1: 
            continue
        idx += 1
        off_fp = os.path.join(offline_file_path, hostinfo) 
        if os.path.exists(off_fp):
            continue
        base_dir = os.path.join(save_file_path, hostinfo + "/result.json")
        if debug:
            pass
        else:
            if os.path.exists(base_dir):
                continue

        ip, port = hostinfo.split(":")
        if is_port_open(ip, int(port)):
            try:
                test_command = ["redis-cli", "-h", ip, "-p", str(port), "INFO"]
                response = subprocess.run(
                    test_command, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    timeout=6
                )

                output = response.stdout.strip() if response.returncode == 0 else response.stderr.strip()
                if output.startswith("NOAUTH"):
                    auth_flag = "closed"
                elif output.startswith("DENIED"):
                    auth_flag = "deny"
                elif output == "Error: Connection reset by peer":
                    continue
                else:
                    auth_flag = "default"

                
                probe_data = get_data_from_json(
                    f"VersionSeek/Probes/Redis/probe_data_{auth_flag}.json"
                )
                new_probe_data = dict()
                for key in probe_data.keys():
                    new_list = []
                    for v_list in probe_data[key]:
                        v_set = set(v_list)
                        new_list.append(v_set)
                    new_probe_data[key] = new_list
                filter_versions = ['6.2.9', '6.2.15', '3.2.13', '4.0.3']

                versions_file = 'versions'
                with open(versions_file, 'r') as file:
                    versions = file.read().splitlines()
                versions = [x for x in versions if x not in filter_versions]
                init_tree, min_probes = generate_optimal_tree(new_probe_data, set(versions), [])


                base_dir = os.path.join(save_file_path, hostinfo)
                if not os.path.exists(base_dir):
                    os.makedirs(base_dir)
                print(f"start scan {hostinfo}")
                results = full_scan(hostinfo, init_tree, new_probe_data, ctype,auth_flag)
                
                if len(results) > 2 and len(results[2]) > 0:
                    results[2] = sorted(
                        results[2], key=lambda x: tuple(map(int, x.split(".")))
                    )
                print(results)
                with open(os.path.join(base_dir, "result.json"), "w") as f:
                    json.dump(results, f)
            except Exception as e:
                traceback.print_exc()
                print(f"RealWorld Case Error is :{e}")
            # exit()
        else:
            os.makedirs(off_fp)
            not_exist_hosts.append(hostinfo)
            print(f"{hostinfo} is not connected")

    end_time = time.time()
    #print((end_time - start_time)/10)

probe_sizes = 0
generate_probes_time = 0

def replan(hostinfo, auth_required, ctype="redis", debug=True, limit_probe=[]):
    service = ctype2service(ctype)
    if auth_required == 'need_auth':
        auth_flag = 'closed'
    elif auth_required == 'no_auth':
        auth_flag = 'default'
    else: auth_flag = 'deny'
    save_file_path = ""

    try:    
        probe_data = get_data_from_json(
                f"VersionSeek/Probes/Redis/probe_data_{auth_flag}.json"
            )
        new_probe_data = dict()
        for key in probe_data.keys():
            new_list = []
            for v_list in probe_data[key]:
                v_set = set(v_list)
                new_list.append(v_set)
            new_probe_data[key] = new_list
        filter_versions = ['6.2.9', '6.2.15', '3.2.13', '4.0.3']

        versions_file = 'versions'
        with open(versions_file, 'r') as file:
            versions = file.read().splitlines()
        versions = [x for x in versions if x not in filter_versions]
        s = time.perf_counter()
        init_tree, min_probes = generate_optimal_tree(new_probe_data, set(versions), [])
        e = time.perf_counter()
        global generate_probes_time
        generate_probes_time += e-s
        base_dir = os.path.join(save_file_path, hostinfo)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)
        results = full_scan(hostinfo, init_tree, new_probe_data, ctype,auth_flag)
        if len(results) > 2 and len(results[2]) > 0:
            results[2] = sorted(
                results[2], key=lambda x: tuple(map(int, x.split(".")))
            )
        global probe_sizes
        probe_sizes += len(results[1])
        print(results)
        with open(os.path.join(base_dir, "result.json"), "w") as f:
            json.dump(results, f)
    except Exception as e:
        traceback.print_exc()
        print(f"RealWorld Case Error is :{e}")


def get_average_time(data:dict, auth_type:str):
    hosts = data.get(auth_type, [])
    hosts = [h.replace('_', ':') for h in hosts]
    total_time = 0
    number = 10
    
    if len(hosts) < number:
        print(f"Not enough hosts to scan. Available hosts: {len(hosts)}")
        return
    
    selected_hosts = random.sample(hosts, number)
    
    times = 0
    
    for host in selected_hosts:
        ip, port = host.split(':')
        print(host)
        start = time.perf_counter()
        try:
            replan(host, auth_type, 'redis', True, [])
        except Exception as e:
            print(f"An error occurred: {e}")
            continue
        end = time.perf_counter()
        elapsed_time = end - start
        total_time += elapsed_time
        print(f"Elapsed time: {elapsed_time:.6f} seconds")
        times += 1
    
    if times > 0:
        average_time = total_time / times
        print(f"Scanning {times} servers using time {total_time:.6f} seconds, average time is {average_time:.6f} seconds")
    else:
        print("No servers were scanned.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 dynamicTreeDubbo.py [peroid|V1|debug]')
    para = sys.argv[1]

    if para == "peroid":
        schedule_job()
    elif para == "V1":
        plain_job()
    elif para == "debug":
        plain_job(True)
    elif para == 'get_time':
        data = get_data_from_json('')
        start = time.perf_counter()
        for auth_type in ['need_auth', 'no_auth','deny']:
            get_average_time(data, auth_type)
        end = time.perf_counter()
        print("total",(end-start-generate_probes_time)/probe_sizes)