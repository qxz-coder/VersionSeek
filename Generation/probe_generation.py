import pprint

import sys
sys.path.append('xx') # save scripts for qwen_agent https://github.com/QwenLM/Qwen-Agent

from qwen_agent.agents import Assistant
from qwen_agent.tools.base import BaseTool, register_tool
from datetime import datetime
import os, json, requests
import time

from func_timeout import func_set_timeout

# Step1: input the component version and feature description,

def save_chat_history(messages, msg_type, version=None, en = False, save_fp = None, detaile_fp = None):
    base_fp = ''
    
    if version is not None:

        base_fp = f''    
        
        if save_fp is not None:
            base_fp = f'{save_fp}/{version}'
        
        if detaile_fp is not None:
            base_fp = detaile_fp
        
        if not os.path.exists(base_fp):
            os.makedirs(base_fp)
    date_prefix = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    file_name = f'{date_prefix}_{msg_type}.json'
    file_path = os.path.join(base_fp, file_name)
    with open(file_path, 'w') as f:
        json.dump(messages, f)

    return messages


def en_search_releate_filepath(component, version, feature, conversation):
    llm_cfg = {
        'model':'Qwen2.5-32B-Instruct',
        'model_server':'',  # llm server address
        'api_key':'',
        "generate_cfg": {"top_p": 0.8, "temperature": 0.5, 'max_input_tokens': 20000},
    }
    fp = "" # save user guide
        
    en_system_instruction = f"""You are a helpful AI assistant. Upon receiving a user's request, you should:
        Step 1: Extract the component version number and feature description from the user's problem description. Focus on the content after the ":" in the feature description. For example, in "QL: Add filtering Query DSL support to IndexResolve," only focus on "Add filtering Query DSL support to IndexResolve."
        Step 2: Generate the root directory based on the version number and base_dir. If it's Elasticsearch, retain only the first two segments of the version number (e.g., for 7.9.1, keep 7.9). The corresponding root directory will be base_dir/7.9. In this real scenario, base_dir is {fp}.
        Step 3: Traverse all filenames and paths under the previously generated root directory and save them in a list. This step requires using the os library functions to traverse and obtain the actual paths, rather than simulating a file list. e.g. for root,ds,fs in os.walk(root_path).
        Step 4: Determine the relevance of the file and directory names to the feature description, prioritizing files with higher relevance, and select up to 10 files for further filtering.
        Step 5: Further assess the relevance to the feature description by considering the keyword frequency in the file contents, such as files where keywords appear most frequently.
        Step 6: Finally, return the file paths most relevant to the feature description, prioritizing the top 5 relevant file paths, ensuring that the provided paths correspond to specific files, such as '{fp}/7.9/Query DSL/Compound queries/compound-queries.html.'
        Step 7: Sort the output file path list again based on the weights of the keywords in the file path names, prioritizing the paths with higher keyword weights.
        
        The following are the notes:
        - If the path cannot be found, end directly and return the error reason without assuming.
        - Do not fabricate non-existent or uncertain answers. If they do not exist in the execution results, do not fabricate them yourself.
        - When filtering keywords, the weight of specific words should be higher than general words. For example, in "Add Kibana UserName," the weight of "Kibana" should be higher than "Add" and "UserName."
        - Ignore the "Release Notes" directory and "toc.html" file during retrieval.
        """
    tools = ["code_interpreter"]
    # , "retrieval"
    
    en_prompt = 'Here is a new feature introduced in {component}v{version} with the description "{feature}". The additional description on GitHub is "{coversation}". Please find the most relevant content in the file list based on this feature description and file and directory names. Finally, only return the file paths, which can include multiple related file paths.'

    bot = Assistant(llm=llm_cfg, system_message=en_system_instruction, function_list=tools)
    
    messages = [] 
    loop_times = 1
    while True:
        try:
            query = en_prompt.format(
                component=component,
                version=version,
                feature=feature,
                coversation=conversation,
            )

            messages.append({"role": "user", "content": query})
            response = []
            for response in bot.run(messages=messages):

                print("Rebot response:")
                pprint.pprint(response, indent=2)

            messages.extend(response)
            loop_times += 1
            if loop_times > 2:
                break
        except Exception as e:

            loop_times = 1
            messages = []
        
    save_chat_history(messages, "search_releate_filepath")
    return messages
    

