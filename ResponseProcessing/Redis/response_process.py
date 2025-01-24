# This script is used to parse the response from the server
import os,re,json
from difflib import SequenceMatcher


def mask_text(content:str):
    combined_messages = []
    command_pattern = r'Command:\s*(.*?)\s*(?=Output:|Error:|$)'
    output_pattern = r'Output:\s*(.*?)\s*(?=Error:|$)'
    error_pattern = r'Error:\s*(.*?)(?=Command:|$)'

    commands = re.findall(command_pattern, content, re.DOTALL)
    outputs = re.findall(output_pattern, content, re.DOTALL)
    errors = re.findall(error_pattern, content, re.DOTALL)

        
    for i in range(len(commands)):
        combined_message = "" 
     
        if commands[i].strip().endswith('MEMORY STATS') :
            if i < len(outputs):
                output_text = outputs[i]
                output_lines = output_text.splitlines() 
                filtered_output_lines = [line for index, line in enumerate(output_lines) if index % 2 == 0] 
                filtered_output = "\n".join(filtered_output_lines) 
                combined_message += f"Output: {filtered_output}\n" 
        elif commands[i].strip().endswith('CLIENT INFO'):
            if i < len(outputs):
                output_text = outputs[i]
                output_lines = output_text.splitlines() 
                filtered_output_lines = []
                for line in output_lines:
                
                    line = re.sub(r"=(\S+)", "= ", line)
                    filtered_output_lines.append(line)
                filtered_output = "\n".join(filtered_output_lines)  
                combined_message += f"Output: {filtered_output}\n"  
        
        elif commands[i].strip().endswith('INFO STATS') or \
        commands[i].strip().endswith('INFO server') or commands[i].strip().endswith('INFO CLIENTS') or \
        commands[i].strip().endswith('INFO Persistence') or commands[i].strip().endswith('INFO'): 
         
            if i < len(outputs):
                output_text = outputs[i]
                output_lines = output_text.splitlines()  
                filtered_output_lines = []
                for line in output_lines:
                  
                    line = re.sub(r'(:\s?|rps=|avg_msec=|p50=)(\d+(\.\d+)?|\d*\.\d+)', r'\1<VALUE>', line)
                    line = re.sub(r'(:\s*)(.+)', r'\1<VALUE>', line)
                    line = re.sub(r'(\b\w*id\w*\b:\s?)([^\s]+)', r'\1<VALUE>', line)
                    filtered_output_lines.append(line)
                filtered_output = "\n".join(filtered_output_lines) 
                combined_message += f"Output: {filtered_output}\n"  
        else:
   
            if i < len(outputs):
                output_text = outputs[i]
                output_lines = output_text.splitlines() 
                filtered_output_lines = []
                for line in output_lines:
                   
                    line = re.sub(r'(:\s?|rps=|avg_msec=|p50=)(\d+(\.\d+)?|\d*\.\d+)', r'\1<VALUE>', line)
                    line = re.sub(r'(\b\w*id\w*\b:\s?)([^\s]+)', r'\1<VALUE>', line)
                    filtered_output_lines.append(line)
                filtered_output = "\n".join(filtered_output_lines)  
                combined_message += f"Output: {filtered_output}\n"  
       
        if i < len(errors):
            error_text = errors[i]
            error_text = re.sub(r'(:\s?|rps=|avg_msec=|p50=)(\d+(\.\d+)?|\d*\.\d+)', r'\1<VALUE>', error_text)
            error_text = re.sub(r'(\b\w*id\w*\b:\s?)([^\s]+)', r'\1<VALUE>', error_text)
            combined_message += f"Error: {error_text}\n" 

        combined_messages.append(combined_message.strip())  
    return combined_messages[0]


def similarity(text1,text2):
#    from difflib import SequenceMatcher
    return SequenceMatcher(None,text1,text2).ratio()