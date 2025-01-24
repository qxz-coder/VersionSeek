
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




def split_versions(version_set, version_sets_by_probe):

    remaining_versions = version_set.copy()
    new_sets = []
    

    for v_set in version_sets_by_probe:
        intersection = version_set.intersection(v_set)
        if intersection:
            new_sets.append(intersection)
            remaining_versions -= intersection
    
    if remaining_versions:
        new_sets.append(remaining_versions)
    
    return new_sets


def heuristic_sort_probes(probe_data, remaining_set, chosen_probes):

    def split_effectiveness(probe):
        version_sets = probe_data[probe]
        new_sets = []
        for v_set in remaining_set:
            new_sets.extend(split_versions(v_set, version_sets))
        return len(new_sets) - len(remaining_set)

    effective_probes = [
        probe for probe in probe_data.keys() if split_effectiveness(probe) > 0 and probe not in chosen_probes
    ]

    return sorted(effective_probes, key=split_effectiveness, reverse=True)



def min_probes_backtracking(probe_data, all_versions):


    min_probes = float('inf')
    best_path = []


    probe_data = simplify_probe_data(probe_data, all_versions)
    
    def backtrack(remaining_set, chosen_probes):
        nonlocal min_probes, best_path

        if all(len(s) == 1 for s in remaining_set):
            if len(chosen_probes) < min_probes:
                min_probes = len(chosen_probes)
                best_path = chosen_probes[:]
            return

        if len(chosen_probes) >= min_probes:
            return

        sorted_probes = heuristic_sort_probes(probe_data, remaining_set, chosen_probes)

        for probe in sorted_probes:
            new_sets = []
            for v_set in remaining_set:
                new_sets.extend(split_versions(v_set, probe_data[probe]))
            

            chosen_probes.append(probe)
            backtrack(new_sets, chosen_probes)
            chosen_probes.pop()


    initial_sets = [all_versions]

    backtrack(initial_sets, [])

    return min_probes, best_path