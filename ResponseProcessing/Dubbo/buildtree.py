import os,json

    
class TreeNode:
    def __init__(self, name, path=None, remaining_versions=None):
        self.name = name
        self.children = {}
        self.path = path if path else []  

        self.remaining_versions = remaining_versions if remaining_versions else set()
        if len(self.remaining_versions):
            self.type = "probe"
        else:
            self.type = "version"
        
        

    def add_child(self, response_category, child_node):
        # print(self.path)
        child_node.path = self.path + [response_category] 
        self.children[response_category] = child_node
        self.type = "probe"  
        # print(child_node.path)


    def to_dict(self):
        return {
            "name": self.type+ '_'+ self.name,
            "children": {key: child.to_dict() for key, child in self.children.items()},
            "path": self.path,
            "type": self.type,
            "not_distinguished_versions": list(self.remaining_versions)
        }


def can_split(probe_data:dict,current_probe:str,remaining_versions:set):
    for v_sets in probe_data[current_probe]:
        new_remains_versions = remaining_versions.intersection(v_sets)
        if len(new_remains_versions) == 0 or len(new_remains_versions) == len(remaining_versions): 
            continue
        return True
    return False



def build_tree(probe_data, all_verison_sets, current_probe, remaining_versions, used_probes, path=[]):
    node = TreeNode(current_probe, path=path, remaining_versions = remaining_versions)
    if current_probe not in probe_data:
        return node
    
    for v_sets in probe_data[current_probe]:
        response_category_name = f"p:{current_probe}_r:{list(v_sets)[0]}"
        new_remains_versions = remaining_versions.intersection(v_sets)  # 交集
        
        if len(new_remains_versions) == 0 or len(new_remains_versions) == len(remaining_versions):  
            continue
        elif len(new_remains_versions) == 1:

            child_node = TreeNode(list(new_remains_versions)[0], path=path+[response_category_name], remaining_versions = set())
            node.add_child(response_category_name, child_node)
        
        else:
            # 
            selected_flag = False   

            for probe in probe_data:

                if probe in used_probes:
                    continue

                if not can_split(probe_data, probe, new_remains_versions):
                    continue
                
                selected_flag = True
                used_probes.add(probe)
                child_node = build_tree(probe_data, all_verison_sets, probe, new_remains_versions, used_probes, path+[response_category_name])
                # child_node = TreeNode(probe, path=None, remaining_versions = new_remains_versions)
                node.add_child(response_category_name, child_node)
                # child_node.add_child(probe, build_tree(probe_data, all_verison_sets, probe, new_remains_versions, used_probes))
                used_probes.remove(probe)
                break
            

            if not selected_flag:
                child_node = TreeNode("notdis", path=path+[response_category_name], remaining_versions = new_remains_versions)
                node.add_child(response_category_name, child_node)
    return node    
    
    

def save_tree_to_json(tree_root, filename):
    with open(filename, 'w') as f:
        json.dump(tree_root.to_dict(), f, indent=4)


if __name__ == "__main__":
    
    probes = ['6.7.0', '8.14.0', '6.2.0', '6.5.0', '7.4.0', '8.12.0']
    
    
    probe_data = {}
    
    
    probe_data = {
        "probe1": [{"A1", "A2"}, {"B1", "B2"}],
        "probe2": [{"A1", "B1"}, {"A2", "B2"}],
    }

    distinguished_sets = {"A1", "A2", "B1", "B2"}


    root = build_tree(probe_data, distinguished_sets, "probe1", distinguished_sets, {"probe1"},path = [])


    save_tree_to_json(root, "probe_tree.json")
