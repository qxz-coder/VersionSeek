import os,re,json
from func_timeout import func_set_timeout
import subprocess
import func_timeout



def get_test_command_from_llm(version:str):
    base_fp = 'xx/Agent/Qwen-Agent/results'
    file_path = f'{base_fp}/{version}'
    files = os.listdir(file_path)
    # print(files)
    for file in files:
        if file.endswith('get_interact_command.json'):
            with open(os.path.join(file_path,file),'r') as f:
                data = json.load(f)
            # print(data[-1][0]['content'])
            command = data[-1][0]['content']
            # break
    
    # if not filter_invalid_command(command):
        # return ''
        # return command
        # print(version,command)
    return command

def get_test_command_from_llm_en(version:str,base_fp = 'xx/Agent/Qwen-Agent/en_results'):
    
    file_path = f'{base_fp}/{version}'
    files = os.listdir(file_path)
    # print(files)
    
    
    
    files.sort()
    for file in files:
        if file.endswith('get_interact_command.json'):
            with open(os.path.join(file_path,file),'r') as f:
                data = json.load(f)
            # print(data[-1][0]['content'])
            command = data[-1][0]['content']
            # break
    return command


def get_test_command_from_llm_en_multiple(version:str,base_fp = 'xx/Agent/Qwen-Agent/en_results'):
    
    results = {}    
    file_path = f'{base_fp}/{version}'
    files = os.listdir(file_path)
    # print(files)
    
    
    # command_file_count = 0
    
    
    files.sort()
    for file in files:
        if file.endswith('get_interact_command.json'):
            
            index = file.split('_')[2]
            str_index= '{}_{}'.format(version,index)
            with open(os.path.join(file_path,file),'r') as f:
                data = json.load(f)
            # print(data[-1][0]['content'])
            command = data[-1][0]['content']
            results[str_index] = command
            # break
    # print('command_file_count:',command_file_count)
    
    return results


def filter_invalid_command(command):
    if 'no specific command' in command.lower():
        return False
    
    if 'the specific command' in command.lower():
        return False
    
    if 'a specific command' in command.lower():
        return False
    
    if 'contain specific command' in command.lower():
        return False
    
    if 'no direct command' in command.lower():
        return False
    
    if 'relevant command' in command.lower():
        return False
    
    if 'not directly correspond to' in command.lower():
        return False
    
    if 'contain the specific information' in command.lower():
        return False
    
    if 'no relevant files found' in command.lower():
        return False 
    
    if 'specific complete command' in command.lower():
        return False
    
    if 'no matching documentation' in command.lower():
        return False
    
    if 'specific information' in command.lower():
        return False
    
    if 'related command' in command.lower():
        return False
    
    if 'the provided document paths' in command.lower():
        return False
    
    
    # if re.search(r'[\u4e00-\u9fa5]',command):
    #     return False
    
    
    #     return False
    
    return True

def filter_error_command_from_results():
    error_times = {}
    results_dir = 'xx/ElasticSearch/batchTestResults'
    for root,ds,fs in os.walk(results_dir):
        for f in fs:
            with open(os.path.join(root,f),'r') as rf:
                content = rf.read()
                if '/bin/sh' in content:
                    # print(f)
                    version_name = f[:-4]
                    # print(content)
                    error_times[version_name] = error_times.get(version_name,0) + 1
    print(error_times)    
    return error_times 


@func_set_timeout(30)
def execute_command_long(command:str):
    p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = p.communicate()
    return out,err


def safe_execute_command_long(command:str):
    try:
        out,err = execute_command_long(command)
        return out,err
    except func_timeout.exceptions.FunctionTimedOut as e:
        return b'command timeout',str(e).encode()
    except Exception as e:
        return b'command error',str(e).encode()



@func_set_timeout(10)
def execute_command(command:str):
    p = subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out,err = p.communicate()
    return out,err


def safe_execute_command(command:str):
    try:
        out,err = execute_command(command)
        return out,err
    except func_timeout.exceptions.FunctionTimedOut as e:
        return b'command timeout',str(e).encode()
    except Exception as e:
        return b'command error',str(e).encode()


