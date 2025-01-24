# This script is used to parse the response from the server
import os,re,json
from difflib import SequenceMatcher


def mask_text(content):
    combined_messages = []
    
    pattern = r"% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n(?:.*\n){0,10}"
    content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    pattern2 = r'(<(?:script|link)[^>]*(?:src|href)="[^"]+?)(\?[\da-f]+)("[^>]*>)'
    content = re.sub(pattern2, r'\1<VALUE>\3', content)
    content = re.sub(r'<version>\d+\.\d+\.\d+</version>', '<version>XXX</version>', content)
    command_blocks = re.findall(r'Command:\s*(.*?)\nOutput:\s*(.*?)\nError:\s*(.*?)\n', content, flags=re.DOTALL)
    combined_message = ''
    for command, output, error in command_blocks:
        output_lines = [line.strip() for line in output.splitlines() if line.strip()]
        error_lines = [line.strip() for line in error.splitlines() if line.strip()]

        filtered_output = "\n".join(output_lines)
        filtered_error = "\n".join(error_lines)

        if filtered_error:
            combined_message = f"{filtered_output} | Error: {filtered_error}"
        else:
            combined_message = filtered_output

    return combined_message


def similarity(text1,text2):
    return SequenceMatcher(None,text1,text2).ratio()