# 
def en_get_interact_command(component, version, feature, conversation, releated_files):
    en_system_instruction = """You are an AI assistant enhanced by RAG. You need to answer the user's question according to the following steps:
    - Step1: Extract the relevant document path list from the content provided by the user, for example, ['/7.9/Query DSL/Compound queries/compound-queries.html', '/7.9/Query DSL/Compound queries/compound-queries.html']
    - Step2: Based on the file content provided by the user as the context for answering the question, use RAG enhancement to answer the user's question, for example, "How to trigger the new feature's function"
    - Step3: Answer the question concisely. For example, if the user requests a return of the command interaction operation, you only need to reply with the specific command, without providing additional explanations
    """
    
    rag_llm_cfg = {
        'model':'Qwen2.5-32B-Instruct',
        'model_server':'',  # llm server address
        'api_key':'',
    }
    
    rag_prompt = """Here is a new feature introduced in {component}v{version} with the description "{feature}". The additional description on GitHub is "{coversation}". The document path related to this feature is {releated_files}. Based on this information, use RAG enhancement to answer how to trigger this feature. Finally, only provide the specific complete command, without additional explanations or instructions."""
    
    files = [
        "ElasticSearch Commands Cheat Sheet.pdf"
    ]  # probe command examples
    
    description = """Use RAG to retrieve and answer, supporting file types: PDF/Word/PPT/TXT/HTML"""
    
    name = "rag_bot"
    
    rag_bot = Assistant(
        llm=rag_llm_cfg,
        name=name,
        system_message=en_system_instruction,
        description=description,
        files=files,
    )
    
    rag_query = rag_prompt.format(
        component=component,
        version=version,
        feature=feature,
        coversation=conversation,
        releated_files=releated_files,
    )
    
    new_messages = [{"role": "user", "content": [{"text": rag_query}]}]
    
    loop_times = 2
    resp_list = []
    messages = []
    while True:
        try:
            for rsp in rag_bot.run(new_messages):
                pprint.pprint(rsp, indent=2)
                resp_list.append(rsp)
            messages.extend(resp_list)
            loop_times += 1
            if loop_times > 2:
                break
        except Exception as e:
            loop_times = 2
            resp_list = []
            messages = []
        
    save_chat_history(messages, "get_interact_command")
    return messages
 


def run_test():
    component = "ElasticSearch"
    version = "7.9.1"
    feature = "QL: Wildcard field type support"
    conversation = """This PR adds support for `wildcard` data type following its addition in Elasticsearch with https://github.com/elastic/elasticsearch/pull/49993.
    There is one issue that will need to be addressed afterwards: there is a slightly different behavior between `wildcard` and the other text based data types (ie `keyword`) when it comes to Painless scripting. As soon as https://github.com/elastic/elasticsearch/issues/58044 is fixed, the workaround in `InternalQlScriptUtils` needs to be reverted.
    """
    releated_file_messages = en_search_releate_filepath(component, version, feature, conversation)
    save_chat_history(releated_file_messages, "search_releate_filepath", version)
    releated_files = releated_file_messages[-1]["content"]
    command_messages = en_get_interact_command(component, version, feature, conversation, releated_files)
    save_chat_history(command_messages, "get_interact_command", version)







def en_workflow(reworkList=None, case_fp = 'test_case_complate.json',save_fp = ''):
    with open(case_fp,'r') as f:
        case_lists = json.load(f)
    
    start_time = time.time()
    
    for version in case_lists:
        base_fp = save_fp
        if not os.path.exists(base_fp):
            os.makedirs(base_fp)
            
        if os.path.exists(f'{base_fp}/{version}'):
            if reworkList is not None and version in reworkList:
                pass
            else:
                continue
        
        component = case_lists[version]['component']
        version = case_lists[version]['version']
        feature = case_lists[version]['feature']
        conversation = case_lists[version]['conversation']
        releated_file_messages = en_search_releate_filepath(component, version, feature, conversation)
        save_chat_history(releated_file_messages, "search_releate_filepath", version, en = True, save_fp = save_fp)
        releated_files = releated_file_messages[-1]["content"]
        command_messages = en_get_interact_command(component, version, feature, conversation, releated_files)
        save_chat_history(command_messages, "get_interact_command", version, en = True, save_fp = save_fp)


    end_time = time.time()
    len_version = len(case_lists)
    print(f'平均每个版本的运行时间为{(end_time-start_time)/len_version}秒')
    
    



