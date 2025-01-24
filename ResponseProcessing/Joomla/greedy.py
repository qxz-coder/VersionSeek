def split_version_by_greedy(probe_data:dict,target_version:str):
    '''
    Input: A dictionary where keys are probe names and values are lists of sets.
    Output: A greedy selection of probes that maximizes distinctions.
    '''
    all_versions = set()
    for probe in probe_data:
        for version_set in probe_data[probe]:
            all_versions.update(version_set)
    
    if target_version not in all_versions:
        # raise ValueError("Target version not in version set.")
        return [],all_versions
    
    not_distinguished_set = all_versions.copy()
    # if target_version in not_distinguished_set:
    not_distinguished_set.remove(target_version)
    

    selected_probes = []
    while True:
        max_num_versions = 0   
        best_probe = None
        for probe,version_sets_by_probe in probe_data.items():
            if probe in selected_probes:
                continue
            
  
            for version_set in version_sets_by_probe:
                if target_version in version_set:
                    remains = all_versions.difference(version_set)
                    intersection = remains.intersection(not_distinguished_set)
                    if len(intersection) > max_num_versions:
                        max_num_versions = len(intersection)
                        best_probe = probe
        
        if best_probe is None:
            break
        
        selected_probes.append(best_probe)
        for version_set in probe_data[best_probe]:
            if target_version in version_set:
                remains = all_versions.difference(version_set)
                not_distinguished_set = not_distinguished_set.difference(remains)
                
    return selected_probes,not_distinguished_set