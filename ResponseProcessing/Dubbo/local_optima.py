import os,json,re,requests,time
from greedy import split_version_by_greedy

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

def remove_redundant_probes(data:dict, probe_data:dict, remians_probes:list, optima_results:dict):
    all_versions = list(data.keys())
    remains_versions = set(all_versions)
    
    for version in data:
        min_probes = set(data[version])
        if min_probes.issubset(set(remians_probes)):
            remains_versions.remove(version)
    
    new_probe_data = dict()
    for probe in remians_probes:
        new_probe_data[probe] = probe_data[probe]
    
    for version in remains_versions:
        _,new_not_distinguished_set = split_version_by_greedy(new_probe_data,version)
        
        if version  in optima_results:
            old_not_distinguished_set = optima_results[version]
        else:
            _,old_not_distinguished_set = split_version_by_greedy(probe_data,version)
        
        if new_not_distinguished_set != old_not_distinguished_set:  
            return False
    return True


def local_optima(data:dict,probe_data:dict,addition_probes:list=[]):

    versions = list(data.keys())
    max_probes = set()
    for version in versions:
        max_probes = max_probes.union(set(data[version]))
    
    if len(addition_probes) > 0:
        max_probes = max_probes.union(set(addition_probes)) 
    
    
    probe_data = simplify_probe_data(probe_data,set(versions))

    optima_results = dict()
    for version in versions:
        _,not_distinguished_set = split_version_by_greedy(probe_data,version)
        optima_results[version] = not_distinguished_set


    def remove_probe(probes):
        if len(probes) == 0:
            return []
        
        for probe in probes:
            if probe in addition_probes:
                continue
            
            new_probes = probes.copy()
            new_probes.remove(probe)
            if remove_redundant_probes(data,probe_data,new_probes,optima_results = optima_results):
                return remove_probe(new_probes)
        return probes
    
    min_probes = remove_probe(list(max_probes))
    # min_probes = find_min_probes(list(max_probes)[::-1])
    print('min_probes:',min_probes)
    return min_probes



def local_optima_split(data:dict,probe_data:dict,addition_probes:list=[]):

    versions = list(data.keys())
    max_probes = set()
    for version in versions:
        max_probes = max_probes.union(set(data[version]))
    
    if len(addition_probes) > 0:
        max_probes = max_probes.union(set(addition_probes))

    
    
    probe_data = simplify_probe_data(probe_data,set(versions))
    
    print(len(versions),len(max_probes))    

    def remove_probe(probes):
        if len(probes) == 0:
            return []
        
        for probe in probes:
            if probe in addition_probes:
                continue
            
            new_probes = probes.copy()
            new_probes.remove(probe)
            if remove_redundant_probes(data,probe_data,new_probes):
                return remove_probe(new_probes)
        return probes
    
    
    min_probes = remove_probe(list(max_probes))
    # min_probes = find_min_probes(list(max_probes)[::-1])
    print('min_probes:',min_probes)
    return min_probes