def find_all_longest_balanced_braces(s):
    
    stack = []
    matches = []
    current_start = None

    for i, char in enumerate(s):
        if char == '{':
            if not stack:  
                current_start = i
            stack.append(i)
        elif char == '}' and stack:
            stack.pop()  
            if not stack:  
                current_end = i
                
                matches.append(s[current_start:current_end + 1])

    return matches


def sanity_command(command):
    
    
    cpattern = r'```.*?```'
    cmatches = re.findall(cpattern,command,re.DOTALL)
    if cmatches:
        command = cmatches[0]    
    
    
    
    command = command.replace('```bash','').replace('```shell','').replace('```sh', '').replace('```', '')
    
    
    
    command = command.replace('json\n','').replace('sql\n','')
    
    
    if 'GET ' not in command and 'POST ' not in command and 'PUT ' not in command:
        if '{\n  "query"' in command or "{\n  'query'" in command:
            command = 'curl -XGET http://localhost:9200/_search\n'+command
    
    
    
    if 'curl' not in command and ('POST ' in command or 'GET ' in command or 'PUT ' in command):
        
        if 'POST /' not in command:
            command = command.replace('POST ','POST /')
        if 'GET /' not in command:
            command = command.replace('GET ','GET /')
        if 'PUT /' not in command:
            command = command.replace('PUT ','PUT /')
        
        command = command.replace('POST /','curl -XPOST http://localhost:9200/')
        command = command.replace('GET /','curl -XGET http://localhost:9200/')
        command = command.replace('PUT /','curl -XPUT http://localhost:9200/')
        
        # if 'curl' not in command:
        #     command = command.replace('POST ','curl -XPOST http://localhost:9200/')
        #     command = command.replace('GET ','curl -XGET http://localhost:9200/')
        #     command = command.replace('PUT ','curl -XPUT http://localhost:9200/')
        
    # print(command)
    
    
    d_pattern = r'-d\s*[\'\"]\s*{'
    matches = re.findall(d_pattern,command,re.DOTALL)
     
    if '{' in command and not matches:
        
        command = command.replace('\"','\\\"')
        
        result = find_all_longest_balanced_braces(command)
        for match in result:
            command = command.replace(match,f'-d \"{match}\"') if f'\n{match}' not in command else command.replace(f'\n{match}', f' -d \"{match}\"')
            # print(match)
        # command = command.replace('\n{\n',' -d \"{\n')
        # command = command.strip()
        # command = command+'\"'
    
    
    if '<id>' in command:
        command = command.replace('<id>','0000')
    command = command.strip()
    
    
    if '(password)' in command:
        command = command.replace('(password)','123456')
    command = command.strip()
    
    
    
    if '\n\n\ncurl' in command:
        pattern = r"\n{3}curl.*?(\n {0,1}\n{2})"
        match = re.search(pattern, command, re.DOTALL)
        if match:
            command = match.group()
            command = command.strip()
        else:
            if command.endswith('\'') or command.endswith('\"'):
                start_index = command.rfind('\n\n\ncurl')
                command = command[start_index+3:]   
    
    
    # specific command
    # if '/_cat/thread_pool?' in command:
    #     command = command.replace('/_cat/thread_pool?','/_cat/thread_pool?format=json&')
    
    # if '/_cat/indices?' in command:
    #     command = command.replace('/_cat/indices?','/_cat/indices?format=json&')
        
    # if '/_cat/shards?' in command:
    #     command = command.replace('/_cat/shards?','/_cat/shards?format=json&')
        
    # if '/_cat/segments?' in command:
    #     command = command.replace('/_cat/segments?','/_cat/segments?format=json&')
    
    
    # curl -X GET 'http://localhost:9200/_cat/shards?v' or curl -X GET 'http://localhost:9200/_cat/indices?v'
    
    
    # curl -X GET 'http://localhost:9200/_cat/segments?v'
    
    
    # curl -XGET http://localhost:9200/_cat/plugins?v
    
    
    return command  

def upgrade_command(command:str,version:str,open_flag:str=None):

    
    if version.startswith('8') and open_flag!='open':
        command = command.replace('http://','https://')
        command = command.replace('curl ','curl -k ')
    return command    