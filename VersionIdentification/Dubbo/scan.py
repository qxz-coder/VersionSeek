# coding = utf-8
# This Script is used to transform the tree structure to scan script

import os, json, re
import traceback
import sys
sys.path.append('../../ResponseProcessing/Dubbo')

from greedy import split_version_by_greedy
from local_optima import local_optima
from lark_notice import notice
from buildtree import build_tree
from tree2scan import tree2scan

import traceback
import subprocess
import sys
from itertools import groupby

def versions_to_ranges(versions):
    def group_by_major_minor(version):
        return ".".join(version.split(".")[:2])

    def find_ranges(group):
        group = sorted(map(lambda v: tuple(map(int, v.split("."))), group))
        ranges = []
        start = group[0]
        prev = group[0]

        for current in group[1:]:
            if current[2] != prev[2] + 1:  
                if start == prev:
                    ranges.append(f"{'.'.join(map(str, start))}")
                else:
                    ranges.append(
                        f"{'.'.join(map(str, start))}-" f"{'.'.join(map(str, prev))}"
                    )
                start = current
            prev = current

        if start == group[-1]:
            ranges.append(f"{'.'.join(map(str, start))}")
        else:
            ranges.append(
                f"{'.'.join(map(str, start))}-" f"{'.'.join(map(str, group[-1]))}"
            )
        return ranges

    grouped_versions = groupby(
        sorted(versions, key=lambda v: tuple(map(int, v.split(".")))),
        group_by_major_minor,
    )

    result = []
    for _, group in grouped_versions:
        result.extend(find_ranges(list(group)))

    return ", ".join(result)

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


def full_scan(hostinfo, init_tree, probe_data, ctype="dubbo"):
    debug = False
    filter_versions = [
        "2.6.0",
        "2.7.0",
        "2.7.1",
        "2.7.2",
        "2.7.3",
        "2.7.4",
        "2.7.5",
        "3.2.14",
        "3.2.15",
        "3.1.1",
        "3.1.2",
    ]

    init_versions = get_valid_versions()
    init_versions = [x for x in init_versions if x not in filter_versions]

    conflict_number = 0
    conflict_relations = dict()
    conflict_limit = 3

    used_probes = []
    limit_number = 15
    scan_results = tree2scan(
        hostinfo,
        init_tree,
        probe_data=probe_data,
        conflict_relations=conflict_relations,
        look_path= []
    )

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


    limit_number = 10 if conflict_number == 2 else 5

    print('start conflict!!!')
    vote_results = dict()
    print(conflict_relations)
    # ckeys = list(conflict_relations.keys())
    ckeys = [x for x in conflict_relations.keys() if 'conflict_result' not in x]
    for head in ckeys[:conflict_limit]:
        used_probes = []  
        filter_conflict_probe = {
            x:probe_data[x] for x in probe_data if x not in conflict_relations[head]
        }
        
        remain_vsets = list(conflict_relations['conflict_result'][head])
        newly_init_versions = set(remain_vsets)
        
        init_tree, min_probes = generate_optimal_tree(
            filter_conflict_probe, set(init_versions), [head]
        )
        
        init_path = f'p:{head}_r:{remain_vsets[0]}'
        
        scan_results = tree2scan(hostinfo, init_tree, probe_data=None, conflict_relations=None, look_path=[init_path]) 
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
            
            
            # intersection = merge_not_failed_path(path1, path2)
            # intersection = set(path1).intersection(set(path2))
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


def prepare_probe_data():
    probe_data = get_data_from_json(
        "../../Probes/Dubbo/dubbo_probe_data.json"
    )
    for key in probe_data.keys():
        new_list = []
        for v_list in probe_data[key]:
            v_set = set(v_list)
            new_list.append(v_set)
        probe_data[key] = new_list
    return probe_data

def prepare_data():
    probe_data = get_data_from_json(
        "../../Probes/Dubbo/dubbo_probe_data.json"
    )
    for key in probe_data.keys():
        new_list = []
        for v_list in probe_data[key]:
            v_set = set(v_list)
            new_list.append(v_set)
        probe_data[key] = new_list


    filter_versions = [
        "2.6.0",
        "2.7.0",
        "2.7.1",
        "2.7.2",
        "2.7.3",
        "2.7.4",
        "2.7.5",
        "3.2.14",
        "3.2.15",
        "3.1.1",
        "3.1.2",
    ]
    versions = get_valid_versions()
    versions = [x for x in versions if x not in filter_versions]
    
    return probe_data,versions




def work_one(hostinfo:str,debug=False, replan_flag = False):
    ctype="dubbo"

    
    save_file_path = f""
    offline_file_path = f""
    replan_file_path = f''
    off_fp = os.path.join(offline_file_path, hostinfo) 
    base_dir = os.path.join(save_file_path, hostinfo + "/result.json")
    
    if not debug:
        if not replan_flag:
            if os.path.exists(off_fp) or os.path.exists(base_dir):
                print(f"{hostinfo} is already scanned")
                return
        else:
            if os.path.exists(os.path.join(replan_file_path, hostinfo)):
                print(f"{hostinfo} is already replanned")
                return
    
    
    ip, port = hostinfo.split(":")
    if is_port_open(ip, int(port)):
        try:
            if not replan_flag:
                base_dir = os.path.join(save_file_path, hostinfo)
            else:
                base_dir = os.path.join(replan_file_path, hostinfo)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            print(f"start scan {hostinfo}")

            probe_data, versions = prepare_data()
            init_tree, min_probes = generate_optimal_tree(probe_data, set(versions), [])
            results = full_scan(hostinfo, init_tree, probe_data, ctype)

            if len(results) > 2 and len(results[2]) > 0:
                results[2] = sorted(
                    results[2], key=lambda x: tuple(map(int, x.split(".")))
                )

            vr = versions_to_ranges(results[2])
            if not vr == '2.5.5-2.5.10, 2.6.1-2.6.12, 2.7.6-2.7.23, 3.0.0-3.0.15, 3.1.0, 3.1.3-3.1.11, 3.2.0-3.2.13':
                if not debug:
                    with open(os.path.join(base_dir, "result.json"), "w") as f:
                        json.dump(results, f)

        except Exception as e:
            traceback.print_exc()
            notice(f"RealWorld Case Error is :{e}")

    else:
        if not replan_flag and not debug:
            os.makedirs(off_fp)
            print(f"{hostinfo} is not connected")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python3 scan.py [args]')
    para = sys.argv[1]
    work_one(para)
   