def extract_command_from_chat_history(version:str):
    base_fp = '' # save llm result
    file_path = f'{base_fp}/{version}'
    files = os.listdir(file_path)
    for file in files:
        if file.endswith('get_interact_command.json'):
            with open(os.path.join(file_path,file),'r') as f:
                data = json.load(f)
            # print(data[-1][0]['content'])
            command = data[-1][0]['content']
            # break
    return command


def find_history(description:str,version:str):
    llm_res_dir = 'xx/llmResults'
    files = os.listdir(llm_res_dir)
    for dir_ in files:
        root_path = os.path.join(llm_res_dir,dir_)
        versions = os.listdir(root_path)
        if version in versions:
            file_path = os.path.join(root_path,version)
            files = os.listdir(file_path)
            find_flag = False
            for file in files:
                if file.endswith('search_releate_filepath.json'):
                    with open(os.path.join(file_path,file),'r') as f:
                        related_files_data = json.load(f)
                    for item in related_files_data:
                        if description in item['content']:
                            find_flag = True
                            break
            
            
            
            for file in files:
                if file.endswith('get_interact_command.json'):
                    if find_flag:
                        with open(os.path.join(file_path,file),'r') as f:
                            command_data = json.load(f)
                            
                            return related_files_data,command_data       
    return None,None

def extract_info_from_pr_request_new(pull_request_url:str):
    owner = pull_request_url.split("/")[3]
    repo = pull_request_url.split("/")[4]
    pull_number = pull_request_url.split("/")[6]
    return owner, repo, pull_number

def get_pr_comments_new(owner, repo, pull_number, base_path = ''):
    pr_data = None
    base_dir = f'{base_path}/{owner}/{repo}'
    file_path = os.path.join(base_dir, f'{pull_number}.json')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            pr_data = json.load(f)
    return pr_data

@func_set_timeout(900)
def en_workflow_new(case_lists:dict,save_dir:str,componentName:str='ElasticSearch',debug=False):
    if not debug:
        for version in case_lists:
            for index,case in enumerate(case_lists[version]):
                component = componentName
                version = version
                feature = case['Description']
                pr_url = case['Pull Request'][0]
                pr_info = extract_info_from_pr_request_new(pr_url)
                pr_data = get_pr_comments_new(*pr_info)
                if pr_data is None or 'body' not in pr_data:
                    continue
                conversation = pr_data['body']
                
                version_index = f'{version}_{index}'
                if version_index in black_lists:
                    continue
                
                re_file_name = f'{version}_feature_{index}_search_releate_filepath.json'
                re_command_name = f'{version}_feature_{index}_get_interact_command.json'
                save_base_dir = os.path.join(save_dir,version)
                full_re_file_name = os.path.join(save_base_dir,re_file_name)
                
                
                if not os.path.exists(save_base_dir):
                    os.makedirs(save_base_dir)
                    
                if not os.path.exists(full_re_file_name):
                    with open(full_re_file_name,'w') as f:
                        json.dump(related_files_data,f)
                
                full_re_command_name = os.path.join(save_base_dir,re_command_name)
                
                if not os.path.exists(full_re_command_name):
                    with open(full_re_command_name,'w') as f:
                        json.dump(command_data,f)


    else:   
        startTime = time.time()
        valitTimes = 0
        import random
        keys = list(case_lists.keys())
        rkeys = random.choices(keys,k=20)
        for version in rkeys:
            for index,case in enumerate(case_lists[version]):
                component = componentName
                version = version
                feature = case['Description']
                pr_url = case['Pull Request'][0]
                pr_info = extract_info_from_pr_request_new(pr_url)
                pr_data = get_pr_comments_new(*pr_info)
                if pr_data is None or 'body' not in pr_data:
                    continue
                conversation = pr_data['body']
                
                related_files_data = en_search_releate_filepath(component, version, feature, conversation)
                releated_files = related_files_data[-1]["content"]
                command_data = en_get_interact_command(component, version, feature, conversation, releated_files)

                valitTimes += 1
                if valitTimes >=10:
                    end_time = time.time()
                    average_time = (end_time-startTime)/valitTimes
                    return 

        
        
        
        

if __name__ == "__main__":

    save_fp = ''
    features_fp = '' # save functional features
    with open('','r') as f:
        case_lists = json.load(f)   
    print(112)
    # en_workflow_new(case_lists,save_fp)
    

    
