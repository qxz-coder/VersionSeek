# This script is used to parse the response from the server
import os,re,json
from difflib import SequenceMatcher
def mask_text(text):
    pattern = r'(ByteBufStreamInput@)([^;]+)(;)'
    text = re.sub(
        pattern,
        lambda m: f"{m.group(1)}{'*' *6}{m.group(3)}",
        text,
        flags=re.DOTALL  
    )


    pattern = r"% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n(?:.*\n){0,}"
    
    blurred_text = re.sub(pattern, '', text, flags=re.MULTILINE)
    
    uuid_pattern = re.compile(r'"index_uuid"\s*:\s*"[^"]+"',re.MULTILINE)
    # blurred_text = uuid_pattern.sub(uuid_pattern,'"index_uuid":"uuid"',blurred_text)
    
    for match in re.findall(uuid_pattern,blurred_text):
        length = len(match.split('"')[-2]) 
        # blurred_text = blurred_text.replace(match, '"index_uuid":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match, '"index_uuid":"{}"')
    
    index_name_pattern = re.compile(r'"index_name"\s*:\s*"[^"]+"')
    for match in index_name_pattern.finditer(blurred_text):
        length = len(match.group().split('"')[-2])
        # blurred_text = blurred_text.replace(match.group(), '"index_name":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match.group(), '"index_name":"{}"')
      
    node_name_pattern = re.compile(r'"node"\s*:\s*"[^"]+"')
    for match in node_name_pattern.finditer(blurred_text):
        length = len(match.group().split('"')[-2])
        # blurred_text = blurred_text.replace(match.group(), '"node":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match.group(), '"node":"{}"')
      
    index_pattern = re.compile(r'"index"\s*:\s*"[^"]+"')
    for match in index_pattern.finditer(blurred_text):
        length = len(match.group().split('"')[-2])
        # blurred_text = blurred_text.replace(match.group(), '"index":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match.group(), '"index":"{}"')
    
    scroll_id_pattern = re.compile(r'"_scroll_id"\s*:\s*"[^"]+"')
    for match in scroll_id_pattern.finditer(blurred_text):
        length = len(match.group().split('"')[-2])
        # blurred_text = blurred_text.replace(match.group(), '"_scroll_id":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match.group(), '"_scroll_id":"{}"')
    _id_pattern = re.compile(r'"_id"\s*:\s*"[^"]+"')
    for match in _id_pattern.finditer(blurred_text):
        length = len(match.group().split('"')[-2])
        # blurred_text = blurred_text.replace(match.group(), '"_id":"{}"'.format('*'*length))
        blurred_text = blurred_text.replace(match.group(), '"_id":"{}"')
    
    
    
    #     
    out_content_pattern = 'out is:\n(.*)error is:\n'
    out_content = re.findall(out_content_pattern,blurred_text,re.S)
    if out_content:
        out_content = out_content[0]
        match_content = out_content
        try:
            out_content = json.loads(out_content)
            if 'hits' in out_content and 'hits' in out_content['hits']: 
                out_content['hits']['total'] = 0
                out_content['hits']['hits'] = []
            

            
            if 'took' in out_content:
                out_content['took'] = 0
            
            if '_nodes' in out_content and 'nodes' in out_content:
                out_content['nodes'] = {}
                if 'indices' in out_content:
                    out_content['indices'] = {}
            
            if 'error' in out_content and 'header' in out_content['error'] and 'WWW-Authenticate' in out_content['error']['header']:
                temp = out_content['error']['header']['WWW-Authenticate']   # list
                # sort  list
                temp.sort()
                out_content['error']['header']['WWW-Authenticate'] = temp
                
            # if 'error' in out_content and 'failed_shards' in out_content['error']:
                
            if '_shards' in out_content:
                if 'total' in out_content['_shards']:
                    out_content['_shards']['total'] = 0
                if 'successful' in out_content['_shards']:
                    out_content['_shards']['successful'] = 0
                if 'failed' in out_content['_shards']:
                    out_content['_shards']['failed'] = 0
                if 'skipped' in out_content['_shards']:
                    out_content['_shards']['skipped'] = 0
            
            if 'max_score' in out_content:
                out_content['max_score'] = 0
            
            
            
            
            if 'profile' in out_content and 'shards' in out_content['profile']:
                out_content['profile']['shards'] = []
            
            out_content = json.dumps(out_content,sort_keys=True)
            blurred_text = blurred_text.replace(match_content,'out is:\n'+out_content+'error is:\n')
            # blurred_text = re.sub(out_content_pattern,'out is:\n'+out_content+'error is:\n',blurred_text,re.S)
        except:
            pass

    return blurred_text



def similarity(text1,text2):

    return SequenceMatcher(None,text1,text2).ratio()

